from __future__ import annotations

import json
import logging
import re

from langchain_core.runnables import Runnable

from ic.domain.absent_data import build_absent_paragraph, check_retrieval_sufficient
from ic.domain.chains.chain_02b_entidades import MAX_ENTIDADES, parse_entidades
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.domain.kb.relevance import format_referentes_globales
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.text_utils import has_cjk_characters
from ic.shared.types import CapBenchmarking

logger = logging.getLogger(__name__)

_MIN_CHUNKS = 5

# Bloque cercado del radar emitido al final de la respuesta del LLM (T16.1).
# Tolera etiquetas de lenguaje variables: ```radar_json, ```json o ``` a secas (T22.2, DT-027).
_RADAR_RE = re.compile(r"```(?:radar_json|json)?\s*(.*?)```", re.DOTALL)
# Coma colgante antes de } o ] (error de formato frecuente del LLM local).
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _find_balanced_object(texto: str, needle: str) -> str | None:
    """Devuelve el objeto JSON balanceado ({...}) que contiene `needle`, o None.

    Escaneo puro de llaves para tolerar objetos anidados sin fences (T22.2).
    No fabrica datos: solo delimita un objeto ya presente en el texto.
    """
    pos = texto.find(needle)
    if pos == -1:
        return None
    start = texto.rfind("{", 0, pos)
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(texto)):
        if texto[i] == "{":
            depth += 1
        elif texto[i] == "}":
            depth -= 1
            if depth == 0:
                return texto[start : i + 1]
    return None


def _try_parse_radar(raw_json: str) -> dict | None:
    """Parsea un objeto JSON del radar, tolerando comas colgantes. Nunca fabrica datos.

    Parseo laxo (cualquier dict): la validación de claves la hace el pipeline aguas
    abajo (contrato T16.1). Devuelve None solo si no hay JSON parseable.
    """
    for candidate in (raw_json, _TRAILING_COMMA_RE.sub(r"\1", raw_json)):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data
    return None


def _extract_radar(texto: str) -> tuple[str, dict | None]:
    """Extrae el bloque radar_json del texto del LLM y devuelve (texto_limpio, datos).

    Si el bloque no existe o es inválido, devuelve (texto_original, None).
    Tolera etiquetas de lenguaje del fence, comas colgantes y bloques sin fence (T22.2).
    El bloque cercado se retira de la prosa aunque el JSON no sea parseable.
    """
    m = _RADAR_RE.search(texto)
    if m:
        clean = texto[: m.start()].rstrip()
        data = _try_parse_radar(m.group(1).strip())
        if data is not None:
            return clean, data
        logger.warning(
            "radar_json no parseable — fallback a placeholder. Raw: %r", m.group(1)[:120]
        )
        return clean, None
    # Fallback sin fence: objeto JSON balanceado que contenga las claves del radar.
    bare = _find_balanced_object(texto, '"dimensions"')
    if bare is not None:
        data = _try_parse_radar(bare)
        if data is not None:
            return texto[: texto.find(bare)].rstrip(), data
    return texto, None


class GenerateBenchmarking:
    def __init__(
        self,
        chain: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        entidades_chain: Runnable | None = None,
        kb_competidores: list[str] | None = None,
        kb_locales: list[str] | None = None,
        jugadores_locales_ctx: str = "",
        fichas_conocidas_ctx: str = "",
    ) -> None:
        self._chain = chain
        self._store = store
        self._web_connector = web_connector
        # T22.4 (DT-054): cadena de identificación de entidades competidoras. Si es None se
        # conserva el comportamiento previo (sin búsqueda dirigida por entidad).
        self._entidades_chain = entidades_chain
        # DT-056/T3: lista canónica de competidores del KB por sector (cierra causas A/E). None o
        # [] = comportamiento B1 (solo lo que el LLM ancle en la evidencia). Los nombres del KB
        # provienen de evidencia (candidatos NER consolidados), no se fabrican (RN-001).
        self._kb_competidores = kb_competidores or []
        # DT-050: jugadores LOCALES del directorio (regionales + startups) para 2.1.2/2.1.3.
        # `kb_locales` = nombres para la búsqueda dirigida; `jugadores_locales_ctx` = bloque de
        # contexto estructurado inyectado al prompt. Vacíos → invariante (flag OFF). RN-001: son
        # datos recuperados del directorio, no fabricados.
        self._kb_locales = kb_locales or []
        self._jugadores_locales_ctx = jugadores_locales_ctx or ""
        # DT-064/T4: bloque de fichas ya conocidas del KB (pre-fill). "" → invariante.
        self._fichas_conocidas_ctx = fichas_conocidas_ctx or ""

    def _identificar_entidades(self, chunks, sector_gics: str) -> list[str]:
        """Entidades competidoras a explotar: KB (canónico) + las ancladas en la evidencia.

        La lista del KB lidera (menos alucinación, fichas pre-pobladas); se completa con las que
        el LLM extrae de la evidencia. Dedup casefold, cota MAX_ENTIDADES (T22.4/DT-056, RN-001).
        """
        raw = self._entidades_chain.invoke({
            "sector_gics": sector_gics,
            "retrieval_competidores": format_chunks_as_context(chunks),
        })
        del_llm = parse_entidades(raw)
        # Fusión priorizando el KB (global + locales del directorio), sin duplicar (casefold),
        # respetando la cota. Los locales entran a la búsqueda dirigida para poblar 2.1.2/2.1.3.
        fusionadas: list[str] = []
        vistos: set[str] = set()
        for nombre in [*self._kb_competidores, *self._kb_locales, *del_llm]:
            clave = nombre.casefold()
            if clave in vistos:
                continue
            vistos.add(clave)
            fusionadas.append(nombre)
            if len(fusionadas) >= MAX_ENTIDADES:
                break
        logger.info(
            "entidades competidoras: %d (KB=%d, LLM=%d) %s",
            len(fusionadas), len(self._kb_competidores), len(del_llm), fusionadas,
        )
        return fusionadas

    def _buscar_por_entidad(self, entidades: list[str], sector_gics: str) -> None:
        """Búsqueda web dirigida por entidad para poblar las fichas de la sección 2.1 (T22.4)."""
        for entidad in entidades:
            query = (
                f"{entidad} {sector_gics} perfil empresa portafolio productos "
                "cuota de mercado Colombia"
            )
            results = self._web_connector.search(query, search_depth="advanced")
            if results:
                self._store.ingest(
                    texts=[r.content for r in results],
                    fuente_tipo="web",
                    urls=[r.url for r in results],
                )

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        sector_gics_code: str | None = None,
        empresa_id=None,
    ) -> CapBenchmarking:
        # Queries específicas de perfil de empresa (no overviews de sector) con
        # search_depth="advanced": Tavily recupera contenido más profundo, necesario
        # para poblar las fichas de competidor de la sección 2.1 (DT-035).
        queries = [
            f"{sector_gics} principales empresas competidoras Colombia cuota de mercado 2025",
            f"{sector_gics} líderes globales del sector perfil estratégico portafolio",
            f"{sector_gics} referentes regionales LatAm empresas emergentes disruptores",
        ]
        for query in queries:
            web_results = self._web_connector.search(query, search_depth="advanced")
            if web_results:
                self._store.ingest(
                    texts=[r.content for r in web_results],
                    fuente_tipo="web",
                    urls=[r.url for r in web_results],
                )

        retrieval_query = f"{sector_gics} competitors benchmarking {nombre_empresa}"
        chunks = self._store.search(
            retrieval_query, sector_gics=sector_gics_code, empresa_id=empresa_id,
        )

        # T22.4 (DT-054): identificar entidades competidoras y lanzar búsquedas dirigidas por
        # entidad (no solo por sector) para enriquecer las fichas de la sección 2.1. Solo si hay
        # cadena de entidades y evidencia inicial suficiente para anclar nombres (RN-001).
        if self._entidades_chain is not None and check_retrieval_sufficient(
            chunks, min_chunks=_MIN_CHUNKS
        ):
            entidades = self._identificar_entidades(chunks, sector_gics)
            if entidades:
                self._buscar_por_entidad(entidades, sector_gics)
                # Re-recuperar con el índice enriquecido (web por-entidad + EMIS individuales).
                chunks = self._store.search(
                    retrieval_query, sector_gics=sector_gics_code, empresa_id=empresa_id,
                )

        if not check_retrieval_sufficient(chunks, min_chunks=_MIN_CHUNKS):
            return CapBenchmarking(
                texto=build_absent_paragraph("Cap 2 — Análisis Competitivo"),
                n_chunks_usados=0,
                retrieval_suficiente=False,
                chunks_usados=[],
            )

        context = format_chunks_as_context(chunks)
        texto_raw = self._chain.invoke({
            "descripcion_empresa": descripcion_empresa,
            "sector_gics": sector_gics,
            "retrieval_competidores": context,
            "jugadores_locales": self._jugadores_locales_ctx,
            # DT-064/T1: sujetos globales anclados (kb_competidores) como actores obligatorios de
            # 2.1.1. Vacío → invariante (el LLM identifica los globales del RAG del sector).
            "referentes_globales_anclados": format_referentes_globales(self._kb_competidores),
            # DT-064/T4: campos de ficha ya conocidos del KB (escribir desde hechos).
            "fichas_conocidas": self._fichas_conocidas_ctx,
        })

        if has_cjk_characters(texto_raw):
            return CapBenchmarking(
                texto=build_absent_paragraph(
                    "Cap 2 — Análisis Competitivo",
                    "El modelo generó texto en un idioma incorrecto (no español)",
                ),
                n_chunks_usados=len(chunks),
                retrieval_suficiente=False,
                chunks_usados=chunks,
            )

        # T16.1: extraer bloque radar_json; si parseable, adjuntar en radar_data
        texto, radar_data = _extract_radar(texto_raw)
        # T22.2 (DT-027): log determinista para medir el hit-rate del radar (N corridas).
        logger.info(
            "radar_data: %s (%d competidores)",
            "PRESENTE" if radar_data else "AUSENTE",
            len(radar_data.get("competidores", {})) if radar_data else 0,
        )

        return CapBenchmarking(
            texto=texto,
            n_chunks_usados=len(chunks),
            retrieval_suficiente=True,
            chunks_usados=chunks,
            radar_data=radar_data,
        )
