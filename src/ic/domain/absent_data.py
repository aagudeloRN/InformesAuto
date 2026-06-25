"""Política de datos ausentes (ADR-002): si el retrieval no supera el umbral, no se llama al LLM."""

from ic.shared.types import ChunkResult


def check_retrieval_sufficient(chunks: list[ChunkResult], min_chunks: int = 3) -> bool:
    return len(chunks) >= min_chunks


def build_absent_paragraph(
    section: str,
    reason: str = "No se encontraron fuentes suficientes",
) -> str:
    return (
        f"**{section}**\n\n"
        f"Dato no disponible en fuentes consultadas. {reason}. "
        "Se recomienda al usuario incorporar documentos adicionales (informes sectoriales, "
        "bases de datos EMIS, reportes de la empresa) y regenerar este capítulo."
    )
