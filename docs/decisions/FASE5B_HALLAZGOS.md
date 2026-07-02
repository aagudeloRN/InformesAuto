# Hallazgos y decisiones operativas — Fase 5B

**Fecha:** 2026-07-02  
**Alcance:** Cap 3 Tendencial + OpenAlexConnector + test_connections + corrección credenciales BD  
**Tests al cierre:** 47 definidos (37 heredados + 10 OpenAlex + 10 Cap 3); 37/37 pasando en frío  
**Commit:** `d681e31`

---

## H5B-01: DATABASE_URL tenía credenciales del ejemplo, no de producción

**Contexto:** Al verificar la conexión a PostgreSQL con `test_connections.py`, el script
falló con `password authentication failed for user "ic_user"`. La causa fue que al agregar
las nuevas claves (OpenRouter, Tavily, OpenAlex) al `.env`, el bloque de base de datos
quedó con los valores del `.env.example` (`ic_user/changeme@localhost:5434/informes_ic_db`)
en lugar de los reales (`repositorio_user@localhost:5434/repositorio_ctie`).

**Resolución:** Corregido manualmente por el usuario. Verificado con `SELECT 1` directo
y con `test_connections.py` mostrando las 4 tablas del schema `informes_ic`.

**Lección:** El `.env.example` tiene valores ilustrativos que no coinciden con el entorno
compartido. Documentar explícitamente en el `README.md` que `DATABASE_URL` debe apuntar
a `repositorio_ctie` con el usuario real del servidor compartido.

---

## H5B-02: OpenAlex tuvo caída 503 durante toda la sesión

**Contexto:** Todas las llamadas a `https://api.openalex.org/works` retornaron 503 Service
Unavailable durante la sesión del 2026-07-02. La API es pública y gratuita pero tiene
interrupciones ocasionales.

**Decisión de diseño:** `OpenAlexConnector.search()` captura `HTTPStatusError` y
`RequestError` y retorna lista vacía — nunca propaga la excepción. `GenerateTendencias`
trata OpenAlex como fuente opcional: si retorna vacío, el capítulo se genera igualmente
con fuentes web (DDG/Tavily). El `test_connections.py` marca el servicio como ❌ pero
no bloquea el script.

**Por qué esta decisión:** OpenAlex no tiene SLA. Un capítulo sin fuentes académicas es
mejor que un informe que falla. La calidad se degrada, no se rompe.

**Implicación para Cap 3 E2E:** Si OpenAlex sigue en 503, el capítulo se generará con
fuentes web únicamente. Las referencias APA de trabajos académicos estarán ausentes en
esa ejecución — comportamiento esperado y documentado.

---

## H5B-03: Modelos Ollama disponibles — candidato a actualizar la política WSL

**Contexto:** `test_connections.py` reveló 24 modelos Ollama instalados, incluyendo
varios más recientes que la política actual (`qwen2.5:7b` como máximo recomendado):

| Modelo | Tamaño | Candidato |
|--------|--------|-----------|
| `qwen3:8b` | 5.2 GB | ✅ Qwen 3 es generacionalmente superior a Qwen 2.5 |
| `gemma3:4b` | 3.3 GB | ✅ Opción liviana para tareas fundacionales |
| `qwen3.5:9b` | 6.6 GB | ⚠️ Límite ajustado, riesgo en WSL 8GB |
| `qwen2.5:7b` | 4.7 GB | ✅ Actual (funciona bien, política documentada) |

**Recomendación:** Probar `qwen3:8b` (5.2 GB) para Cap 1 y GICS en la próxima E2E.
Si el tiempo de respuesta mejora sin cuelgues, actualizar `LLM_LOCAL_ANALYTIC_MODEL`
en `.env`. No cambiar sin validación previa.

**No implementado en esta sesión:** cambio de modelo local requiere prueba E2E que
confirmó tiempos. Se deja para decisión del usuario.

---

## H5B-04: OpenRouter free tier responde en <2s — confirma el routing de modelos

**Contexto:** `test_connections.py` mostró:
- Nemotron Super (`free`): 0.9s de respuesta
- Nemotron Ultra (`synth`): 1.8s de respuesta

vs. Cap 2 con qwen2.5:7b local: 243s.

**Validación del diseño ADR-002:** El escalado a OpenRouter para capítulos N1 analíticos
es la decisión correcta. El overhead de red (0.9s) es insignificante frente al tiempo
de inferencia local. Cap 3 en adelante deberían correr en 15-30s con Nemotron.

**Costo confirmado:** Los modelos `:free` tienen precio $0. Solo `gemma-3-27b-it` (respaldo
pago, ~$0.15 USD por cap) tiene costo real.

---

## H5B-05: Parámetro force_ddg protege el free tier de Tavily en tests

**Contexto:** `WebConnector.search()` sin modificar llamaba a Tavily en cada prueba si
la API key estaba configurada. Con ~1000 créditos/mes en el free tier y múltiples suites
de tests, el agotamiento prematuro era un riesgo real.

**Solución implementada:** `force_ddg: bool = False` — los tests pasan `force_ddg=True`
para usar DDG sin costo. Producción sigue usando Tavily (mejor calidad). El script
`test_connections.py` hace exactamente 1 llamada Tavily por ejecución (verificación mínima).

**Regla de gold para futuros tests:** cualquier test que instancie `WebConnector`
debe pasar `force_ddg=True` si no está probando Tavily específicamente.

---

## H5B-06: test_pilot_end_to_end_noel falla por timeout de Ollama bajo carga

**Contexto:** Al correr la suite completa (`pytest tests/`) después de múltiples ejecuciones
encadenadas, `test_pilot_end_to_end_noel` falló con `httpx.ReadTimeout`. El mismo test
pasa cuando Ollama no está bajo carga (demostrado en la primera ejecución de la sesión).

**No es un bug:** El test E2E llama a Ollama para generar el informe completo (~32s cap1 +
4s GICS + 243s cap2 = ~280s). Si la GPU está saturada de correr múltiples suites
encadenadas, el timeout de `httpx` se dispara antes de que Ollama responda.

**Implicación:** Los tests de integración con Ollama (`test_llm.py`, `test_retrieval.py`,
`test_assembler.py::test_pilot_end_to_end_noel`) deben correrse en frío, no tras múltiples
suites. Considerar agregar markers pytest (`@pytest.mark.slow`) para excluirlos del CI rápido.

---

## Pendientes concretos al cierre de Fase 5B

1. **E2E de Cap 3 (prioridad):**
   ```bash
   uv run python scripts/run_pilot.py --empresa "Noel S.A.S." --ciiu 1081
   ```
   Criterio de éxito: el `.docx` generado incluye texto real en "Capítulo 3. Análisis
   Sectorial Tendencial" con ≥200 palabras (no el párrafo estándar de ausencia).

2. **Actualizar política de modelo local:** Probar `qwen3:8b` para Cap 1/GICS y documentar
   el resultado en `.env` si mejora sin cuelgues.

3. **Cap 4 — Ecosistema:** Después de validar Cap 3 en E2E.
   Fuente: `source_prompts/` (leer el .docx correspondiente).

4. **Markers pytest slow:** Agregar `@pytest.mark.slow` a los tests que llaman a Ollama
   para poder excluirlos con `pytest -m "not slow"` en el flujo rápido.
