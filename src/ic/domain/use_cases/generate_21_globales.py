"""UC-1: Referentes Globales (Cap 2.1.1).

Propone candidatos globales vía LLM, busca cada uno en web, recupera chunks RAG
y genera perfiles en prosa. Máx 5 empresas.
"""

from __future__ import annotations

import logging
import uuid

from ic.data.repositories.entidad_repo import _clave_exclusion
from ic.domain.absent_data import build_absent_paragraph
from ic.domain.chains.chain_02c_pares_globales import parse_pares_globales
from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
from ic.infrastructure.sources.web_connector import WebConnector
from ic.shared.protocols import InvokableChain as Runnable
from ic.shared.types import Cap21Globales, ChunkResult

logger = logging.getLogger(__name__)

_MIN_CHUNKS = 3
_HEADING = "### 2.1.1. Referentes Globales"
_SECTION_LABEL = "Referentes Globales"


class Generate21Globales:
    def __init__(
        self,
        chain_candidatos: Runnable,
        chain_perfil: Runnable,
        store: PGVectorStore,
        web_connector: WebConnector,
        max_empresas: int = 5,
    ) -> None:
        self._chain_candidatos = chain_candidatos
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
        productos: str = "",
    ) -> Cap21Globales:
        # 1. Proponer candidatos vía LLM
        raw = self._chain_candidatos.invoke({
            "sector_gics": sector_gics,
            "productos": productos or descripcion_empresa,
        })
        todos = parse_pares_globales(str(raw)) if isinstance(raw, str) else (raw or [])

        # 2. Excluir la empresa focal y recortar a max_empresas
        focal_key = _clave_exclusion(nombre_empresa)
        candidatos = [n for n in todos if _clave_exclusion(n) != focal_key]
        candidatos = candidatos[: self._max_empresas]

        if not candidatos:
            return Cap21Globales(
                texto=build_absent_paragraph(
                    _SECTION_LABEL,
                    "El modelo no identificó referentes globales para el sector/productos",
                ),
                candidatos=[],
                n_candidatos_con_web=0,
                retrieval_suficiente=False,
            )

        # 3. Búsqueda web por candidato + ingesta en store
        n_con_web = 0
        for candidato in candidatos:
            query = f"{candidato} {sector_gics} business model revenue market strategy 2024 2025"
            resultados = self._web.search(query, max_results=3)
            if not resultados:
                continue
            n_con_web += 1
            textos = [r.content for r in resultados]
            urls = [r.url for r in resultados]
            self._store.ingest(textos, fuente_tipo="web", urls=urls, empresa_id=empresa_id)

        # 4. Retrieval post-ingesta
        retrieval_query = (
            f"{sector_gics} referentes globales clase mundial modelo de negocio "
            + " ".join(candidatos[:3])
        )
        chunks: list[ChunkResult] = self._store.search(
            retrieval_query,
            sector_gics=sector_gics_code,
            empresa_id=empresa_id,
        )

        # 5. Regla de ausencia
        if len(chunks) < _MIN_CHUNKS:
            return Cap21Globales(
                texto=build_absent_paragraph(
                    _SECTION_LABEL,
                    "No se encontraron fuentes suficientes sobre los referentes "
                    "globales identificados",
                ),
                candidatos=candidatos,
                n_candidatos_con_web=n_con_web,
                retrieval_suficiente=False,
            )

        # 6. Generar prosa
        ctx = format_chunks_as_context(chunks)
        texto = self._chain_perfil.invoke({
            "sector_gics": sector_gics,
            "candidatos": ", ".join(candidatos),
            "nombre_empresa": nombre_empresa,
            "chunks_context": ctx,
        })
        if not isinstance(texto, str):
            texto = str(texto)
        if not texto.startswith(_HEADING):
            texto = f"{_HEADING}\n\n{texto}"

        logger.info(
            "Cap21Globales: %d candidatos, %d con web, %d chunks",
            len(candidatos), n_con_web, len(chunks),
        )

        return Cap21Globales(
            texto=texto,
            candidatos=candidatos,
            n_candidatos_con_web=n_con_web,
            retrieval_suficiente=True,
            chunks_usados=chunks,
        )
