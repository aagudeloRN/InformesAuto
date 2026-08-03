"""Paralelización N1: Caps 2 (Benchmarking), 3 (Tendencias) y 4 (Ecosistema).

Extraído de generate_informe.py (DT-004) para mantener archivos < 300 líneas.
El orquestador (GenerateInforme._run_n1) delega aquí sin cambiar la interfaz pública.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ic.domain.use_cases.generate_informe import _PipelineContext

logger = logging.getLogger(__name__)


def run_n1_parallel(ctx: _PipelineContext) -> None:
    """Ejecuta Caps 2/3/4 en paralelo + párrafos introductivos N1."""
    from ic.data.database import SessionLocal
    from ic.data.models.entidad import (
        ALCANCE_GLOBAL,
        ESTADO_CANDIDATO,
        ESTADO_VERIFICADO,
        FUENTE_LLM,
        FUENTE_WEB,
        SEGMENTO_STARTUP,
        TIPO_COMPETIDOR,
        ensure_entidades_tables,
    )
    from ic.data.repositories.embedding_repo import EmbeddingRepository
    from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow
    from ic.domain.chains.chain_02b_entidades import build_chain_entidades
    from ic.domain.chains.chain_02c_pares_globales import build_chain_pares_globales
    from ic.domain.chains.chain_03_benchmarking import build_chain_03
    from ic.domain.chains.chain_03b_mercado import build_chain_03b
    from ic.domain.chains.chain_04_tendencias import build_chain_04
    from ic.domain.chains.chain_05_ecosistema import build_chain_05
    from ic.domain.chains.chain_judge import CRITERIOS_CAPITULO
    from ic.domain.kb.ficha_parser import parse_fichas_competidores
    from ic.domain.kb.relevance import format_fichas_conocidas, format_jugadores_locales
    from ic.domain.use_cases.discover_globales import DiscoverGlobales
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
    from ic.domain.use_cases.generate_ecosistema import GenerateEcosistema
    from ic.domain.use_cases.generate_mercado import GenerateMercado
    from ic.domain.use_cases.generate_tendencias import GenerateTendencias
    from ic.domain.use_cases.self_review_hooks import review_web_cap
    from ic.infrastructure.llm.gateway import build_api_llm
    from ic.infrastructure.ner.entity_recognizer import normalize_entity
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.cached_connector import (
        CachedOpenAlexConnector,
        CachedWebConnector,
    )
    from ic.infrastructure.sources.openalex_connector import OpenAlexConnector
    from ic.shared.constants.gics_groups import extract_gics_code
    from ic.shared.text_productos import producto_terms

    ctx.step_fn(3, "N1 — Caps 2/3/4 en paralelo")
    e, g, s = ctx.params.empresa, ctx.gics.grupo_gics, ctx.settings
    g_code = extract_gics_code(g)
    # DT-063: la señal de precisión del descubrimiento son los PRODUCTOS/SERVICIOS de la empresa
    # (Cap 1), no un sub-código GICS frágil. El grupo GICS queda como red de recall + guardrail; el
    # solape producto↔candidato ordena globales y locales. Vacío → fallback a nivel grupo.
    productos = ctx.empresa.productos_servicios
    productos_terms = producto_terms(productos)

    def _descubrir_globales(store, web) -> None:
        """DT-062/DT-063: siembra globales LLM corroborados por web. Best-effort; nunca rompe.

        Guard de coste **por producto** (DT-063): el guard cuenta globales del grupo con SOLAPE de
        producto ≥1; si ya hay ≥8, no re-descubre (KB caliente para esos productos). El recall del
        LLM se steerea por los productos/servicios (no por un sub-código): una láctea recibe
        globales de lácteos, no del grupo entero. Al sembrar un corroborado se guarda su **perfil de
        producto** (`productos_perfil`) para que el anclaje futuro lo filtre por solape.
        Corroborado → verificado/alcance=global; si no → candidato/fuente=llm no citable.
        """
        if not g_code:
            return
        try:
            with SessionLocal() as db_kb:
                ensure_entidades_tables(db_kb.get_bind())
                repo = EntidadRepository(db_kb)
                # El ranker global exige solape (require_overlap): `ya` ya son globales de ESTOS
                # productos. KB caliente para estos productos ⇒ no re-descubrir.
                ya = repo.list_competidores_by_sector(
                    g_code, productos_terms=productos_terms, alcance=ALCANCE_GLOBAL, limit=100
                )
                if len(ya) >= 8:
                    return

                def _seed(nombre: str, corroborado: bool, _hits: int) -> None:
                    estado = ESTADO_VERIFICADO if corroborado else ESTADO_CANDIDATO
                    eid = repo.upsert_entidad(EntidadRow(
                        nombre=nombre, nombre_normalizado=normalize_entity(nombre),
                        tipo=TIPO_COMPETIDOR, sector_gics=g_code,
                        alcance=ALCANCE_GLOBAL if corroborado else None, estado=estado,
                    ))
                    repo.add_atributo(
                        eid, "origen", "llm-corroborado" if corroborado else "llm",
                        FUENTE_LLM, estado=estado,
                    )
                    # DT-063: perfil de producto del global (re-rank por solape del anclaje).
                    if corroborado and productos:
                        repo.add_atributo(
                            eid, "productos_perfil", productos[:2000], FUENTE_LLM,
                            estado=ESTADO_VERIFICADO,
                        )

                DiscoverGlobales(
                    chain=build_chain_pares_globales(ctx.api_llm or ctx.llm),
                    web_connector=web, store=store,
                    min_corrob=s.discover_globales_min_corrob,
                ).discover(sector_gics=g, productos=productos, seed_repo_fn=_seed)
        except Exception:  # noqa: BLE001 — el descubrimiento es un boost; nunca rompe la corrida.
            logger.warning("Descubrimiento LLM de globales falló (sector %s)", g_code)

    # T16.0-B: cada thread abre su propia sesión y crea sus propios wrappers cached.
    # SQLAlchemy Session no es thread-safe — nunca compartir entre threads paralelos.
    def _store(fn):
        with SessionLocal() as db:
            store = PGVectorStore(ctx.embedder, EmbeddingRepository(db), s)
            store.session_id = ctx.session_id
            cached_web = CachedWebConnector(ctx.web, db, s, counter=ctx.cache_web_counter)
            cached_oal = CachedOpenAlexConnector(
                OpenAlexConnector(s), db, s, counter=ctx.cache_oal_counter
            )
            return fn(store, cached_web, cached_oal)

    def _persistir_fichas_ancladas(cap, kb_competidores, kb_locales) -> None:
        """DT-064/T3: persiste los campos de ficha de los competidores ANCLADOS (reuso sectorial).

        Solo entidades ya ancladas (globales + locales del KB) → no persiste competidores del RAG.
        Idempotente (add_atributo por entidad+clave+fuente); best-effort: nunca rompe la corrida.
        """
        if cap is None or not getattr(cap, "texto", ""):
            return
        anclados = {normalize_entity(n) for n in (*kb_competidores, *kb_locales)}
        if not anclados:
            return
        try:
            fichas = [
                f for f in parse_fichas_competidores(cap.texto)
                if normalize_entity(f.nombre) in anclados
            ]
            if not fichas:
                return
            with SessionLocal() as db_p:
                ensure_entidades_tables(db_p.get_bind())
                repo_p = EntidadRepository(db_p)
                for f in fichas:
                    ent_id = repo_p.get_id_by_nombre_sector(normalize_entity(f.nombre), g_code)
                    if ent_id is None:
                        continue
                    for clave, valor in f.campos.items():
                        repo_p.add_atributo(ent_id, clave, valor, FUENTE_WEB)
        except Exception:  # noqa: BLE001 — la persistencia de fichas es un boost; nunca rompe.
            logger.warning("No se pudieron persistir las fichas del Cap 2", exc_info=True)

    def _fn_cap2(store, web, _oal):
        # T22.4 (DT-054): cadena de identificación de entidades para búsqueda dirigida por
        # competidor (enriquece las fichas de 2.1 más allá de las queries a nivel sector).
        # DT-056/T3: anclar con la lista canónica del KB por sector (cierra causas A/E). Sesión
        # propia por thread; [] → comportamiento B1 (SQLAlchemy Session no es thread-safe).
        # DT-061b: la lista anclada es la de competidores de CLASE MUNDIAL → filtra alcance=global
        # (los jugadores locales grandes son otro componente, DT-050).
        # DT-062: descubrimiento LLM de globales corroborados por web (motor de recall del
        # componente de clase mundial). Flag OFF = anclaje solo con la semilla curada (DT-061b).
        if s.discover_globales_enabled:
            _descubrir_globales(store, web)
        kb_competidores: list[str] = []
        kb_locales: list[str] = []
        jugadores_locales_ctx = ""
        fichas_conocidas_ctx = ""
        try:
            with SessionLocal() as db_kb:
                ensure_entidades_tables(db_kb.get_bind())
                repo_kb = EntidadRepository(db_kb)
                kb_competidores = repo_kb.list_competidores_by_sector(
                    g_code or "", productos_terms=productos_terms, alcance=ALCANCE_GLOBAL
                )
                # DT-050/DT-063: anclaje del tier LOCAL (2.1.2 regionales + 2.1.3 startups) desde el
                # directorio, re-rankeado por solape de producto. Flag OFF → nada (invariante). No
                # diluye el global: el path global usa alcance=global con su propio método.
                if s.anclaje_local_enabled and g_code:
                    n = s.anclaje_local_top_n
                    regionales = repo_kb.list_locales_by_sector(
                        g_code, solo_establecidas=True, productos_terms=productos_terms, limit=n
                    )
                    startups = repo_kb.list_locales_by_sector(
                        g_code, segmento=SEGMENTO_STARTUP, productos_terms=productos_terms, limit=n
                    )
                    jugadores_locales_ctx = format_jugadores_locales(regionales, startups)
                    kb_locales = [r.nombre for r in (*regionales, *startups)]
                # DT-064/T4 + DT-065: pre-fill del prompt con los campos de ficha ya conocidos, de
                # los globales anclados (persistidos por T3) Y de los locales (data estructurada de
                # StartIA/EmpresasColombia mapeada a los campos de ficha) → el LLM escribe desde
                # hechos, no fabrica. Vacío → invariante.
                nombres_ficha = [*kb_competidores, *kb_locales]
                if g_code and nombres_ficha:
                    fichas_conocidas_ctx = format_fichas_conocidas(
                        repo_kb.list_ficha_atributos_by_sector(g_code, nombres_ficha)
                    )
        except Exception:  # noqa: BLE001 — el KB es un boost; nunca debe romper la corrida.
            logger.warning("No se pudo consultar el KB de competidores (sector %s)", g_code)
        # DT-064/T5: cadena de escalada = tier de API superior (synth = Nemotron Ultra). Se usa SOLO
        # ante negativa del LLM tras retry (coste acotado). Sin API key o tier no configurado → None
        # (invariante). El modelo vive en .env (ADR-002), no se hardcodea.
        escalation_chain = None
        if s.openrouter_api_key:
            tier = getattr(s, "benchmarking_escalation_tier", "synth")
            try:
                escalation_chain = build_chain_03(
                    build_api_llm(s, tier=tier, cost_tracker=ctx.tracker)
                )
            except Exception:  # noqa: BLE001 — sin tier de escalada la corrida sigue igual.
                logger.warning("No se pudo construir la cadena de escalada (tier=%s)", tier)
        cap = GenerateBenchmarking(
            chain=build_chain_03(ctx.api_llm or ctx.llm), store=store, web_connector=web,
            entidades_chain=build_chain_entidades(ctx.api_llm or ctx.llm),
            kb_competidores=kb_competidores, kb_locales=kb_locales,
            jugadores_locales_ctx=jugadores_locales_ctx,
            fichas_conocidas_ctx=fichas_conocidas_ctx,
            escalation_chain=escalation_chain,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )
        # DT-059/T3: auto-revisión sabor web (re-busca por faltantes + KB). Flag OFF = no-op.
        cap = review_web_cap(
            settings=s, llm=ctx.api_llm or ctx.llm,
            capitulo_nombre="Cap 2 — Análisis Competitivo",
            criterios=CRITERIOS_CAPITULO["Cap 2 — Análisis Competitivo"],
            cap_obj=cap, run_key=ctx.run_key, store=store, web=web,
            sector_gics=g, sector_gics_code=g_code, empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} competitors benchmarking {e}",
            kb_competidores=kb_competidores,
            # DT-064/T2: reinyecta los sujetos anclados (globales + locales) al rescatar el Cap 2.
            jugadores_locales_ctx=jugadores_locales_ctx,
        )
        # DT-064/T3: extrae y persiste los campos de ficha de los competidores anclados (reuso).
        _persistir_fichas_ancladas(cap, kb_competidores, kb_locales)
        return cap

    def _fn_mercado(store, web, _oal):
        if ctx.api_llm is None:
            return None
        return GenerateMercado(
            chain=build_chain_03b(ctx.api_llm), store=store, web_connector=web
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )

    def _fn_cap3(store, web, oal):
        if ctx.api_llm is None:
            return None
        cap = GenerateTendencias(
            chain=build_chain_04(ctx.api_llm), store=store,
            web_connector=web, openalex_connector=oal,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )
        return review_web_cap(
            settings=s, llm=ctx.api_llm,
            capitulo_nombre="Cap 3 — Análisis Sectorial Tendencial",
            criterios=CRITERIOS_CAPITULO["Cap 3 — Análisis Sectorial Tendencial"],
            cap_obj=cap, run_key=ctx.run_key, store=store, web=web,
            sector_gics=g, sector_gics_code=g_code, empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} tendencias sectoriales tecnológicas {e}",
        )

    def _fn_cap4(store, web, _oal):
        if ctx.api_llm is None:
            return None
        cap = GenerateEcosistema(
            chain=build_chain_05(ctx.api_llm), store=store, web_connector=web,
        ).execute(
            nombre_empresa=e, descripcion_empresa=ctx.empresa.texto, sector_gics=g,
            sector_gics_code=g_code, empresa_id=ctx.empresa_id,
        )
        return review_web_cap(
            settings=s, llm=ctx.api_llm,
            capitulo_nombre="Cap 4 — Panorama Ecosistema",
            criterios=CRITERIOS_CAPITULO["Cap 4 — Panorama Ecosistema"],
            cap_obj=cap, run_key=ctx.run_key, store=store, web=web,
            sector_gics=g, sector_gics_code=g_code, empresa_id=ctx.empresa_id,
            retrieval_query=f"{g} ecosistema inversiones fusiones adquisiciones alianzas {e}",
        )

    # T22.3 (DT-030): --resume salta los caps ya persistidos; solo se computan los faltantes.
    from ic.domain.use_cases import checkpoint_hooks

    _fns = {"cap2": _fn_cap2, "mercado": _fn_mercado, "cap3": _fn_cap3, "cap4": _fn_cap4}
    _restored = {name: checkpoint_hooks.restore(ctx, name) for name in _fns}
    _results: dict = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        _futures = {
            name: pool.submit(_store, fn)
            for name, fn in _fns.items()
            if _restored[name] is None
        }
    for name in _fns:
        _results[name] = (
            _restored[name] if _restored[name] is not None else _futures[name].result()
        )
    ctx.cap, ctx.cap_mercado = _results["cap2"], _results["mercado"]
    ctx.cap_tend, ctx.cap_eco = _results["cap3"], _results["cap4"]

    ctx.step_fn(4, "Párrafos introductorios N1")
    if ctx.intro_chain is not None:
        # El intro se aplica solo a caps recién computados; los restaurados ya lo incluyen.
        for cap_obj, titulo, name in [
            (ctx.cap, "Análisis Competitivo", "cap2"),
            (ctx.cap_tend, "Análisis Sectorial Tendencial", "cap3"),
            (ctx.cap_eco, "Ecosistema Empresarial", "cap4"),
        ]:
            if _restored[name] is None and cap_obj is not None and cap_obj.retrieval_suficiente:
                intro = ctx.intro_chain.invoke({
                    "titulo": titulo, "empresa": ctx.params.empresa,
                    "resumen_cap": cap_obj.texto[:500],
                })
                # DT-055: intro saneado puede quedar vacío → no anteponer líneas en blanco
                if intro:
                    cap_obj.texto = intro + "\n\n" + cap_obj.texto

    # Persistir los caps recién computados (con intro) con keep-best + fallback (Fase 1).
    _slots = {"cap2": "cap", "mercado": "cap_mercado", "cap3": "cap_tend", "cap4": "cap_eco"}
    for name, obj in [
        ("cap2", ctx.cap), ("mercado", ctx.cap_mercado),
        ("cap3", ctx.cap_tend), ("cap4", ctx.cap_eco),
    ]:
        if _restored[name] is None:
            setattr(ctx, _slots[name], checkpoint_hooks.commit_best(ctx, name, obj))
