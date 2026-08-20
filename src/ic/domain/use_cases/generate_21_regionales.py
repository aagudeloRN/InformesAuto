"""UC-2: Referentes Regionales LatAm/Colombia (Cap 2.1.2).

EMIS como fuente primaria (fuente_tipo_filter="emis"). Ausencia inmediata si no hay
chunks EMIS del sector. Complemento web opcional si hay base EMIS.
"""

from __future__ import annotations

import logging
import re
import uuid

from ic.data.repositories.entidad_repo import _clave_exclusion
from ic.domain.absent_data import build_absent_paragraph
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.protocols import InvokableChain as Runnable
from ic.shared.types import Cap21Regionales, ChunkResult

logger = logging.getLogger(__name__)

_MIN_CHUNKS_EMIS = 3
_HEADING = "### Referentes Regionales LatAm/Colombia"
_SECTION_LABEL = "Referentes Regionales LatAm/Colombia"

# Patrón simple para extraer nombres de empresa de texto de chunk (heurístico, no NER completo)
_EMPRESA_PATTERN = re.compile(
    r"\b([A-Z][A-Za-záéíóúüñÁÉÍÓÚÜÑ]{2,}"
    r"(?:\s+[A-Z][A-Za-záéíóúüñÁÉÍÓÚÜÑ]{2,}){0,3})\b"
)


def _extraer_nombres_emis(chunks: list[ChunkResult]) -> list[str]:
    """Extrae nombres candidatos de empresa desde metadatos o texto de chunks EMIS."""
    nombres: list[str] = []
    vistos: set[str] = set()
    for chunk in chunks:
        meta = chunk.metadatos or {}
        for key in ("empresa", "nombre_empresa", "titulo", "title"):
            val = meta.get(key)
            if val and isinstance(val, str):
                nombre = val.strip()
                clave = nombre.casefold()
                if nombre and clave not in vistos:
                    nombres.append(nombre)
                    vistos.add(clave)
    return nombres


class Generate21Regionales:
    def __init__(
        self,
        chain_perfil: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        max_empresas: int = 3,
    ) -> None:
        self._chain_perfil = chain_perfil
        self._store = store
        self._web = web_connector
        self._max_empresas = max_empresas

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        sector_gics_code: str | None,
        empresa_id: uuid.UUID | None,
    ) -> Cap21Regionales:
        # 1. Retrieval exclusivo EMIS
        query_emis = (
            f"{sector_gics} referentes regionales LatAm Colombia competidores líderes mercado"
        )
        chunks_emis: list[ChunkResult] = self._store.search(
            query_emis,
            sector_gics=sector_gics_code,
            empresa_id=empresa_id,
            fuente_tipo_filter="emis",
        )

        # 2. Ausencia inmediata si no hay chunks EMIS
        if len(chunks_emis) < _MIN_CHUNKS_EMIS:
            return Cap21Regionales(
                texto=build_absent_paragraph(
                    _SECTION_LABEL,
                    "No se encontraron documentos EMIS del sector en el repositorio. "
                    "Incorpore informes EMIS del sector para generar esta sección",
                ),
                empresas_emis=[],
                n_con_emis=0,
                retrieval_suficiente=False,
            )

        # 3. Extraer nombres, filtrar empresa focal y recortar a max_empresas
        nombres_emis = _extraer_nombres_emis(chunks_emis)
        clave_focal = _clave_exclusion(nombre_empresa)
        nombres_emis = [n for n in nombres_emis if _clave_exclusion(n) != clave_focal]
        nombres_emis = nombres_emis[: self._max_empresas]

        # 4. Complemento web opcional (solo si hay base EMIS)
        chunks_web: list[ChunkResult] = []
        if nombres_emis:
            for nombre in nombres_emis[:2]:
                query_web = f"{nombre} {sector_gics} mercado LatAm Colombia 2024 2025"
                resultados = self._web.search(query_web, max_results=2)
                if not resultados:
                    continue
                textos = [r.content for r in resultados]
                urls = [r.url for r in resultados]
                self._store.ingest(textos, fuente_tipo="web", urls=urls, empresa_id=empresa_id)

            query_web_retrieval = (
                f"{sector_gics} referentes regionales {' '.join(nombres_emis[:2])}"
            )
            chunks_web = self._store.search(query_web_retrieval, sector_gics=sector_gics_code)

        # 5. Generar prosa
        ctx_emis = format_chunks_as_context(chunks_emis)
        ctx_web = format_chunks_as_context(chunks_web) if chunks_web else "(sin complemento web)"
        texto = self._chain_perfil.invoke({
            "sector_gics": sector_gics,
            "nombre_empresa": nombre_empresa,
            "empresas_emis": ", ".join(nombres_emis) if nombres_emis else "identificadas en EMIS",
            "chunks_emis_context": ctx_emis,
            "chunks_web_context": ctx_web,
        })
        if not isinstance(texto, str):
            texto = str(texto)
        if not texto.startswith(_HEADING):
            texto = f"{_HEADING}\n\n{texto}"

        todos_chunks = chunks_emis + chunks_web
        logger.info(
            "Cap21Regionales: %d chunks EMIS, %d empresas, %d web",
            len(chunks_emis), len(nombres_emis), len(chunks_web),
        )

        return Cap21Regionales(
            texto=texto,
            empresas_emis=nombres_emis,
            n_con_emis=len(nombres_emis),
            retrieval_suficiente=True,
            chunks_usados=todos_chunks,
        )
