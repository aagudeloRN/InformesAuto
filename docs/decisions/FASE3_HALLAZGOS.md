# Hallazgos de Fase 3 — LLM Gateway + Cadenas LCEL + Use Cases

**Fecha:** 2026-06-25
**Fase:** 3 — Orquestación LLM (gateway + cadenas LCEL + use cases piloto)

Registro de decisiones operativas y hallazgos imprevistos durante la ejecución de
Fase 3 que afectan fases siguientes.

---

## 1. Import path de `BaseChatModel` en LangChain 0.3+

**Hallazgo:** En LangChain ≥0.3, `BaseChatModel` vive en `langchain_core`, no en
`langchain`. Los mensajes y resultados también vienen de `langchain_core`:

```python
# Correcto (LangChain 0.3+)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

# Incorrecto (API pre-0.3, genera DeprecationWarning o ImportError)
from langchain.chat_models.base import BaseChatModel
```

**Impacto en Fase 4+:** Todos los imports de LangChain en código nuevo deben usar
`langchain_core.*` para tipos, mensajes y modelos base. `langchain.*` solo para
componentes concretos que no existan en `langchain_core` (ej. `ChatPromptTemplate`,
que sí está en `langchain_core.prompts`).

---

## 2. `@retry` de tenacity: aplicar al closure HTTP, no al método `_generate`

**Hallazgo:** El circuit breaker con tenacity debe envolver el bloque HTTP directo
(el closure `_call()`), no el método `_generate()` completo.

```python
# Correcto: retry solo sobre el POST
def _generate(self, messages, ...):
    @retry(stop=stop_after_attempt(self.max_retries), ...)
    def _call() -> str:
        resp = httpx.post(...)
        return resp.json()["message"]["content"]
    content = _call()
    ...

# Incorrecto: retry sobre toda la generación (incluye conversión de mensajes, etc.)
@retry(...)
def _generate(self, messages, ...):
    ...
```

**Razón:** El retry debe cubrir solo el fallo de red/timeout de Ollama. Reintentar
`_generate()` completo reharía la conversión de mensajes y registros de callbacks
innecesariamente.

---

## 3. SYSTEM_PROMPT_02: interpolación en tiempo de importación, no de invocación

**Decisión:** El bloque GICS (25 grupos, ~2 KB) se interpola dentro del system prompt
**una sola vez, al importar el módulo**:

```python
SYSTEM_PROMPT_02 = _SYSTEM_PROMPT_02_TEMPLATE.format(gics_block=build_gics_prompt_block())
```

**Razón:** La lista de 25 grupos GICS es una constante del sistema. Interpolarla en
cada `chain.invoke()` sería un micro-costo innecesario y haría el sistema prompt
dinámico cuando no lo es.

**Consecuencia:** Si `build_gics_prompt_block()` fallara (ej. `gics_groups.py` tiene
un bug), el módulo fallaría al importarse — lo cual es deseable: falla rápido y en
carga, no al generar el primer informe.

---

## 4. Bug encontrado en implementación: `PGVectorStore.ingest()` recibe `list[str]`, no `list[WebResult]`

**Hallazgo:** `generate_benchmarking.py` llamaba `self._store.ingest(web_results, ...)` 
donde `web_results` es `list[WebResult]`. La firma real de `PGVectorStore.ingest()` es:

```python
def ingest(self, texts: list[str], fuente_tipo: str, urls: list[str | None], ...) -> int
```

**Fix aplicado en el mismo PR:**

```python
self._store.ingest(
    texts=[r.content for r in web_results],
    fuente_tipo="web",
    urls=[r.url for r in web_results],
)
```

**Lección:** El `PGVectorStore` no acepta DTOs de dominio (`WebResult`) — recibe
primitivos. La conversión es responsabilidad del use case. Si se quiere cambiar esto,
habría que añadir un método `ingest_from_web_results()` al store, pero por ahora la
conversión inline es más simple y no viola SoC.

---

## 5. Nombres de variables de template: seguir los nombres del doc de prompt

**Hallazgo:** El plan de Fase 3 usaba `{competidores_context}` como variable de
template en `chain_03`, pero el documento de prompts (`prompt-03-benchmarking.md`)
define `{retrieval_competidores}`.

**Decisión:** Usar siempre los nombres del documento de prompt como fuente de verdad.
El nombre `{retrieval_competidores}` es más descriptivo (indica que el contenido viene
del retrieval, no es una lista genérica de competidores).

**Impacto en Fase 4+:** Si se agregan nuevas cadenas (Prompt-04, Prompt-05…), las
variables de template deben coincidir exactamente con las definidas en
`docs/prompts/prompt-0N-*.md`. El documento de prompt es la especificación.

---

## 6. `ClassifyGICS._extract_field()`: regex con lookahead para campos multi-línea

**Contexto:** La salida del LLM para Prompt-02 tiene el formato:
```
Grupo Industrial: Alimentos, bebidas y tabaco
Justificación: La empresa produce alimentos envasados...
múltiples líneas posibles.
```

**Decisión:** El regex usa `re.DOTALL` con lookahead a mayúscula inicial o fin de
string para capturar el valor hasta que empiece el siguiente campo:

```python
re.search(rf"{label}:\s*(.+?)(?:\n[A-ZÁÉÍÓÚÑ]|\Z)", text, re.DOTALL)
```

**Consecuencia:** Si el LLM añade un campo extra después de "Justificación:" que
empiece con minúscula, el regex podría incluirlo en la captura. En la práctica el
system prompt es suficientemente restrictivo para que esto no ocurra. Si el parsing
falla, `grupo_gics` o `justificacion` quedan vacíos — lo cual es detectable y
permite reintentar sin abortar el informe.

---

## Métricas de Fase 3

| Métrica | Valor |
|---------|-------|
| Archivos creados | 9 |
| Archivos modificados | 1 (`shared/types.py`) |
| Líneas de código nuevas | ~310 |
| Tests nuevos | 6 |
| Tests totales pasando | 19/19 |
| Latencia Ollama (qwen2.5:7b, Prompt-02 NOEL) | ~35–50 s |
| Dependencias nuevas | ninguna (tenacity y langchain-core ya estaban en deps) |
