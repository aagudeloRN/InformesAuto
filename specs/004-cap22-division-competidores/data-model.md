# Data Model: Cap 2.2 — División de Competidores

**Phase 1 output** | **Date**: 2026-08-20 | **Feature**: [spec.md](spec.md)

## Entidades de dominio nuevas

### `CuadranteKey` (enum)

```python
# src/ic/shared/types.py — nuevo enum
class CuadranteKey(str, Enum):
    MASIVO_TRADICIONAL = "masivo_tradicional"
    MASIVO_INNOVADOR   = "masivo_innovador"
    NICHO_TRADICIONAL  = "nicho_tradicional"
    NICHO_INNOVADOR    = "nicho_innovador"
```

**Regla**: los cuatro valores son exhaustivos y excluyentes. Toda empresa de Cap 2.1 se asigna a exactamente uno.

---

### `ClasificacionCompetidor` (dataclass)

```python
# src/ic/shared/types.py — nuevo dataclass
@dataclass
class ClasificacionCompetidor:
    nombre: str                   # Nombre exacto tal como aparece en Cap 2.1
    cuadrante: CuadranteKey       # Cuadrante asignado por el LLM
    dato_no_disponible: bool = False  # True si la clasificación fue ambigua por falta de atributos
```

**Validaciones**:
- `nombre` debe existir en la lista cerrada derivada de `Cap21Jugadores`.
- `cuadrante` es uno de los cuatro valores del enum (no nullable).
- `dato_no_disponible = True` NO impide la clasificación; solo la marca para revisión.

---

### `Cap22Division` (dataclass)

```python
# src/ic/shared/types.py — nuevo dataclass
@dataclass
class Cap22Division:
    texto: str                                 # Markdown completo de la sección 2.2
    clasificaciones: list[ClasificacionCompetidor]  # Una por cada empresa de 2.1
    n_empresas_procesadas: int                 # Total de empresas en el input de 2.1
    retrieval_suficiente: bool                 # False si Cap 2.1 estaba vacío
    warnings_nombres_ajenos: list[str] = field(default_factory=list)  # Nombres eliminados por lista cerrada
```

**Invariante**: `len(clasificaciones) == n_empresas_procesadas` cuando `retrieval_suficiente = True`.

---

### `Cap22LlmOutput` (dataclass interno — no expuesto fuera del use_case)

Representa el JSON que devuelve el LLM antes de la validación:

```python
@dataclass
class Cap22LlmOutput:
    cuadrantes: dict[str, list[str]]  # CuadranteKey → lista de nombres (raw, sin validar)
    intro: str
    sintesis_incumbente: str
    sintesis_entrante: str
```

Este tipo vive dentro del módulo `generate_22_division.py` y no se exporta a `shared/types.py`.

---

## Entidades existentes modificadas

### `InformePiloto` (modificación)

```python
# src/ic/shared/types.py — campo nuevo
@dataclass
class InformePiloto:
    # ... campos existentes ...
    cap_22_division: "Cap22Division | None" = None  # NUEVO
```

**Posición**: añadir después de `cap_benchmarking` (que contiene Cap 2.1) y antes de `cap_mercado`.

---

## Estructura de persistencia

### Checkpoint en BD

Clave canónica: `cap_nombre = "cap_2_2"`.

Payload serializado (JSON en columna `payload` de la tabla `informes_ic.capitulos_checkpoint`):
```json
{
  "texto": "## 2.2. División de Competidores\n\n...",
  "clasificaciones": [
    {"nombre": "EmpresaA", "cuadrante": "masivo_tradicional", "dato_no_disponible": false},
    {"nombre": "EmpresaB", "cuadrante": "nicho_innovador",   "dato_no_disponible": true}
  ],
  "n_empresas_procesadas": 12,
  "retrieval_suficiente": true,
  "warnings_nombres_ajenos": []
}
```

**Serialización / deserialización**: `Cap22Division` → `dict` usando `dataclasses.asdict()`. Reconstrucción: `Cap22Division(**payload)` con conversión de `CuadranteKey` desde string.

---

## Contratos de entrada/salida del use_case

### Entrada (`Generate22Division.__call__`)

```python
def __call__(
    self,
    run_key: str,
    cap21: Cap21Jugadores,          # Resultado de Cap 2.1 (ya generado)
    empresa: DescripcionEmpresa,    # Contexto de Cap 1
    feedback: str | None = None,    # Retroalimentación para regeneración (opcional)
) -> Cap22Division:
```

### Salida

`Cap22Division` con `texto` en formato markdown estandarizado (ver contrato en `contracts/`).

### Precondiciones

- `cap21` puede tener `retrieval_suficiente = False` → use_case devuelve párrafo de ausencia sin invocar LLM.
- `feedback` puede ser `None` (primera generación) o un string no vacío (regeneración).
- `empresa` puede estar incompleta (sin `sector_gics`) → la síntesis de presión competitiva omite la conexión sectorial y lo indica.

---

## Relaciones entre entidades

```
DescripcionEmpresa (Cap 1)  ──┐
                               ├──→ Generate22Division ──→ Cap22Division ──→ InformePiloto
Cap21Jugadores (Cap 2.1)    ──┘
                                         │
                                         ↓
                               ClasificacionCompetidor × N
                                         │
                                         ↓
                               CuadranteKey (enum, 4 valores)
```

---

## Archivos a crear/modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `src/ic/shared/types.py` | Modificar | Añadir `CuadranteKey`, `ClasificacionCompetidor`, `Cap22Division`; modificar `InformePiloto` |
| `src/ic/domain/chains/chain_cap2_22_division.py` | Crear | Cadena LLM para clasificación en cuadrantes + síntesis |
| `src/ic/domain/use_cases/generate_22_division.py` | Crear | Orchestrator: valida input, llama chain, valida output (lista cerrada), persiste checkpoint |
| `src/ic/domain/kb/seccion22_assembler.py` | Crear | Assembler determinista: convierte `Cap22LlmOutput` validado a markdown final |
| `src/ic/domain/use_cases/generate_n1.py` | Modificar | Añadir `Generate22Division` al ThreadPoolExecutor de N1 |
| `docs/prompts/prompt-02b-division-competidores.md` | Crear | Documentación del prompt de Cap 2.2 |
| `tests/test_generate_22_division.py` | Crear | Tests unitarios (≥6 escenarios, ≥80% cobertura del use_case) |
