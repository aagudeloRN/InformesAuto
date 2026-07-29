"""T22.2 (DT-027): mide el hit-rate del radar de posicionamiento (Cap 2).

Ejercita SOLO el camino del radar (chain_03 → _extract_radar) N veces sobre el corpus
EMIS enriquecido, sin correr el pipeline completo (más rápido y reproducible que N
informes). Alterna dos sectores completos (3020 Alimentos, 2510 Automóviles). El radar
se considera "presente" si radar_data es no-nulo y tiene ≥1 competidor parseable.

Uso:
    uv run python scripts/measure_radar_hitrate.py            # N=5 (default)
    uv run python scripts/measure_radar_hitrate.py --n 5 --out docs/decisions/radar.json

Requiere Ollama/OpenRouter disponibles (usa el modelo API si hay clave; si no, el local).
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

# Descripción mínima por empresa (evita recomputar Cap 1: no afecta al radar, que se
# basa en el retrieval sectorial + análisis de competidores de la sección 2.1).
_CASOS = [
    {
        "empresa": "Alpina S.A.S.",
        "descripcion": (
            "Alpina S.A.S. es una empresa colombiana líder en producción de alimentos "
            "y bebidas lácteas: yogures, quesos, leches y postres."
        ),
        "gics_idx": 10,  # Grupo 11 — Alimentos, bebidas y tabaco (GICS 3020)
    },
    {
        "empresa": "Sofasa S.A.",
        "descripcion": (
            "Sofasa S.A. es una ensambladora automotriz colombiana que fabrica vehículos "
            "de las marcas Renault para el mercado nacional y de exportación."
        ),
        "gics_idx": 5,  # Grupo 6 — Automóviles y componentes (GICS 2510)
    },
]


def _run_once(caso: dict, settings, api_llm, llm, embedder, web) -> dict:
    from ic.data.database import SessionLocal
    from ic.data.repositories.embedding_repo import EmbeddingRepository
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
        cap = GenerateBenchmarking(
            chain=build_chain_03(api_llm or llm), store=store, web_connector=cached_web
        ).execute(
            nombre_empresa=caso["empresa"], descripcion_empresa=caso["descripcion"],
            sector_gics=grupo, sector_gics_code=g_code, empresa_id=None,
        )
    radar = cap.radar_data
    n_comp = len(radar.get("competidores", {})) if isinstance(radar, dict) else 0
    presente = bool(radar) and n_comp >= 1
    return {
        "empresa": caso["empresa"], "gics": g_code,
        "radar_presente": presente, "n_competidores": n_comp,
        "retrieval_suficiente": cap.retrieval_suficiente,
        "segundos": round(time.time() - t0, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Mide el hit-rate del radar (T22.2, DT-027)")
    parser.add_argument("--n", type=int, default=5, help="Número de corridas (default 5)")
    parser.add_argument(
        "--out", default="docs/decisions/fase22_radar_hitrate.json",
        help="Ruta del snapshot JSON de resultados",
    )
    args = parser.parse_args()

    from ic.infrastructure.llm.gateway import CostTracker, build_llm, build_resilient_api_llm
    from ic.infrastructure.retrieval.embedder import Embedder
    from ic.infrastructure.sources.web_connector import WebConnector
    from ic.shared.config import get_settings

    settings = get_settings()
    tracker = CostTracker(budget_limit=settings.llm_budget_limit_usd)
    api_llm = (
        build_resilient_api_llm(settings, cost_tracker=tracker)
        if settings.openrouter_api_key else None
    )
    llm = build_llm(settings, cost_tracker=tracker)
    embedder = Embedder(settings)
    web = WebConnector(settings)

    corridas = []
    for i in range(args.n):
        caso = _CASOS[i % len(_CASOS)]
        print(f"[{i + 1}/{args.n}] {caso['empresa']}...", flush=True)
        try:
            res = _run_once(caso, settings, api_llm, llm, embedder, web)
        except Exception as exc:  # noqa: BLE001
            res = {"empresa": caso["empresa"], "radar_presente": False, "error": repr(exc)}
        corridas.append(res)
        print(f"    → radar_presente={res.get('radar_presente')} "
              f"competidores={res.get('n_competidores', 0)} "
              f"({res.get('segundos', '?')}s)", flush=True)

    hits = sum(1 for c in corridas if c.get("radar_presente"))
    snapshot = {
        "tarea": "T22.2 (DT-027) hit-rate del radar tras endurecer prompt+extractor",
        "n": args.n,
        "hits": hits,
        "hit_rate": round(hits / args.n, 3) if args.n else 0.0,
        "corridas": corridas,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n=== HIT-RATE: {hits}/{args.n} ({snapshot['hit_rate'] * 100:.0f}%) ===")
    print(f"Snapshot: {out_path}")


if __name__ == "__main__":
    main()
