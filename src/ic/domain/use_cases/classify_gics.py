import re

from langchain_core.runnables import Runnable

from ic.shared.types import ClasificacionGICS


class ClassifyGICS:
    def __init__(self, chain: Runnable) -> None:
        self._chain = chain

    def execute(self, nombre_empresa: str, descripcion_empresa: str) -> ClasificacionGICS:
        texto_raw = self._chain.invoke({
            "nombre_empresa": nombre_empresa,
            "descripcion_empresa": descripcion_empresa,
        })

        grupo = self._extract_field(texto_raw, "Grupo Industrial")
        justificacion = self._extract_field(texto_raw, "Justificación")

        return ClasificacionGICS(
            grupo_gics=grupo,
            justificacion=justificacion,
            texto_raw=texto_raw,
        )

    @staticmethod
    def _extract_field(text: str, label: str) -> str:
        match = re.search(rf"{label}:\s*(.+?)(?:\n[A-ZÁÉÍÓÚÑ]|\Z)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
