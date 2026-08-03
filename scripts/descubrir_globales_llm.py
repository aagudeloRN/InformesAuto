"""Siembra offline de competidores globales recomendados por LLM (DT-062).

Precalienta el KB por sector sin generar un informe: el LLM recomienda actores de clase mundial,
la búsqueda web dirigida los corrobora (RN-001/TIER 4) y solo los corroborados se siembran como
`verificado`/`alcance=global` con provenance `fuente=llm`. Reutiliza el mismo caso de uso que el
pipeline (`DiscoverGlobales`). Idempotente (upsert dedup por nombre+sector; no degrada estado).

Uso:
    uv run python scripts/descubrir_globales_llm.py --sector 3020 --sub 302020
    uv run python scripts/descubrir_globales_llm.py --sector 3020 --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.data.database import SessionLocal  # noqa: E402
from ic.data.models.entidad import (  # noqa: E402
    ALCANCE_GLOBAL,
    ESTADO_CANDIDATO,
    FUENTE_LLM,
    TIPO_COMPETIDOR,
    ensure_entidades_tables,
)
from ic.data.repositories.embedding_repo import EmbeddingRepository  # noqa: E402
from ic.data.repositories.entidad_repo import EntidadRepository, EntidadRow  # noqa: E402
from ic.domain.chains.chain_02c_pares_globales import build_chain_pares_globales  # noqa: E402
from ic.domain.use_cases.discover_globales import DiscoverGlobales  # noqa: E402
from ic.infrastructure.llm.gateway import (  # noqa: E402
    CostTracker,
    build_llm,
    build_resilient_api_llm,
)
from ic.infrastructure.ner.entity_recognizer import normalize_entity  # noqa: E402
from ic.infrastructure.retrieval.embedder import Embedder  # noqa: E402
from ic.infrastructure.retrieval.pgvector_store import PGVectorStore  # noqa: E402
from ic.infrastructure.sources.web_connector import WebConnector  # noqa: E402
from ic.shared.config import get_settings  # noqa: E402
from ic.shared.constants.gics_groups import GICS_GROUPS, extract_gics_code  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logger = logging.getLogger("descubrir_globales_llm")


def _nombre_sector(sector_code: str) -> str:
    """Nombre del grupo GICS para el prompt/consultas (fallback al código si no se encuentra)."""
    for grupo in GICS_GROUPS:
        if extract_gics_code(grupo) == sector_code:
            return grupo
    return sector_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Descubrimiento LLM de globales (DT-062)")
    parser.add_argument("--sector", nargs="+", required=True,
                        help="Uno o más códigos de grupo GICS (ej. --sector 3020 2020)")
    parser.add_argument("--sub", default=None, help="Sub-código GICS 6 díg (ej. 302020)")
    parser.add_argument("--ddg-only", action="store_true",
                        help="Forzar DuckDuckGo (no gasta Tavily) — pre-warm por lotes (DT-065)")
    parser.add_argument("--dry-run", action="store_true",
                        help="No siembra ni ingiere; solo reporta recomendados/corroborados")
    args = parser.parse_args()

    settings = get_settings()
    tracker = CostTracker(budget_limit=settings.llm_budget_limit_usd)
    api_llm = (
        build_resilient_api_llm(settings, cost_tracker=tracker)
        if settings.openrouter_api_key else None
    )
    llm = build_llm(settings, cost_tracker=tracker)
    embedder = Embedder(settings)
    web = WebConnector(settings)
    chain = build_chain_pares_globales(api_llm or llm)

    with SessionLocal() as db:
        ensure_entidades_tables(db.get_bind())
        repo = EntidadRepository(db)
        store = PGVectorStore(embedder, EmbeddingRepository(db), settings)
        # En dry-run no queremos ingerir evidencia web: un store no-op evita escribir vectores.
        store_efectivo = store if not args.dry_run else _NoopStore()

        for sector_code in args.sector:
            sector_nombre = _nombre_sector(sector_code)

            def _seed(nombre: str, corroborado: bool, hits: int, _sector=sector_code) -> None:
                # DT-065: LLM/web = SIEMPRE candidato (verificado se reserva a informes humanos).
                # La corroboración (≥min_corrob) gatea alcance=global (para 2.1.1) + ingesta.
                marca = "✓ candidato/global" if corroborado else "· candidato/llm"
                logger.info("  %-22s hits=%d → %s", nombre, hits, marca)
                if args.dry_run:
                    return
                eid = repo.upsert_entidad(EntidadRow(
                    nombre=nombre, nombre_normalizado=normalize_entity(nombre),
                    tipo=TIPO_COMPETIDOR, sector_gics=_sector, sub_gics=args.sub,
                    alcance=ALCANCE_GLOBAL if corroborado else None,
                    estado=ESTADO_CANDIDATO,
                ))
                repo.add_atributo(
                    eid, "origen", "llm-corroborado" if corroborado else "llm",
                    FUENTE_LLM, estado=ESTADO_CANDIDATO,
                )

            conteos = DiscoverGlobales(
                chain=chain, web_connector=web, store=store_efectivo,
                min_corrob=settings.discover_globales_min_corrob,
                force_ddg=args.ddg_only,
            ).discover(sector_gics=sector_nombre, productos="", seed_repo_fn=_seed)

            logger.info(
                "Sector %s (%s)%s%s: recomendados=%d corroborados=%d no_corroborados=%d",
                sector_code, sector_nombre, " [DRY-RUN]" if args.dry_run else "",
                " [DDG]" if args.ddg_only else "",
                conteos["recomendados"], conteos["corroborados"], conteos["no_corroborados"],
            )
    return 0


class _NoopStore:
    """Store inerte para --dry-run: la corroboración se mide igual, pero no se ingiere evidencia."""

    def ingest(self, *_, **__) -> int:  # noqa: D401 — firma mínima usada por DiscoverGlobales.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
