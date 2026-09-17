"""T1 (DT-054, T22.4): mide la evidencia de competidores del Cap 2 antes/después.

Ejercita SOLO el camino del Cap 2 (identificación de entidades → búsqueda dirigida → chain_03)
N veces sobre el corpus EMIS, sin correr el pipeline completo (patrón measure_radar_hitrate).
Alterna dos sectores (3020 Alimentos, 2510 Automóviles). Métricas por corrida:

  - n_fichas               : tablas markdown de competidor en 2.1 ("| Campo | Valor |").
  - n_competidores_radar   : competidores en radar_data.
  - n_refs_emis_individual : chunks_usados de EMIS individual (pdf, con sector_gics, no compilado).
  - n_docs_distintos       : documentos/fuentes distintos en chunks_usados.

Uso:
    uv run python scripts/measure_competitor_evidence.py            # DESPUÉS (con entidades)
    uv run python scripts/measure_competitor_evidence.py --before   # ANTES (sin entidades_chain)
    uv run python scripts/measure_competitor_evidence.py --n 2 --out docs/decisions/x.json

Requiere Ollama/OpenRouter disponibles y el corpus EMIS indexado. Correr AISLADO (no editar
módulos del pipeline mientras corre — lección B1).
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logging.getLogger("ic").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

_CASOS = [
    {
        "empresa": "Alpina S.A.S.",
        "descripcion": (
            "Alpina S.A.S. es una empresa colombiana líder en producción de alimentos "
            "y bebidas lácteas: yogures, quesos, leches y postres."
        ),
        "gics_idx": 10,
    },
    {
        "empresa": "Sofasa S.A.",
        "descripcion": (
            "Sofasa S.A. es una ensambladora automotriz colombiana que fabrica vehículos "
            "de las marcas Renault para el mercado nacional y de exportación."
        ),
        "gics_idx": 5,
    },
]


def _es_emis_individual(meta: dict | None) -> bool:
    """EMIS individual: chunk de PDF con sector_gics seteado y tipo_fuente != informe_compilado."""
    if not meta:
        return False
    return meta.get("sector_gics") is not None and meta.get("tipo_fuente") != "informe_compilado"


def _metricas(cap) -> dict:
    texto = cap.texto or ""
    n_fichas = texto.count("| Campo | Valor |")
    radar = cap.radar_data
    n_comp = len(radar.get("competidores", {})) if isinstance(radar, dict) else 0
    chunks = cap.chunks_usados or []
    n_emis = sum(1 for c in chunks if _es_emis_individual(getattr(c, "metadatos", None)))
    docs = {getattr(c, "fuente_url", None) or getattr(c, "chunk_id", None) for c in chunks}
    return {
        "n_fichas": n_fichas,
        "n_competidores_radar": n_comp,
        "n_refs_emis_individual": n_emis,
        "n_docs_distintos": len(docs),
        "n_chunks_usados": len(chunks),
        "retrieval_suficiente": cap.retrieval_suficiente,
    }


def _run_once(caso: dict, settings, api_llm, llm, embedder, web, con_entidades: bool) -> dict:
    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository
    from ic.domain.chains.chain_02b_entidades import build_chain_entidades
    from ic.domain.chains.chain_03_benchmarking import build_chain_03
    from ic.domain.use_cases.generate_benchmarking import GenerateBenchmarking
    from ic.infrastructure.retrieval.pgvector_store import PGVectorStore
    from ic.infrastructure.sources.cached_connector import CachedWebConnector
    from ic.shared.constants.gics_groups import GICS_GROUPS, extract_gics_code

    grupo = GICS_GROUPS[caso["gics_idx"]]
    g_code = extract_gics_code(grupo)
    t0 = time.time()
    with SessionLocal() as db:
        store = PGVectorStore(embedder, EmbeddingRepository(db), settings)
        cached_web = CachedWebConnector(web, db, settings)
        entidades_chain = build_chain_entidades(api_llm or llm) if con_entidades else None
        cap = GenerateBenchmarking(
            chain=build_chain_03(api_llm or llm),
            store=store,
            web_connector=cached_web,
            entidades_chain=entidades_chain,
        ).execute(
            nombre_empresa=caso["empresa"],
            descripcion_empresa=caso["descripcion"],
            sector_gics=grupo,
            sector_gics_code=g_code,
            empresa_id=None,
        )
    res = {"empresa": caso["empresa"], "gics": g_code, "segundos": round(time.time() - t0, 1)}
    res.update(_metricas(cap))
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description="Mide evidencia de competidores (DT-054, T22.4)")
    parser.add_argument("--n", type=int, default=2, help="Número de corridas (default 2)")
    parser.add_argument(
        "--before",
        action="store_true",
        help="Baseline sin entidades_chain (búsqueda solo por sector)",
    )
    parser.add_argument("--out", default=None, help="Ruta del snapshot JSON")
    args = parser.parse_args()

    con_entidades = not args.before
    fase = "despues" if con_entidades else "antes"
    out_path = Path(args.out or f"docs/decisions/fase22_competitor_evidence_{fase}.json")

    from ic.infrastructure.llm.gateway import CostTracker, build_llm, build_resilient_api_llm
    from ic.infrastructure.retrieval.embedder import Embedder
    from ic.infrastructure.sources.web_connector import WebConnector
    from ic.shared.config import get_settings

    settings = get_settings()
    tracker = CostTracker(budget_limit=settings.llm_budget_limit_usd)
    api_llm = (
        build_resilient_api_llm(settings, cost_tracker=tracker)
        if settings.openrouter_api_key
        else None
    )
    llm = build_llm(settings, cost_tracker=tracker)
    embedder = Embedder(settings)
    web = WebConnector(settings)

    corridas = []
    for i in range(args.n):
        caso = _CASOS[i % len(_CASOS)]
        print(f"[{i + 1}/{args.n}] {caso['empresa']} ({fase})...", flush=True)
        try:
            res = _run_once(caso, settings, api_llm, llm, embedder, web, con_entidades)
        except Exception as exc:  # noqa: BLE001
            res = {"empresa": caso["empresa"], "error": repr(exc)}
        corridas.append(res)
        print(
            f"    → fichas={res.get('n_fichas')} radar={res.get('n_competidores_radar')} "
            f"emis_indiv={res.get('n_refs_emis_individual')} "
            f"docs={res.get('n_docs_distintos')} ({res.get('segundos', '?')}s)",
            flush=True,
        )

    def _avg(key):
        vals = [c[key] for c in corridas if key in c]
        return round(sum(vals) / len(vals), 2) if vals else None

    snapshot = {
        "tarea": "DT-054 + T22.4 — evidencia de competidores del Cap 2",
        "modo": fase,
        "con_entidades_chain": con_entidades,
        "n": args.n,
        "promedios": {
            "n_fichas": _avg("n_fichas"),
            "n_competidores_radar": _avg("n_competidores_radar"),
            "n_refs_emis_individual": _avg("n_refs_emis_individual"),
            "n_docs_distintos": _avg("n_docs_distintos"),
        },
        "corridas": corridas,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== {fase.upper()}: {snapshot['promedios']} ===")
    print(f"Snapshot: {out_path}")


if __name__ == "__main__":
    main()
