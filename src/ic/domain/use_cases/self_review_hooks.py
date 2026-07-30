"""Cableado del loop de auto-revisión en el pipeline (DT-059/T3).

Aísla el acceso a LLM/store/red del loop puro (`domain/eval/self_review`), igual que
`checkpoint_hooks` aísla el acceso a BD. Expone dos sabores (PROPUESTA §4):

- `review_web_cap` (Caps 2/3/4): el revisor **re-busca** por los faltantes del juez y por los
  competidores del KB (Reflexion con herramientas, reusa el anclaje de DT-056), re-recupera y
  re-sintetiza con la evidencia enriquecida.
- `review_integration_cap` (Caps 5/6): el revisor **solo re-sintetiza** sobre la evidencia ya
  recuperada (sin nuevo retrieval; los caps de integración consumen los N1 ya refinados).

Invariante: con `selfreview_enabled=False` (default) el capítulo se devuelve intacto y el loop
no se invoca. Fallo suave: cualquier excepción del loop/persistencia devuelve el mejor cap
conocido sin abortar la corrida (patrón checkpoint).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace

from ic.domain.chains.chain_03_benchmarking import format_chunks_as_context
from ic.domain.chains.chain_judge import build_chain_judge
from ic.domain.chains.chain_revise import build_chain_revise
from ic.domain.eval.rubric_score import RubricScore, parse_rubric_score
from ic.domain.eval.self_review import RevisionTrace, run_self_review

logger = logging.getLogger(__name__)

SABOR_WEB = "web"
SABOR_INTEGRACION = "integracion"

# Cota de re-búsquedas dirigidas por iteración (latencia/coste acotados).
_MAX_QUERIES_FALTANTES = 3
_MAX_QUERIES_KB = 2


def _format_faltantes(faltantes: list[str]) -> str:
    return "\n".join(f"- {f}" for f in faltantes) if faltantes else "- (sin carencias específicas)"


def _run_review(
    *,
    settings,
    judge_llm,
    capitulo_nombre: str,
    criterios: str,
    cap_obj,
    sabor: str,
    revise_fn: Callable[[object, list[str]], object],
    run_key: str,
):
    """Núcleo compartido: juzga el cap y, si no pasa el gate, corre el loop guardar-el-mejor."""
    if not getattr(settings, "selfreview_enabled", False):
        return cap_obj
    if cap_obj is None or not getattr(cap_obj, "retrieval_suficiente", False):
        return cap_obj

    judge_chain = build_chain_judge(judge_llm)

    def judge_fn(cap) -> RubricScore:
        raw = judge_chain.invoke({
            "capitulo_nombre": capitulo_nombre,
            "criterios_capitulo": criterios,
            "texto_capitulo": getattr(cap, "texto", ""),
        })
        return parse_rubric_score(raw)

    try:
        mejor_cap, trace = run_self_review(
            generate_fn=lambda: cap_obj,
            judge_fn=judge_fn,
            revise_fn=revise_fn,
            min_total=getattr(settings, "selfreview_min_total", 11),
            max_iter=getattr(settings, "selfreview_max_iter", 3),
        )
    except Exception:  # noqa: BLE001 — la auto-revisión es un boost; nunca rompe la corrida.
        logger.warning("Auto-revisión falló para '%s' — se conserva el cap original",
                       capitulo_nombre, exc_info=True)
        return cap_obj

    _persist_trace(run_key, capitulo_nombre, sabor, trace)
    logger.info(
        "Auto-revisión [%s/%s]: %d→%d en %d iter (%s)",
        capitulo_nombre, sabor, trace.score_inicial, trace.score_final,
        trace.n_iteraciones, trace.motivo_parada,
    )
    return mejor_cap


def _persist_trace(run_key: str, capitulo: str, sabor: str, trace: RevisionTrace) -> None:
    """Persiste la traza de revisión (trazabilidad TIER 4). Best-effort: nunca aborta la corrida."""
    from ic.data.database import SessionLocal, engine
    from ic.data.models.revision_capitulo import ensure_revisiones_tables
    from ic.data.repositories.revision_repo import RevisionRepository

    try:
        ensure_revisiones_tables(engine)
        with SessionLocal() as db:
            RevisionRepository(db).save_revision(
                run_key=run_key,
                capitulo=capitulo,
                sabor=sabor,
                n_iteraciones=trace.n_iteraciones,
                iter_ganadora=trace.iter_ganadora,
                score_inicial=trace.score_inicial,
                score_final=trace.score_final,
                motivo_parada=trace.motivo_parada,
                dimensiones=dict(trace.mejor.dimensiones),
                faltantes=list(trace.mejor.faltantes),
            )
    except Exception:  # noqa: BLE001 — la trazabilidad es best-effort (patrón checkpoint).
        logger.warning("No se pudo persistir la traza de auto-revisión de '%s'",
                       capitulo, exc_info=True)


def review_web_cap(
    *,
    settings,
    llm,
    capitulo_nombre: str,
    criterios: str,
    cap_obj,
    run_key: str,
    store,
    web,
    sector_gics: str,
    sector_gics_code: str | None,
    empresa_id=None,
    retrieval_query: str,
    kb_competidores: list[str] | None = None,
):
    """Sabor web (Caps 2/3/4): re-busca por faltantes + KB, re-recupera, re-sintetiza."""
    revise_chain = build_chain_revise(llm)
    kb = list(kb_competidores or [])

    def revise_fn(cap, faltantes: list[str]):
        # Reflexion con herramientas: cada carencia del juez dispara una búsqueda dirigida.
        for faltante in faltantes[:_MAX_QUERIES_FALTANTES]:
            _ingest_query(store, web, f"{sector_gics} {faltante}")
        # Reusa el anclaje del KB (DT-056): perfiles de competidores canónicos del sector.
        for nombre in kb[:_MAX_QUERIES_KB]:
            _ingest_query(
                store, web,
                f"{nombre} {sector_gics} perfil empresa portafolio productos cuota de mercado",
            )
        chunks = store.search(
            retrieval_query, sector_gics=sector_gics_code, empresa_id=empresa_id,
        )
        nuevo_texto = revise_chain.invoke({
            "capitulo_nombre": capitulo_nombre,
            "criterios_capitulo": criterios,
            "borrador_actual": getattr(cap, "texto", ""),
            "faltantes": _format_faltantes(faltantes),
            "evidencia": format_chunks_as_context(chunks),
        })
        return replace(cap, texto=nuevo_texto, chunks_usados=chunks, n_chunks_usados=len(chunks))

    return _run_review(
        settings=settings, judge_llm=llm, capitulo_nombre=capitulo_nombre,
        criterios=criterios, cap_obj=cap_obj, sabor=SABOR_WEB, revise_fn=revise_fn,
        run_key=run_key,
    )


def review_integration_cap(
    *,
    settings,
    llm,
    capitulo_nombre: str,
    criterios: str,
    cap_obj,
    run_key: str,
):
    """Sabor integración (Caps 5/6): solo re-sintetiza sobre la evidencia ya recuperada."""
    revise_chain = build_chain_revise(llm)

    def revise_fn(cap, faltantes: list[str]):
        chunks = getattr(cap, "chunks_usados", []) or []
        nuevo_texto = revise_chain.invoke({
            "capitulo_nombre": capitulo_nombre,
            "criterios_capitulo": criterios,
            "borrador_actual": getattr(cap, "texto", ""),
            "faltantes": _format_faltantes(faltantes),
            "evidencia": format_chunks_as_context(chunks),
        })
        return replace(cap, texto=nuevo_texto)  # sin nuevo retrieval (solo re-síntesis)

    return _run_review(
        settings=settings, judge_llm=llm, capitulo_nombre=capitulo_nombre,
        criterios=criterios, cap_obj=cap_obj, sabor=SABOR_INTEGRACION, revise_fn=revise_fn,
        run_key=run_key,
    )


def _ingest_query(store, web, query: str) -> None:
    """Búsqueda web dirigida + ingesta al índice (mismo patrón que GenerateBenchmarking)."""
    results = web.search(query, search_depth="advanced")
    if results:
        store.ingest(
            texts=[r.content for r in results],
            fuente_tipo="web",
            urls=[r.url for r in results],
        )
