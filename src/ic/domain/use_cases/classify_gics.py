import logging
import re

from langchain_core.runnables import Runnable

from ic.shared.constants.ciiu_gics import ciiu_to_gics_candidates
from ic.shared.constants.gics_groups import extract_gics_code, gics_options
from ic.shared.types import ClasificacionGICS

logger = logging.getLogger(__name__)

_EXPLICIT_CODE_RE = re.compile(r"\(GICS \d{4}\)")


class ClassifyGICS:
    def __init__(self, chain: Runnable) -> None:
        self._chain = chain
        self._nombre_por_codigo = dict(gics_options())

    def execute(
        self,
        nombre_empresa: str,
        descripcion_empresa: str,
        ciiu: str | None = None,
    ) -> ClasificacionGICS:
        """Clasifica la empresa en un grupo GICS.

        Si se conoce el CIIU (DT-023): (a) acota la elección del LLM inyectando los grupos
        candidatos del mapeo CIIU→GICS como pista, y (b) valida/corrige el código resuelto
        contra esos candidatos antes del filtro sectorial (ADR-012).
        """
        candidatos = ciiu_to_gics_candidates(ciiu) if ciiu else []
        pistas = self._build_pistas(candidatos)

        texto_raw = self._chain.invoke(
            {
                "nombre_empresa": nombre_empresa,
                "descripcion_empresa": descripcion_empresa,
                "pistas": pistas,
            }
        )

        grupo = self._extract_field(texto_raw, "Grupo Industrial")
        justificacion = self._extract_field(texto_raw, "Justificación")

        grupo = self._validate_and_correct(grupo, candidatos)

        return ClasificacionGICS(
            grupo_gics=grupo,
            justificacion=justificacion,
            texto_raw=texto_raw,
        )

    def _build_pistas(self, candidatos: list[str]) -> str:
        if not candidatos:
            return ""
        nombres = [f"{self._nombre_por_codigo.get(c, c)} (GICS {c})" for c in candidatos]
        return (
            "\nPISTA (por el CIIU de la empresa, el grupo suele estar entre estos candidatos; "
            "elige el más ajustado al core business, pero puedes apartarte si la descripción lo "
            "justifica):\n  - " + "\n  - ".join(nombres) + "\n"
        )

    def _validate_and_correct(self, grupo: str, candidatos: list[str]) -> str:
        """Valida el grupo contra los candidatos del CIIU.

        Política conservadora: si el LLM emitió un código explícito "(GICS XXXX)", se respeta
        aunque quede fuera de los candidatos (solo se registra). Si NO hay código explícito y
        el código resuelto por nombre cae fuera de los candidatos (o no resuelve), se corrige
        al primer candidato, más fiable que el fallback heurístico por nombre.
        """
        if not candidatos:
            return grupo

        code = extract_gics_code(grupo)
        if code in candidatos:
            return grupo

        tiene_codigo_explicito = bool(_EXPLICIT_CODE_RE.search(grupo or ""))
        if tiene_codigo_explicito:
            logger.warning(
                "Clasificación GICS %s fuera de los candidatos del CIIU %s; se respeta el "
                "código explícito del LLM.",
                code,
                candidatos,
            )
            return grupo

        corregido = candidatos[0]
        nombre = self._nombre_por_codigo.get(corregido, corregido)
        logger.warning(
            "Clasificación GICS sin código explícito y fuera de candidatos (resuelto=%s). "
            "Se corrige a %s (GICS %s) por el CIIU.",
            code,
            nombre,
            corregido,
        )
        return f"{nombre} (GICS {corregido})"

    @staticmethod
    def _extract_field(text: str, label: str) -> str:
        match = re.search(rf"{label}:\s*(.+?)(?:\n[A-ZÁÉÍÓÚÑ]|\Z)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
