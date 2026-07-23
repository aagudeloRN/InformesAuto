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
            blocks.extend(parse_markdown(informe.cap_benchmarking.texto))
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

        blocks.append(PageBreak())
        blocks.append(Heading("Referencias", level=2))
        for ref in informe.referencias:
            blocks.append(CitationBlock(ref.apa_string))

        if self._disclaimer:
            blocks.append(Paragraph(""))
            blocks.append(Paragraph(self._disclaimer, style="Caption"))

        empresa_nombre = informe.empresa.nombre_empresa
        return ReportDocument(
            title=f"Informe de Inteligencia Competitiva — {empresa_nombre}",
            company=empresa_nombre,
            date=date.today().strftime("%d de %B de %Y"),
            blocks=blocks,
            disclaimer=self._disclaimer,
        )
