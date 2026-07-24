from datetime import date

from ic.domain.markdown_parser import parse_markdown, renumber_subheadings
from ic.domain.report_model import (
    Callout,
    CitationBlock,
    FigureBlock,
    Heading,
    PageBreak,
    Paragraph,
    ReportDocument,
    Toc,
)
from ic.shared.types import InformePiloto

_DEFAULT_DISCLAIMER = (
    "Informe generado automáticamente por IA. "
    "Los contenidos deben ser verificados por un analista antes de su uso."
)

_ABSENT_MSG = (
    "Información no disponible: el sistema no recuperó fuentes suficientes para este capítulo. "
    "Se recomienda ingresar documentos adicionales o ampliar la consulta web."
)

# Secciones formales del patrón Noel (T21.7, DT-045). El estilo fino se pule en F26.
_METODOLOGIA_PARRAFOS = (
    "Este informe se elabora mediante un sistema de inteligencia competitiva asistido por "
    "modelos de lenguaje bajo una estrategia de recuperación aumentada (RAG). El proceso "
    "prioriza modelos locales y escala a modelos por API solo cuando la calidad lo exige. "
    "Cada capítulo se genera a partir de fragmentos recuperados de un índice vectorial que "
    "combina documentos sectoriales, fuentes académicas (OpenAlex) y búsqueda web.",
    "Alcance y trazabilidad: toda afirmación proveniente de fuentes se cita en formato APA y "
    "es trazable hasta el fragmento que la sustenta. Cuando la recuperación no supera el umbral "
    "de relevancia, el sistema no genera contenido: reporta \"Dato no disponible en fuentes "
    "consultadas\" e invita a incorporar documentos adicionales. Ninguna afirmación se apoya en "
    "el conocimiento paramétrico del modelo.",
    "Limitaciones: la profundidad de cada capítulo depende de la cobertura de fuentes para el "
    "sector analizado. Los resultados deben ser verificados por un analista antes de su uso en "
    "decisiones estratégicas.",
)

_AVISO_IA_PARRAFOS = (
    "Este documento fue generado de forma automática con apoyo de modelos de inteligencia "
    "artificial. La inteligencia artificial se empleó como herramienta de recuperación, síntesis "
    "y redacción a partir de fuentes verificables, no como fuente autónoma de información.",
    "Los contenidos pueden incluir imprecisiones y deben ser revisados y validados por un "
    "analista humano antes de su publicación o uso en la toma de decisiones. La responsabilidad "
    "sobre las decisiones derivadas de este informe recae en el equipo que lo utiliza.",
)


def _insert_before_subheading(blocks: list, insert: list, prefix: str) -> list:
    """Inserta `insert` justo antes del primer Heading cuyo texto empiece por `prefix`.

    Si no se encuentra el ancla, `insert` se añade al final. Usado para intercalar la
    sección 2.3 Mercado entre 2.2 y 2.4 dentro del Capítulo 2 (T21.6, DT-044).
    """
    for i, blk in enumerate(blocks):
        if isinstance(blk, Heading) and blk.text.lstrip().startswith(prefix):
            return blocks[:i] + insert + blocks[i:]
    return blocks + insert


class PilotAssembler:
    def __init__(self, disclaimer: str = _DEFAULT_DISCLAIMER) -> None:
        self._disclaimer = disclaimer

    def build(
        self,
        informe: InformePiloto,
        figura_benchmarking: str | None = None,
    ) -> ReportDocument:
        blocks = [Toc()]

        if informe.resumen_ejecutivo is not None:
            blocks.append(Heading("Resumen Ejecutivo", level=2))
            blocks.extend(parse_markdown(informe.resumen_ejecutivo.texto))
            blocks.append(PageBreak())

        blocks.append(Heading("Capítulo 1. Descripción de la Empresa", level=2))
        blocks.extend(parse_markdown(informe.empresa.texto))
        blocks.append(Paragraph(""))

        blocks.append(Heading("Clasificación GICS", level=3))
        blocks.append(Paragraph(f"Grupo GICS: {informe.gics.grupo_gics}"))
        blocks.extend(parse_markdown(informe.gics.justificacion))
        blocks.append(Paragraph(""))

        blocks.append(Heading("Capítulo 2. Análisis Competitivo", level=2))
        if informe.cap_benchmarking.retrieval_suficiente:
            bench_blocks = parse_markdown(informe.cap_benchmarking.texto)
            # 2.3 Mercado (T21.6, DT-044): se intercala entre 2.2 y 2.4 dentro del Cap 2.
            cap_mercado = getattr(informe, "cap_mercado", None)
            if cap_mercado is not None and cap_mercado.retrieval_suficiente:
                bench_blocks = _insert_before_subheading(
                    bench_blocks, parse_markdown(cap_mercado.texto), prefix="2.4"
                )
            blocks.extend(bench_blocks)
        else:
            blocks.append(Callout(_ABSENT_MSG, kind="absent_data"))
        if figura_benchmarking:
            blocks.append(FigureBlock(
                image_path=figura_benchmarking,
                alt="Radar de benchmarking competidores Cap 2",
                caption="Figura 1. Posicionamiento relativo de competidores clave",
            ))
        blocks.append(Paragraph(""))

        # Número de capítulo canónico para renumerar subcapítulos que el LLM numeró mal (DT-032).
        _OPTIONAL_CAPS = [
            ("Capítulo 3. Análisis Sectorial Tendencial", informe.cap_tendencias, 3),
            ("Capítulo 4. Ecosistema Empresarial", informe.cap_ecosistema, 4),
            ("Capítulo 5. Convergencia Empresarial", informe.cap_convergencia, 5),
        ]
        for titulo, cap, cap_num in _OPTIONAL_CAPS:
            if cap is not None:
                blocks.append(Heading(titulo, level=2))
                if cap.retrieval_suficiente:
                    cap_blocks = parse_markdown(cap.texto)
                    blocks.extend(renumber_subheadings(cap_blocks, cap_num))
                else:
                    blocks.append(Callout(_ABSENT_MSG, kind="absent_data"))
                blocks.append(Paragraph(""))

        if informe.cap_accionables is not None:
            blocks.append(Heading("Capítulo 6. Accionables Estratégicos", level=2))
            blocks.append(Callout(
                "Los accionables siguientes requieren validación del equipo directivo "
                "antes de implementación.",
                kind="actionable",
            ))
            if informe.cap_accionables.retrieval_suficiente:
                blocks.extend(parse_markdown(informe.cap_accionables.texto))
            else:
                blocks.append(Callout(_ABSENT_MSG, kind="absent_data"))
            blocks.append(Paragraph(""))

        # Metodología (patrón Noel): sección formal antes de Referencias (T21.7, DT-045).
        blocks.append(PageBreak())
        blocks.append(Heading("Metodología", level=2))
        blocks.append(Paragraph(
            f"Fuentes consultadas y citadas en este informe: {len(informe.referencias)}."
        ))
        for parrafo in _METODOLOGIA_PARRAFOS:
            blocks.append(Paragraph(parrafo))
        blocks.append(Paragraph(""))

        blocks.append(Heading("Referencias", level=2))
        for ref in informe.referencias:
            blocks.append(CitationBlock(ref.apa_string))

        # Aviso sobre el uso de IA: sección formal (antes era un disclaimer de una línea).
        blocks.append(Paragraph(""))
        blocks.append(Heading("Aviso sobre el uso de inteligencia artificial", level=2))
        for parrafo in _AVISO_IA_PARRAFOS:
            blocks.append(Paragraph(parrafo))

        empresa_nombre = informe.empresa.nombre_empresa
        return ReportDocument(
            title=f"Informe de Inteligencia Competitiva — {empresa_nombre}",
            company=empresa_nombre,
            date=date.today().strftime("%d de %B de %Y"),
            blocks=blocks,
            disclaimer=self._disclaimer,
        )
