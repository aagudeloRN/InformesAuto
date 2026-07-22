"""Purga ÚNICA del backlog web histórico no usado (Fase 14, T14.5, DT-020).

Antes de Fase 14 los resultados web se persistían al buscar, acumulando miles de chunks sin
ciclo de vida que competían con el corpus sectorial. Desde Fase 14 solo persiste lo citado
(chunks promovidos). Este script borra el backlog "legacy": chunks web sin `session_id`
(no están en una corrida en curso) y sin `promoted` (nunca fueron citados). Se ejecuta UNA vez.

Uso:
    uv run python scripts/purge_web_backlog.py            # dry-run: solo muestra conteos
    uv run python scripts/purge_web_backlog.py --apply    # ejecuta el borrado
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

for _noisy in ("sqlalchemy.engine",):
    logging.getLogger(_noisy).disabled = True

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from ic.data.database import SessionLocal  # noqa: E402
from ic.data.repositories.embedding_repo import EmbeddingRepository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Purga única del backlog web no usado")
    parser.add_argument(
        "--apply", action="store_true", help="Ejecuta el borrado (por defecto: dry-run)"
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        repo = EmbeddingRepository(db)
        antes = repo.count_web()
        print("Conteo web ANTES:", antes)
        print(f"  Backlog legacy a purgar: {antes['legacy']} chunks")

        if not args.apply:
            print("\n[dry-run] No se borró nada. Re-ejecuta con --apply para purgar.")
            return 0

        n = repo.purge_unused_web_backlog()
        despues = repo.count_web()
        print(f"\nBorrados: {n} chunks legacy.")
        print("Conteo web DESPUÉS:", despues)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
