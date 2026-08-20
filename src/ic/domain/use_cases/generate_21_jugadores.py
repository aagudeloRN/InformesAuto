"""UC-4: Orquestador Cap 2.1 — Jugadores Clave.

Coordina los tres sub-módulos (Globales, Regionales, Startups), deduplica cross-tier
(Global > Regional > Startup) y ensambla el texto completo de la sección 2.1.
"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace

from ic.data.repositories.entidad_repo import _clave_exclusion
from ic.domain.absent_data import build_absent_paragraph
from ic.domain.use_cases import checkpoint_hooks
from ic.domain.use_cases.generate_21_globales import Generate21Globales
from ic.domain.use_cases.generate_21_regionales import Generate21Regionales
from ic.domain.use_cases.generate_21_startups import Generate21Startups
from ic.shared.types import (
    Cap21Globales,
    Cap21Jugadores,
    Cap21Regionales,
    Cap21Startups,
    ChunkResult,
)

logger = logging.getLogger(__name__)

_HEADING = "## 2.1. Jugadores Clave"
_SECTION_LABEL = "2.1. Jugadores Clave"


def _dedup_regionales(globales: Cap21Globales, regionales: Cap21Regionales) -> Cap21Regionales:
    """Elimina de regionales las empresas en globales (prioridad Global > Regional)."""
    claves_globales = {_clave_exclusion(n) for n in globales.candidatos}
    empresas_filtradas = [
        e for e in regionales.empresas_emis if _clave_exclusion(e) not in claves_globales
    ]
    if len(empresas_filtradas) == len(regionales.empresas_emis):
        return regionales
    return replace(regionales, empresas_emis=empresas_filtradas, n_con_emis=len(empresas_filtradas))


def _dedup_startups(
    globales: Cap21Globales | None,
    regionales: Cap21Regionales | None,
    startups: Cap21Startups,
) -> Cap21Startups:
    """Elimina de startups locales/internacionales las empresas de niveles superiores."""
    claves_superiores: set[str] = set()
    if globales:
        claves_superiores.update(_clave_exclusion(n) for n in globales.candidatos)
    if regionales:
        claves_superiores.update(_clave_exclusion(n) for n in regionales.empresas_emis)

    locales_filtrados = [
        n for n in startups.locales if _clave_exclusion(n) not in claves_superiores
    ]
    intl_filtrados = [
        n for n in startups.internacionales if _clave_exclusion(n) not in claves_superiores
    ]
    if (
        len(locales_filtrados) == len(startups.locales)
        and len(intl_filtrados) == len(startups.internacionales)
    ):
        return startups
    return replace(startups, locales=locales_filtrados, internacionales=intl_filtrados)


class Generate21Jugadores:
    def __init__(
        self,
        gen_globales: Generate21Globales,
        gen_regionales: Generate21Regionales,
        gen_startups: Generate21Startups,
    ) -> None:
        self._gen_globales = gen_globales
        self._gen_regionales = gen_regionales
        self._gen_startups = gen_startups

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        sector_gics: str,
        sector_gics_code: str | None,
        sectores_ancla: list[str],
        empresa_id: uuid.UUID | None,
        productos: str = "",
        cached_globales: Cap21Globales | None = None,
        cached_regionales: Cap21Regionales | None = None,
        cached_startups: Cap21Startups | None = None,
        # engine y run_key van en execute() (no en __init__) para que el llamador pueda usar
        # claves distintas por corrida: cache sectorial → f"sector_{code}_{sub}"; corrida principal
        # → ctx.run_key. Constructor injection haría imposible esta diferenciación (FR-012).
        engine=None,
        run_key: str | None = None,
    ) -> Cap21Jugadores:
        base_kwargs = dict(
            nombre_empresa=nombre_empresa,
            descripcion_empresa=descripcion_empresa,
            sector_gics=sector_gics,
            sector_gics_code=sector_gics_code,
            empresa_id=empresa_id,
        )

        globales: Cap21Globales | None = cached_globales
        regionales: Cap21Regionales | None = cached_regionales
        startups: Cap21Startups | None = cached_startups

        # Ejecutar sub-módulos no cacheados en paralelo
        pendientes: dict[str, object] = {}
        if globales is None:
            pendientes["globales"] = self._gen_globales
        if regionales is None:
            pendientes["regionales"] = self._gen_regionales
        if startups is None:
            pendientes["startups"] = self._gen_startups

        if pendientes:
            with ThreadPoolExecutor(max_workers=len(pendientes)) as executor:
                futures = {}
                for nombre, gen in pendientes.items():
                    if nombre == "globales":
                        fut = executor.submit(gen.execute, **base_kwargs, productos=productos)
                    elif nombre == "regionales":
                        fut = executor.submit(gen.execute, **base_kwargs)
                    else:
                        fut = executor.submit(
                            gen.execute, **base_kwargs, sectores_ancla=sectores_ancla
                        )
                    futures[fut] = nombre

                for fut in as_completed(futures):
                    nombre = futures[fut]
                    try:
                        resultado = fut.result()
                    except Exception as exc:
                        logger.error("Sub-módulo %s falló: %s", nombre, exc)
                        resultado = None
                    if nombre == "globales":
                        globales = resultado
                        checkpoint_hooks.save_cap(engine, run_key, "cap2_21_globales", globales)
                    elif nombre == "regionales":
                        regionales = resultado
                        checkpoint_hooks.save_cap(engine, run_key, "cap2_21_regionales", regionales)
                    else:
                        startups = resultado
                        checkpoint_hooks.save_cap(engine, run_key, "cap2_21_startups", startups)

        # Deduplicación cross-tier (Global > Regional > Startup)
        if (
            globales and globales.retrieval_suficiente
            and regionales and regionales.retrieval_suficiente
        ):
            regionales = _dedup_regionales(globales, regionales)
        if startups and startups.retrieval_suficiente:
            startups = _dedup_startups(globales, regionales, startups)

        # Verificar si todos fallan
        todos_ausentes = all(
            obj is None or not obj.retrieval_suficiente
            for obj in (globales, regionales, startups)
        )

        if todos_ausentes:
            texto = (
                f"{_HEADING}\n\n"
                + build_absent_paragraph(
                    _SECTION_LABEL,
                    "No se encontraron fuentes suficientes para ningún sub-módulo "
                    "(Referentes Globales, Regionales ni Startups). "
                    "Incorpore informes EMIS, datos de StartIA y conexión a internet "
                    "para regenerar",
                )
            )
            return Cap21Jugadores(
                texto=texto,
                globales=globales,
                regionales=regionales,
                startups=startups,
                retrieval_suficiente=False,
            )

        # Ensamblar texto
        partes = [_HEADING, ""]
        if globales and globales.retrieval_suficiente:
            partes.append(globales.texto)
            partes.append("")
        if regionales and regionales.retrieval_suficiente:
            partes.append(regionales.texto)
            partes.append("")
        if startups and startups.retrieval_suficiente:
            partes.append(startups.texto)

        texto = "\n".join(partes).rstrip()

        # Agregar chunks
        todos_chunks: list[ChunkResult] = []
        for obj in (globales, regionales, startups):
            if obj and obj.chunks_usados:
                todos_chunks.extend(obj.chunks_usados)

        logger.info("Cap21Jugadores ensamblado: retrieval_suficiente=True")

        return Cap21Jugadores(
            texto=texto,
            globales=globales,
            regionales=regionales,
            startups=startups,
            retrieval_suficiente=True,
            chunks_usados=todos_chunks,
        )
