"""UC Cap 2.2 — División de Competidores (Grupos Estratégicos).

Clasifica exhaustivamente los competidores de Cap 2.1 en una matriz 2×2
(Masivo/Nicho × Tradicional/Innovador). Grounding estricto: lista cerrada de
empresas de 2.1; validador post-gen elimina cualquier nombre ajeno.

Errores de red/API se propagan al orquestador (FR-012); el retry x2 aplica
solo a JSON malformado.
"""

from __future__ import annotations

import json
import logging
import re

from ic.domain.kb.seccion22_assembler import (
    CoverageError,
    DuplicateError,
    absent_paragraph,
    assemble_seccion_22,
)
from ic.shared.types import (
    Cap21Jugadores,
    Cap22Division,
    ClasificacionCompetidor,
    CuadranteKey,
    DescripcionEmpresa,
)

logger = logging.getLogger(__name__)

_CAP_NOMBRE = "cap_2_2"
_MAX_RETRIES = 2

_CUADRANTE_KEYS = [k.value for k in CuadranteKey]


# ---------------------------------------------------------------------------
# Helpers puros
# ---------------------------------------------------------------------------


def _build_closed_list(cap21: Cap21Jugadores) -> list[str]:
    """Extrae nombres de empresa de Cap 2.1 en orden tier (global > regional > startup)."""
    names: list[str] = []
    if cap21.globales:
        names.extend(cap21.globales.candidatos)
    if cap21.regionales:
        names.extend(cap21.regionales.empresas_emis)
    if cap21.startups:
        names.extend(cap21.startups.locales)
        names.extend(cap21.startups.internacionales)
    # deduplicar preservando orden (puede haber solapamiento cross-tier residual)
    seen: set[str] = set()
    deduped: list[str] = []
    for n in names:
        if n not in seen:
            seen.add(n)
            deduped.append(n)
    return deduped


def _build_fichas_context(cap21: Cap21Jugadores) -> str:
    """Construye un resumen de texto de los atributos de ficha de Cap 2.1 para el prompt."""
    partes: list[str] = []
    if cap21.globales and cap21.globales.texto:
        partes.append(cap21.globales.texto)
    if cap21.regionales and cap21.regionales.texto:
        partes.append(cap21.regionales.texto)
    if cap21.startups and cap21.startups.texto:
        partes.append(cap21.startups.texto)
    return "\n\n".join(partes) if partes else "(Sin atributos de ficha disponibles)"


def _parse_llm_json(raw: str) -> dict | None:
    """Extrae y parsea el JSON del output del LLM. Maneja markdown fences."""
    if not raw or not raw.strip():
        return None
    # eliminar markdown fences (```json ... ``` o ``` ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            return None
        if "cuadrantes" not in parsed:
            return None
        return parsed
    except (json.JSONDecodeError, ValueError):
        return None


def _validate_closed_list(
    cuadrantes: dict[str, list[str]], closed_list: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    """Elimina nombres ajenos a closed_list; devuelve (cuadrantes_filtrados, warnings)."""
    closed_lower = {n.lower(): n for n in closed_list}
    warnings: list[str] = []
    filtered: dict[str, list[str]] = {}
    for clave in _CUADRANTE_KEYS:
        raw_names = cuadrantes.get(clave, [])
        kept: list[str] = []
        for nombre in raw_names:
            if nombre.lower() in closed_lower:
                kept.append(closed_lower[nombre.lower()])  # normalizar al nombre canónico
            else:
                warnings.append(nombre)
                logger.warning(
                    "Cap 2.2: nombre ajeno eliminado de cuadrante '%s': '%s'", clave, nombre
                )
        filtered[clave] = kept
    return filtered, warnings


_DATO_NO_DISPONIBLE_MARKER = "Dato no disponible en fuentes consultadas"


def _build_clasificaciones(
    cuadrantes: dict[str, list[str]],
    parsed_validated: dict | None = None,
) -> list[ClasificacionCompetidor]:
    """Construye la lista de clasificaciones; marca dato_no_disponible si el LLM lo indica."""
    sintesis_text = ""
    if parsed_validated:
        sintesis_text = " ".join(
            [
                parsed_validated.get("sintesis_incumbente", ""),
                parsed_validated.get("sintesis_entrante", ""),
            ]
        )

    clases: list[ClasificacionCompetidor] = []
    for clave in _CUADRANTE_KEYS:
        cuadrante_key = CuadranteKey(clave)
        for nombre in cuadrantes.get(clave, []):
            dato_nd = _DATO_NO_DISPONIBLE_MARKER in sintesis_text and nombre in sintesis_text
            clases.append(
                ClasificacionCompetidor(
                    nombre=nombre,
                    cuadrante=cuadrante_key,
                    dato_no_disponible=dato_nd,
                )
            )
    return clases


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------


class Generate22Division:
    """Orquestador de Cap 2.2: valida input → llama LLM → valida output → persiste."""

    def __init__(self, chain: object, checkpoint_repo: object) -> None:
        self._chain = chain
        self._checkpoint_repo = checkpoint_repo

    def __call__(
        self,
        run_key: str,
        cap21: Cap21Jugadores,
        empresa: DescripcionEmpresa,
        feedback: str | None = None,
    ) -> Cap22Division:
        """Genera el subcapítulo 2.2. Propaga excepciones de red/API al orquestador (FR-012)."""
        # --- Guard: Cap 2.1 vacío o retrieval insuficiente ---
        closed_list = _build_closed_list(cap21)
        if not cap21.retrieval_suficiente or not closed_list:
            logger.info("Cap 2.2: Cap 2.1 vacío o retrieval insuficiente — párrafo de ausencia")
            return Cap22Division(
                texto=absent_paragraph(),
                clasificaciones=[],
                n_empresas_procesadas=0,
                retrieval_suficiente=False,
            )

        # --- Construir inputs del prompt ---
        closed_list_str = "\n".join(f"- {n}" for n in closed_list)
        fichas_context = _build_fichas_context(cap21)
        empresa_sector = (
            f"{empresa.nombre_empresa} — {empresa.texto[:300]}"
            if empresa.texto
            else empresa.nombre_empresa
        )
        feedback_str = feedback.strip() if feedback else ""

        # --- Invocar LLM con retry en JSON malformado ---
        parsed: dict | None = None
        for attempt in range(_MAX_RETRIES):
            raw = self._chain.invoke(
                {
                    "closed_list_str": closed_list_str,
                    "fichas_context": fichas_context,
                    "empresa_sector": empresa_sector,
                    "feedback": feedback_str,
                }
            )
            parsed = _parse_llm_json(raw)
            if parsed is not None:
                break
            logger.warning("Cap 2.2: JSON malformado en intento %d/%d", attempt + 1, _MAX_RETRIES)

        if parsed is None:
            logger.error(
                "Cap 2.2: JSON malformado tras %d intentos — párrafo de ausencia", _MAX_RETRIES
            )
            return Cap22Division(
                texto=absent_paragraph(),
                clasificaciones=[],
                n_empresas_procesadas=len(closed_list),
                retrieval_suficiente=False,
            )

        # --- Validar lista cerrada ---
        cuadrantes_validados, warnings = _validate_closed_list(
            parsed.get("cuadrantes", {}), closed_list
        )
        parsed_validated = dict(parsed)
        parsed_validated["cuadrantes"] = cuadrantes_validados

        # --- Ensamblar markdown (con retry si falla cobertura) ---
        texto: str | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                texto = assemble_seccion_22(parsed_validated, closed_list)
                break
            except (CoverageError, DuplicateError) as exc:
                logger.warning(
                    "Cap 2.2: error de ensamblaje (intento %d/%d): %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    exc,
                )
                # en el segundo intento no hay más reintentos de LLM disponibles
                if attempt + 1 >= _MAX_RETRIES:
                    logger.error("Cap 2.2: ensamblaje fallido — párrafo de ausencia")
                    return Cap22Division(
                        texto=absent_paragraph(),
                        clasificaciones=[],
                        n_empresas_procesadas=len(closed_list),
                        retrieval_suficiente=False,
                        warnings_nombres_ajenos=warnings,
                    )

        # --- Construir resultado ---
        clasificaciones = _build_clasificaciones(cuadrantes_validados, parsed_validated)

        # T028: un solo competidor → warning de representatividad
        if len(closed_list) == 1:
            warnings.append(
                "Solo 1 competidor en Cap 2.1; la segmentación 2×2 puede no ser representativa"
            )

        cap22 = Cap22Division(
            texto=texto,
            clasificaciones=clasificaciones,
            n_empresas_procesadas=len(closed_list),
            retrieval_suficiente=True,
            warnings_nombres_ajenos=warnings,
        )

        # --- Persistir checkpoint ---
        try:
            from ic.domain.checkpoint_serde import serialize_cap

            payload = serialize_cap(cap22)
            self._checkpoint_repo.save_capitulo(run_key, _CAP_NOMBRE, payload)
        except Exception:  # noqa: BLE001 — la persistencia es best-effort
            logger.warning("Cap 2.2: no se pudo persistir el checkpoint", exc_info=True)

        return cap22
