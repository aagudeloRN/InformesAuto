from datetime import date

from ic.infrastructure.citation import apa_formatter
from ic.infrastructure.docx_builder import DocxBuilder
from ic.shared.types import InformePiloto


class PilotAssembler:
    def __init__(self, builder: DocxBuilder) -> None:
        self._builder = builder

    def assemble(self, informe: InformePiloto, output_path: str) -> str:
        b = self._builder
        empresa_nombre = informe.empresa.nombre_empresa
        fecha = date.today().strftime("%d de %B de %Y")

        b.add_heading(f"Informe de Inteligencia Competitiva — {empresa_nombre}", level=1)
        b.add_paragraph(f"Fecha de generación: {fecha}")
        b.add_paragraph("")

        b.add_heading("[Resumen ejecutivo — pendiente Fase 5]", level=2)
        b.add_paragraph("")

        b.add_heading("Capítulo 1. Descripción de la Empresa", level=2)
        b.add_markdown_section(informe.empresa.texto)
        b.add_paragraph("")

        b.add_heading("Clasificación GICS", level=3)
        b.add_paragraph(f"Grupo GICS: {informe.gics.grupo_gics}")
        b.add_markdown_section(informe.gics.justificacion)
        b.add_paragraph("")

        b.add_heading("Capítulo 2. Análisis Competitivo", level=2)
        b.add_markdown_section(informe.cap_benchmarking.texto)
        b.add_paragraph("")

        if informe.cap_tendencias is not None:
            b.add_heading("Capítulo 3. Análisis Sectorial Tendencial", level=2)
            b.add_markdown_section(informe.cap_tendencias.texto)
            b.add_paragraph("")

        if informe.cap_ecosistema is not None:
            b.add_heading("Capítulo 4. Ecosistema Empresarial", level=2)
            b.add_markdown_section(informe.cap_ecosistema.texto)
            b.add_paragraph("")

        b.add_heading("Referencias", level=2)
        for ref in informe.referencias:
            b.add_paragraph(ref.apa_string)

        b.add_paragraph("")
        b.add_paragraph(
            "Informe generado automáticamente — piloto NOEL. "
            "Los contenidos son generados por IA y deben ser verificados por un analista."
        )

        b.save(output_path)
        return output_path
