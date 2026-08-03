"""Ganchos de checkpoint --resume del pipeline (T22.3, DT-030).

Funciones compartidas por el orquestador (generate_informe) y la paralelización N1
(generate_n1). Aíslan el acceso a data/ (repositorio + migración) del código de
dominio; la serialización pura vive en domain/checkpoint_serde. Best-effort: un fallo
de persistencia nunca aborta la corrida (solo se pierde la capacidad de reanudar).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)


def load(ctx: _PipelineContext) -> None:
    """Si --resume, puebla ctx.checkpoint con los capítulos ya persistidos."""
    if not ctx.params.resume:
        return
    from ic.data.database import SessionLocal, engine
    from ic.data.models.checkpoint import ensure_checkpoint_table
    from ic.data.repositories.checkpoint_repo import CheckpointRepository

    try:
        ensure_checkpoint_table(engine)
        with SessionLocal() as db:
            ctx.checkpoint = CheckpointRepository(db).load_capitulos(ctx.run_key)
        if ctx.checkpoint:
            logger.info(
                "Resume: %d capítulos recuperados del checkpoint (%s): %s",
                len(ctx.checkpoint), ctx.run_key, ", ".join(sorted(ctx.checkpoint)),
            )
        else:
            logger.info("Resume: sin checkpoint previo para %s — corrida completa", ctx.run_key)
    except Exception:
        logger.warning("No se pudo cargar el checkpoint — corrida completa", exc_info=True)
        ctx.checkpoint = {}


def restore(ctx: _PipelineContext, nombre: str):
    """Devuelve el capítulo persistido (deserializado) o None si no está / está corrupto."""
    payload = ctx.checkpoint.get(nombre)
    if payload is None:
        return None
    try:
        from ic.domain.checkpoint_serde import deserialize_cap
        return deserialize_cap(payload)
    except Exception:
        logger.warning("Checkpoint de '%s' corrupto — se recomputa", nombre, exc_info=True)
        return None


def save(ctx: _PipelineContext, nombre: str, obj) -> None:
    """Persiste el capítulo generado para poder reanudar (best-effort)."""
    if obj is None:
        return
    from ic.data.database import SessionLocal, engine
    from ic.data.models.checkpoint import ensure_checkpoint_table
    from ic.data.repositories.checkpoint_repo import CheckpointRepository
    from ic.domain.checkpoint_serde import serialize_cap

    try:
        ensure_checkpoint_table(engine)
        with SessionLocal() as db:
            CheckpointRepository(db).save_capitulo(ctx.run_key, nombre, serialize_cap(obj))
    except Exception:
        logger.warning("No se pudo persistir checkpoint de '%s'", nombre, exc_info=True)


def commit_best(ctx: _PipelineContext, nombre: str, fresh):
    """Persiste el MEJOR capítulo (keep-best) y devuelve el que debe usar el informe (fallback).

    - Caché durable por `(empresa, ciiu)`: no lo borra la corrida; guarda el de mayor completitud
      (`score_capitulo`) → un capítulo degradado no pisa uno bueno.
    - Fallback anti-regresión: si el fresco está **claramente degradado** frente al cacheado
      (score < `_FALLBACK_RATIO`× el cacheado), devuelve el cacheado para el informe actual; si no,
      el fresco. Best-effort: cualquier fallo de BD → devuelve el fresco y no rompe la corrida.

    Con `ctx.params.use_cache=False` se comporta como el `save` clásico (a ciegas, devuelve el
    fresco) → invariante para quien pida corrida sin caché.
    """
    if fresh is None:
        return fresh
    if not getattr(ctx.params, "use_cache", True):
        save(ctx, nombre, fresh)
        return fresh

    from ic.data.database import SessionLocal, engine
    from ic.data.models.checkpoint import ensure_checkpoint_table
    from ic.data.repositories.checkpoint_repo import CheckpointRepository
    from ic.domain.checkpoint_serde import deserialize_cap, serialize_cap
    from ic.domain.kb.completitud import elegir_mejor

    try:
        ensure_checkpoint_table(engine)
        with SessionLocal() as db:
            repo = CheckpointRepository(db)
            payload = repo.get_capitulo(ctx.run_key, nombre)
            cached = None
            if payload is not None:
                try:
                    cached = deserialize_cap(payload)
                except Exception:
                    cached = None  # cacheado corrupto → se ignora
            para_informe, para_cache = elegir_mejor(fresh, cached)
            if para_informe is cached:
                logger.warning(
                    "Fallback de caché: '%s' fresco degradado → se usa el cacheado en el informe",
                    nombre,
                )
            repo.save_capitulo(ctx.run_key, nombre, serialize_cap(para_cache))
    except Exception:
        logger.warning("commit_best: fallo de caché para '%s' — se usa el fresco", nombre)
        return fresh
    return para_informe


def clear(ctx: _PipelineContext) -> None:
    """Borra el checkpoint tras completar la corrida con éxito."""
    if not ctx.run_key:
        return
    from ic.data.database import SessionLocal
    from ic.data.repositories.checkpoint_repo import CheckpointRepository

    try:
        with SessionLocal() as db:
            CheckpointRepository(db).clear(ctx.run_key)
    except Exception:
        logger.warning("No se pudo limpiar el checkpoint de %s", ctx.run_key, exc_info=True)
