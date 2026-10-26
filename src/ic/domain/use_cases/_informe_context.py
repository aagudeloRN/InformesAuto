"""Contexto, parametros y preparacion de infraestructura del informe (DT-039)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ic.domain.checkpoint_serde import make_run_key
from ic.shared.config import Settings

logger = logging.getLogger(__name__)

StepCallback = Callable[[int, int, str], None]

# Estimacion de latencia de una busqueda web (ms) para reportar el ahorro de cache (T17.1).
_AVG_WEB_MS = 800.0


@dataclass
class InformeParams:
    empresa: str
    ciiu: str | None = None
    output_path: str | None = None
    resume: bool = False
    use_cache: bool = True
    refresh: bool = False
    selfreview: bool | None = None
    discover_globales: bool | None = None
    anclaje_local: bool | None = None
    seccion21_determinista: bool | None = None
    caps_incluidos: set[str] | None = None
    competidores_curados: dict[str, list[str]] | list[str] | set[str] | None = None


@dataclass
class InformeResult:
    ruta_docx: str
    n_referencias: int
    costo_usd: float
    tokens_in: int
    tokens_out: int
    tiempo_total_s: float
    cost_records: list
    ruta_pdf: str | None = None
    cache_web_hits: int = 0
    cache_web_misses: int = 0
    cache_oal_hits: int = 0
    cache_oal_misses: int = 0


@dataclass
class _PipelineContext:
    params: InformeParams
    settings: Any
    step_fn: Any
    total_start: float
    session_id: str = ""
    llm: Any = None
    api_llm: Any = None
    api_llm_alt: Any = None
    api_llm_synth: Any = None
    cap1_llms: list = field(default_factory=list)
    embedder: Any = None
    web: Any = None
    tracker: Any = None
    intro_chain: Any = None
    output_path: str = ""
    empresa: Any = None
    gics: Any = None
    cap: Any = None
    cap_mercado: Any = None
    cap_tend: Any = None
    cap_eco: Any = None
    cap_conv: Any = None
    cap_acc: Any = None
    cap22_division: Any = None
    resumen: Any = None
    cache_web_counter: Any = None
    cache_oal_counter: Any = None
    empresa_id: Any = None
    run_key: str = ""
    checkpoint: dict = field(default_factory=dict)
    _enriched_sectors: set[str] = field(default_factory=set)
    eventos_enriquecimiento: list[Any] = field(default_factory=list)


def setup_pipeline_infra(
    settings: Settings, params: InformeParams, step_fn: Any, total_start: float
) -> _PipelineContext:
    from ic.domain.chains.chain_intro import build_chain_intro
    from ic.infrastructure.llm.gateway import (
        CostTracker,
        build_llm,
        build_resilient_api_llm,
    )
    from ic.infrastructure.retrieval.embedder import Embedder
    from ic.infrastructure.sources.cached_connector import CacheCounter
    from ic.infrastructure.sources.web_connector import WebConnector

    # Aplicar overrides de modulos desde InformeParams (None = respetar el .env/Settings).
    _overrides = {
        k: v
        for k, v in {
            "selfreview_enabled": params.selfreview,
            "discover_globales_enabled": params.discover_globales,
            "anclaje_local_enabled": params.anclaje_local,
            "seccion21_determinista_enabled": params.seccion21_determinista,
        }.items()
        if v is not None
    }
    s = settings.model_copy(update=_overrides) if _overrides else settings
    tracker = CostTracker(budget_limit=s.llm_budget_limit_usd)
    resilient_llm = (
        build_resilient_api_llm(s, cost_tracker=tracker) if s.openrouter_api_key else None
    )
    resilient_synth_llm = resilient_llm
    if s.llm_api_synth_provider == "gemini" and s.gemini_api_key:
        try:
            resilient_synth_llm = build_resilient_api_llm(s, tiers=["synth"], cost_tracker=tracker)
        except ValueError:
            resilient_synth_llm = resilient_llm
    llm = build_llm(s, cost_tracker=tracker)
    cap1_llms = [m for m in [resilient_llm, llm] if m is not None]
    slug = params.empresa.replace(" ", "_").replace(".", "").lower()
    output_path = params.output_path or f"./output/{slug}_informe.docx"
    if not output_path.lower().endswith(".docx"):
        output_path += ".docx"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    import uuid

    return _PipelineContext(
        params=params,
        settings=s,
        step_fn=step_fn,
        total_start=total_start,
        session_id=uuid.uuid4().hex,
        llm=llm,
        api_llm=resilient_llm,
        api_llm_alt=None,
        api_llm_synth=resilient_synth_llm,
        cap1_llms=cap1_llms,
        embedder=Embedder(s),
        web=WebConnector(s),
        tracker=tracker,
        intro_chain=build_chain_intro(resilient_llm) if resilient_llm else None,
        output_path=output_path,
        cache_web_counter=CacheCounter(),
        cache_oal_counter=CacheCounter(),
        run_key=make_run_key(params.empresa, params.ciiu),
    )


def sweep_stale_web(ctx: _PipelineContext) -> None:
    """Barre chunks web meurfanot de corridas previas (crash) antes de empezar (T14.5)."""
    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository

    try:
        with SessionLocal() as db:
            n = EmbeddingRepository(db).sweep_stale_web_sessions(ctx.session_id)
            if n:
                logger.info("Barrido de %d chunks web meurfanot de sesiones previas", n)
    except Exception:
        logger.warning("No se pudo barrer chunks web meurfanot", exc_info=True)


def promote_cited_web(ctx: _PipelineContext, chunks_usados: list) -> None:
    """Promueve solo los chunks web citados; borra el resto de la sesion (T14.5)."""
    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository

    cited_ids = [
        c.chunk_id
        for c in chunks_usados
        if getattr(c, "fuente_tipo", None) == "web" and getattr(c, "chunk_id", None)
    ]
    try:
        with SessionLocal() as db:
            borrados, promovidos = EmbeddingRepository(db).promote_cited_web(
                ctx.session_id, cited_ids
            )
            logger.info(
                "Persistencia web: %d chunks promovidos (citados), %d descartados",
                promovidos,
                borrados,
            )
    except Exception:
        logger.warning("No se pudo promover/purgar chunks web de la sesion", exc_info=True)
