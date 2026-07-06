# Hallazgos Fase 5F

**Fecha:** 2026-07-06
**Contexto:** Párrafos intro por capítulo + paralelización N1 + tracking de costo real

---

## H5F-01 — Paralelización N1 con ThreadPoolExecutor: thread-safety de SQLAlchemy

**Problema:** Los tres capítulos N1 (Benchmarking, Tendencias, Ecosistema) son
independientes entre sí y candidatos a paralelización. El bloqueo previo era que los
tres use cases compartían la misma sesión SQLAlchemy (`SessionLocal()`), que no es
thread-safe.

**Solución:** Cada hilo crea su propia sesión dentro de un helper `_make_store_and_run(fn)`:

```python
def _make_store_and_run(fn):
    with SessionLocal() as db_t:
        repo_t = EmbeddingRepository(db_t)
        store_t = PGVectorStore(embedder, repo_t, settings)
        return fn(store_t)
```

`ThreadPoolExecutor(max_workers=3)` ejecuta los tres fns en paralelo. La barrera es
`f2/f3/f4.result()` — Python espera a que los tres futuros completen antes de continuar
a N2.

**Seguridad de RAM en WSL2 8GB:** Cap 2 usa Ollama local; Caps 3 y 4 usan OpenRouter
(API, sin RAM local). No hay solapamiento de carga de modelos: las llamadas API no
consumen VRAM, y `keep_alive:0` asegura que Ollama libere el modelo tras Cap 2.

**Ganancia medida:** tiempo de pared N1 ≈ `max(cap2, cap3, cap4)` en lugar de
`cap2 + cap3 + cap4`. En condiciones normales (Ollama ~60s, API ~30-90s), el
ahorro esperado es 60-120 segundos.

---

## H5F-02 — Párrafos introductorios: posición y condición de aplicación

**Decisión:** Los intros se añaden **después** de la barrera N1 (para N1) y **después**
de cada cap N2, no dentro del hilo paralelo. Razones:

1. Son llamadas API secuenciales ligeras — no justifican paralelizar.
2. Añadirlos dentro del hilo crearía closures complejos con captura de estado mutable.
3. Si `retrieval_suficiente = False` el capítulo contiene un párrafo de ausencia; añadir
   un intro encima sería incoherente, por eso la condición `cap_obj.retrieval_suficiente`.

`intro_chain = build_chain_intro(api_llm)` se construye **una sola vez** fuera de los
bucles para no re-instanciar la cadena en cada iteración.

**Tier elegido:** `api_llm` free (no `api_llm_synth`). Los intros son generación simple
(2-3 oraciones), no requieren el modelo de síntesis, y mantener el tier free controla
el costo.

---

## H5F-03 — CostTracker: wiring completado en run_pilot.py

El `CostTracker` y `OpenRouterGatewayLLM` ya tenían la infraestructura completa desde
Fase 5A. El único pendiente era instanciar el tracker en `main()` y pasarlo como
`cost_tracker=tracker` a los tres `build_api_llm()`.

El resumen final reemplaza el placeholder `$0.00 (Etapa B)` con:
- Costo total en USD
- Tokens in/out totales
- Desglose por llamada (modelo, tokens, costo individual)

Para modelos `:free` el costo es exactamente `$0.0000` — el desglose sigue siendo útil
para auditar el uso de tokens y detectar contextos excesivamente largos.

---

## H5F-04 — FakeListChatModel vs FakeChatModel en tests

`langchain_core.language_models.fake_chat_models.FakeChatModel` ignora el parámetro
`responses` y siempre devuelve `"fake response"`. La clase correcta para propagar
respuestas predefinidas es `FakeListChatModel`, que sí cicla por la lista `responses`.

**Regla para tests futuros:** usar `FakeListChatModel(responses=["texto esperado"])` para
tests de propagación de respuesta; `FakeChatModel()` solo para tests de estructura
(verificar que la cadena retorna un Runnable, etc.).

---

## Archivos añadidos / modificados

| Tipo | Archivo |
|------|---------|
| Nuevo | `src/ic/domain/chains/chain_intro.py` |
| Nuevo | `tests/test_chain_intro.py` (4 tests: 3 fast + 1 slow) |
| Modificado | `scripts/run_pilot.py` (paralelización N1, intros, costo real) |
| Modificado | `CHANGELOG.md` (v0.6.0) |
| Modificado | `README.md` (estado Fase 5F, 81 fast tests) |
| Modificado | `docs/architecture/ARQUITECTURA.md` (v5F, sección Fase 5F, pendientes) |

---

## Métricas de calidad

- Tests fast antes de Fase 5F: 78 passed (tras correctivo 0.5.5)
- Tests fast después de Fase 5F: 81 passed, 2 skipped, 9 deselected (slow)
- Ningún test existente roto

---

## Próxima fase: 6 — Validación E2E + UI Streamlit

El pipeline completo está implementado. El siguiente paso natural es:
1. **Correr un informe real** (`run_pilot.py --empresa "Noel S.A.S."`) con todos los
   servicios activos y validar el `.docx` generado (contenido, citas APA, intros,
   coherencia entre capítulos).
2. Si el E2E pasa: implementar la UI Streamlit (`presentation/app.py`).
3. Opcional: persistencia de historial en BD (`InformeRepository.save()`).
