"""Wiring de Cap 2.2 en el DAG N1 (extraído de generate_n1.py — T029).

Expone `build_fn_cap2_with_22` que decora `_fn_cap2` para ejecutar también
`Generate22Division` después de que Cap 2.1 haya sido generado y persistido
en checkpoints por `Generate21Jugadores`.

Estrategia de captura (T025):
  Cap21Jugadores se reconstruye desde los checkpoints de sub-módulo
  (`cap2_21_globales`, `cap2_21_regionales`, `cap2_21_startups`) guardados por
  `Generate21Jugadores` durante la ejecución de `_fn_cap2`. Esto evita tener
  que parchear el interior del closure `_fn_cap2`.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)

_SUB_KEYS = ("cap2_21_globales", "cap2_21_regionales", "cap2_21_startups")


def _reconstruct_cap21(ctx: _PipelineContext):
    """Carga y reconstruye Cap21Jugadores desde checkpoints de sub-módulo.

    Devuelve None si no se puede cargar ningún sub-módulo (cap22 se omite).
    """
    from ic.data.database import SessionLocal
    from ic.data.database import engine as db_engine
    from ic.data.models.checkpoint import ensure_checkpoint_table
    from ic.data.repositories.checkpoint_repo import CheckpointRepository
    from ic.domain.checkpoint_serde import deserialize_cap
    from ic.shared.types import Cap21Globales, Cap21Jugadores, Cap21Regionales, Cap21Startups

    try:
        ensure_checkpoint_table(db_engine)
        with SessionLocal() as db:
            repo = CheckpointRepository(db)
            globales: Cap21Globales | None = None
            regionales: Cap21Regionales | None = None
            startups: Cap21Startups | None = None
            for key in _SUB_KEYS:
                payload = repo.get_capitulo(ctx.run_key, key)
                if payload is None:
                    continue
                try:
                    obj = deserialize_cap(payload)
                except Exception:
                    continue
                if key == "cap2_21_globales":
                    globales = obj
                elif key == "cap2_21_regionales":
                    regionales = obj
                else:
                    startups = obj

        retrieval_ok = any(
            obj is not None and obj.retrieval_suficiente
            for obj in (globales, regionales, startups)
        )
        if not retrieval_ok and globales is None and regionales is None and startups is None:
            return None

        return Cap21Jugadores(
            texto="",
            globales=globales,
            regionales=regionales,
            startups=startups,
            retrieval_suficiente=retrieval_ok,
        )
    except Exception:
        logger.warning(
            "Cap 2.2: no se pudo reconstruir Cap21Jugadores desde checkpoints", exc_info=True
        )
        return None


def build_fn_cap2_with_22(fn_cap2_original, ctx: _PipelineContext):
    """Devuelve un decorador de `fn_cap2` que también ejecuta Generate22Division.

    El resultado de cap22 se asigna a `ctx.cap22_division` (best-effort).
    """

    def _fn_cap2_with_22(store, web, oal):
        from ic.data.database import SessionLocal
        from ic.data.database import engine as db_engine
        from ic.data.models.checkpoint import ensure_checkpoint_table
        from ic.data.repositories.checkpoint_repo import CheckpointRepository
        from ic.domain.chains.chain_cap2_22_division import build_chain_cap2_22_division
        from ic.domain.checkpoint_serde import deserialize_cap
        from ic.domain.use_cases.generate_22_division import Generate22Division

        cap = fn_cap2_original(store, web, oal)

        # --- Resume: intentar cargar checkpoint previo ---
        checkpoint = getattr(ctx, "checkpoint", None) or {}
        prior_payload = checkpoint.get("cap_2_2")
        if prior_payload is not None:
            try:
                ctx.cap22_division = deserialize_cap(prior_payload)
                logger.info("Cap 2.2: restaurado desde checkpoint (resume)")
                return cap
            except Exception:
                logger.warning("Cap 2.2: checkpoint previo inválido — regenerando", exc_info=True)

        cap21 = _reconstruct_cap21(ctx)
        if cap21 is None:
            logger.warning("Cap 2.2: Cap21Jugadores no disponible — se omite la generación")
            return cap

        llm_22 = ctx.api_llm or ctx.llm
        if llm_22 is None:
            return cap

        try:
            ensure_checkpoint_table(db_engine)
            with SessionLocal() as db_22:
                chain_22 = build_chain_cap2_22_division(llm_22)
                uc_22 = Generate22Division(
                    chain=chain_22,
                    checkpoint_repo=CheckpointRepository(db_22),
                )
                cap22 = uc_22(
                    run_key=ctx.run_key,
                    cap21=cap21,
                    empresa=ctx.empresa,
                )
                ctx.cap22_division = cap22
                logger.info(
                    "Cap 2.2 generado: %d empresas, retrieval_suficiente=%s",
                    cap22.n_empresas_procesadas,
                    cap22.retrieval_suficiente,
                )
        except Exception:  # noqa: BLE001 — cap22 es best-effort; nunca rompe la corrida
            logger.warning("Cap 2.2: generación falló (best-effort)", exc_info=True)
            from ic.domain.kb.seccion22_assembler import absent_paragraph
            from ic.shared.types import Cap22Division

            ctx.cap22_division = Cap22Division(
                texto=absent_paragraph(),
                clasificaciones=[],
                n_empresas_procesadas=0,
                retrieval_suficiente=False,
            )

        return cap

    return _fn_cap2_with_22
