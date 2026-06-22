"""Script de ejecución única: crea el schema informes_ic y todas las tablas."""

import sys

from sqlalchemy import text

sys.path.insert(0, "src")

from ic.data.database import engine
from ic.data.models import Base
from ic.shared.config import get_settings

settings = get_settings()


def main() -> None:
    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.db_schema}"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        print(f"Schema '{settings.db_schema}' y extensión 'vector' listos.")

    Base.metadata.create_all(engine)

    tablas = list(Base.metadata.tables.keys())
    print(f"Tablas creadas ({len(tablas)}):")
    for t in sorted(tablas):
        print(f"  ✓ {t}")


if __name__ == "__main__":
    main()
