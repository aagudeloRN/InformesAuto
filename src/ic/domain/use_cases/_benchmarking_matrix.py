"""Helpers para cache sectorial y enriquecimiento del benchmarking (Capitulo 2)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from ic.infrastructure.llm.gateway import OllamaGatewayLLM
    from ic.infrastructure.retrieval.pgvector_store import PgVectorStore
    from ic.infrastructure.sources.web_connector import WebConnector

logger = logging.getLogger(__name__)


def load_sector_cache(engine: Any, sector_run_key: str):
    """Carga los tres sub-modulos de 2.1 desde el cache sectorial (SC-005, T037)."""
    try:
        from sqlalchemy.orm import Session

        from ic.data.models.checkpoint import ensure_checkpoint_table
        from ic.data.repositories.checkpoint_repo import CheckpointRepository
        from ic.domain.checkpoint_serde import deserialize_cap

        ensure_checkpoint_table(engine)
        with Session(engine) as db:
            repo = CheckpointRepository(db)
            caps = repo.load_capitulos(sector_run_key)

        def _deserialize(nombre: str):
            payload = caps.get(nombre)
            if payload is None:
                return None
            try:
                return deserialize_cap(payload)
            except Exception:
                return None

        globales = _deserialize("cap2_21_globales")
        regionales = _deserialize("cap2_21_regionales")
        startups = _deserialize("cap2_21_startups")
        return globales, regionales, startups
    except Exception:
        logger.debug("Cache sectorial no disponible para %r", sector_run_key, exc_info=True)
        return None, None, None


def identificar_entidades(
    entidades_chain: Any | None,
    chunks: list[Any],
    sector_gics: str,
) -> list[str]:
    """Identifica entidades competidoras en los chunks recuperados."""
    if entidades_chain is None:
        return []
    try:
        evidencia = "\n\n".join(c.content for c in chunks[:10])
        res = entidades_chain.invoke({"evidencia": evidencia, "sector_gics": sector_gics})
        entidades = [e.strip() for e in res.strip().split(",") if e.strip()][:10]
        return entidades
    except Exception as exc:
        logger.warning("Error identificando entidades: %s", exc)
        return []


def buscar_por_entidad(
    web_connector: WebConnector | None,
    store: PgVectorStore,
    entidades: list[str],
    sector_gics: str,
) -> None:
    """Realiza busquedas web dirigidas por entidad e ingesta los resultados."""
    if not web_connector or not entidades:
        return
    for ent in entidades:
        q = f"{ent} {sector_gics} productos portafolio presencia competidor"
        try:
            res = web_connector.search(q, search_depth="basic")
            if res:
                store.ingest(
                    texts=[r.content for r in res],
                    fuente_tipo="web",
                    urls=[r.url for r in res],
                )
        except Exception as exc:
            logger.warning("Error en busqueda web para %s: %s", ent, exc)


def enriquecer_globales_web(
    web_connector: WebConnector | None,
    llm: OllamaGatewayLLM | None,
    engine: Engine | None,
    fichas_kb: dict[str, dict[str, str]],
    globales: list[str],
    sector_gics: str,
    sector_gics_code: str | None = None,
) -> dict[str, dict[str, str]]:
    """Enriquece campos de ficha de empresas globales via web."""
    if not web_connector or not globales or engine is None:
        return {}
    from ic.domain.chains.chain_03b_ficha_fields import build_chain_ficha_fields
    from ic.domain.kb.ficha_parser import parse_fichas_competidores

    chain_fields = build_chain_ficha_fields(llm) if llm else None
    if chain_fields is None:
        return {}
    nuevas: dict[str, dict[str, str]] = {}
    for empresa in globales[:3]:
        if empresa in fichas_kb and len(fichas_kb[empresa]) >= 4:
            continue
        q = f"{empresa} {sector_gics} overview products markets business model"
        try:
            results = web_connector.search(q, search_depth="basic")
            if not results:
                continue
            texto_web = "\n\n".join(r.content for r in results[:3])
            campos_json = chain_fields.invoke({"nombre": empresa, "evidencia": texto_web})
            fichas_parsed = parse_fichas_competidores(f"### {empresa}\n{campos_json}")
            if fichas_parsed and fichas_parsed[0].campos:
                nuevas[empresa] = fichas_parsed[0].campos
        except Exception as exc:
            logger.warning("Error enriqueciendo %s: %s", empresa, exc)
    return nuevas
