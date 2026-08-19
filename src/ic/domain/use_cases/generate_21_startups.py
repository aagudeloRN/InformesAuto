"""UC-3: Startups y Disruptores (Cap 2.1.3).

Locales: hasta max_locales de StartIA vía list_locales_by_sector(segmento='startup').
Internacionales: hasta max_internacionales vía web (solo si locales < max_locales).
Los locales aparecen primero en la prosa.
"""

from __future__ import annotations

import logging
import uuid

from langchain_core.runnables import Runnable

from ic.data.repositories.entidad_repo import EntidadRepository, _clave_exclusion
from ic.domain.absent_data import build_absent_paragraph
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.domain.kb.relevance import LocalRow
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.types import Cap21Startups, ChunkResult

logger = logging.getLogger(__name__)

_HEADING = "### Startups y Disruptores del sector"
_SECTION_LABEL = "Startups y Disruptores del sector"


def _format_local_row(row: LocalRow) -> str:
    partes = [row.nombre]
    for extra in (row.ciudad, row.actividad, row.tamano):
        if extra:
            partes.append(extra)
    return "- " + " — ".join(partes)


class Generate21Startups:
    def __init__(
        self,
        chain_perfil: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        entidad_repo: EntidadRepository,
        max_locales: int = 3,
        max_internacionales: int = 2,
    ) -> None:
        self._chain_perfil = chain_perfil
        self._store = store
        self._web = web_connector
        self._entidad_repo = entidad_repo
        self._max_locales = max_locales
        self._max_internacionales = max_internacionales

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        sector_gics_code: str | None,
        sectores_ancla: list[str],
        empresa_id: uuid.UUID | None,
    ) -> Cap21Startups:
        # 1. Startups locales desde StartIA
        filas_locales: list[LocalRow] = self._entidad_repo.list_locales_by_sector(
            sectores_ancla,
            segmento="startup",
            limit=self._max_locales,
            exclude_nombre=nombre_empresa,
        )
        nombres_locales = [r.nombre for r in filas_locales]

        # 2. Claves de dedup (locales)
        claves_locales = {_clave_exclusion(n) for n in nombres_locales}

        # 3. Internacionales vía web (solo si hay espacio)
        chunks_internacionales: list[ChunkResult] = []
        nombres_internacionales: list[str] = []

        if len(filas_locales) < self._max_locales:
            query_intl = (
                f"{sector_gics} startups disruptors innovative companies 2024 2025 "
                "venture backed emerging technology"
            )
            resultados_web = self._web.search(query_intl, max_results=5)
            if resultados_web:
                textos = [r.content for r in resultados_web]
                urls = [r.url for r in resultados_web]
                self._store.ingest(textos, fuente_tipo="web", urls=urls, empresa_id=empresa_id)

                chunks_w = self._store.search(query_intl, sector_gics=sector_gics_code)
                chunks_internacionales = chunks_w

                # Extraer nombres candidatos de resultados web (títulos)
                for r in resultados_web[: self._max_internacionales]:
                    candidato = r.title.strip() if r.title else ""
                    if not candidato:
                        continue
                    clave = _clave_exclusion(candidato)
                    if clave in claves_locales:
                        continue
                    if candidato not in nombres_internacionales:
                        nombres_internacionales.append(candidato)
                    if len(nombres_internacionales) >= self._max_internacionales:
                        break

        # 4. Ausencia total si no hay nada
        if not nombres_locales and not chunks_internacionales:
            return Cap21Startups(
                texto=build_absent_paragraph(
                    _SECTION_LABEL,
                    "No se encontraron startups locales en el directorio "
                    "ni fuentes web de disruptores internacionales",
                ),
                locales=[],
                internacionales=[],
                retrieval_suficiente=False,
            )

        # 5. Construir contextos (locales primero)
        locales_ctx = (
            "\n".join(_format_local_row(r) for r in filas_locales)
            if filas_locales else "(sin startups locales)"
        )
        intl_ctx = (
            format_chunks_as_context(chunks_internacionales)
            if chunks_internacionales else "(sin disruptores internacionales)"
        )

        # 6. Generar prosa
        texto = self._chain_perfil.invoke({
            "sector_gics": sector_gics,
            "nombre_empresa": nombre_empresa,
            "locales_context": locales_ctx,
            "internacionales_context": intl_ctx,
        })
        if not isinstance(texto, str):
            texto = str(texto)
        if not texto.startswith(_HEADING):
            texto = f"{_HEADING}\n\n{texto}"

        logger.info(
            "Cap21Startups: %d locales, %d internacionales, %d chunks web",
            len(nombres_locales), len(nombres_internacionales), len(chunks_internacionales),
        )

        return Cap21Startups(
            texto=texto,
            locales=nombres_locales,
            internacionales=nombres_internacionales,
            retrieval_suficiente=True,
            chunks_usados=chunks_internacionales,
        )
