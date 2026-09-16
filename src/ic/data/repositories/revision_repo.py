"""Repositorio de trazabilidad de auto-revisión (DT-059/T4).

Persiste una `RevisionTrace` del loop como fila auditable. No conoce los tipos del loop
(SoC): recibe primitivos + la mejor `RubricScore` desagregada por el hook de dominio.
"""

from sqlalchemy.orm import Session

from ic.data.models.revision_capitulo import RevisionCapitulo


class RevisionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def save_revision(
        self,
        *,
        run_key: str,
        capitulo: str,
        sabor: str,
        n_iteraciones: int,
        iter_ganadora: int,
        score_inicial: int,
        score_final: int,
        motivo_parada: str,
        dimensiones: dict | None = None,
        faltantes: list | None = None,
    ) -> None:
        """Inserta una fila de trazabilidad (append-only: cada corrida deja su historial)."""
        self._db.add(
            RevisionCapitulo(
                run_key=run_key,
                capitulo=capitulo,
                sabor=sabor,
                n_iteraciones=n_iteraciones,
                iter_ganadora=iter_ganadora,
                score_inicial=score_inicial,
                score_final=score_final,
                motivo_parada=motivo_parada,
                dimensiones=dimensiones,
                faltantes=faltantes,
            )
        )
        self._db.commit()
