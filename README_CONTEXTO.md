# Sistema de Informes de Inteligencia Competitiva — Contexto del Proyecto

**Estado:** En planeación → preparado para Fase 0 (andamiaje)  
**Piloto:** Descripción Empresa → Sector GICS → Benchmarking (Cap 2) → ensamblado  
**Estimación:** ~8-11 días de desarrollo (1 persona con Claude Code)

---

## Lo que ya se completó

✅ **Decisiones arquitectónicas cerradas (ADR-001, ADR-002, ADR-003)**
- RAG propio reemplaza NotebookLM en producción
- Routing local-primero (Ollama) con escalado selectivo a API
- Doble vía de ingesta de fuentes (automática + manual) convergiendo en un solo índice vectorial

✅ **CLAUDE.md + hooks esenciales**
- Reglas duras del proyecto (Tier 1-4)
- Hook de secretos (pre-commit, bloqueante)
- Hook de modelos hardcodeados (pre-commit, bloqueante)
- Hook de formateo Python (post-edit, no bloqueante)

✅ **Grafo de dependencias (DAG) del informe**
- Nivel 0: Descripción Empresa, Sector GICS, Ecuaciones búsqueda (fundacionales)
- Nivel 1: Cap2 Benchmarking, Cap3 Tendencial, Cap4 Ecosistema, Cap5 Convergencia (paralelos)
- Nivel 2: Cap6 Accionables (cruza N1)
- Nivel 3: Resumen Ejecutivo, Párrafos Intro, Referencias (consumen informe completo)
- Ensamblado en plantilla membrete .docx
- Evaluar informe (opcional, gate de calidad)

---

## Lo que falta

**Fase 1 (próxima) — Revisar prompts del piloto e identificar refinamientos**

Entrada: ~18 archivos `.docx` con prompts originales (diseñados para NotebookLM manual)  
Salida: 3 plantillas `.md` parametrizadas (Descripción Empresa, Sector GICS, Benchmarking) + decisión clara de cuál refinamiento iterativo heredado de NotebookLM se conserva en el sistema automatizado

Esto requiere leer y analizar:
1. `1__Prompt_Descripción_Empresa.docx` — insumo: RUES, entrada usuario. Output: descripción empresa.
2. `2__Prompt_Sector_GIS_de_la_empresa.docx` — insumo: descripción empresa + 25 grupos GICS. Output: clasificación GICS.
3. `3__Prompt_-_Capítulo_2_-_Benchmarking.docx` — insumo: descripción + (retrieval de 14 competidores). Output: análisis competitivo con citas.

**Fases 2-6 (después de Fase 1)**
- Fase 0: Andamiaje (estructura de carpetas, Docker, esquema PostgreSQL)
- Fase 2: Retrieval (conectores web + RUES + chunking + pgvector)
- Fase 3: Orquestación LLM (cadenas, circuit breaker, faithful/gate)
- Fase 4: Ensamblado en membrete (python-docx, citación APA)
- Fase 5: Tests e integración del piloto
- Fase 6: Medición costo/tiempo

---

## Contexto del entorno

**Hardware:** WSL2 16GB RAM, RTX 2000 Ada 8GB VRAM  
**Benchmarks:** Ollama ~18 t/s (Qwen2.5-Coder 7B)  
**Caso de referencia:** Compañía de Galletas NOEL SAS (Grupo Nutresa)

**Infraestructura base (desde Prime Directive):**
- Ollama en host (qwen2.5, gemma3, llama3.2, nomic-embed-text)
- PostgreSQL + pgvector dockerizado (bind mount, esquema-por-proyecto)
- Servicios compartidos: NO levantar instancias propias de BD/modelos

**Stack definido:**
- Backend: FastAPI
- UI: Streamlit
- Orquestación: LangChain/LlamaIndex (ojo: decisión final de cuál en Fase 0)
- ORM: SQLAlchemy
- Wrapper de LLM: punto único de control de presupuesto/fallback/logging

---

## Los prompts originales (que falta revisar)

Estructura observada tras leer los encabezados de los 18 prompts:

| # | Nombre | Tipo | Rol | Fuentes | Salida |
|---|--------|------|-----|---------|--------|
| 0 | Ecuaciones búsqueda | Meta | define estrategia de retrieval | booleano + keywords | ecuaciones por canal (web, APIs académicas) |
| 1 | Descripción Empresa | Fundacional | ingesta RUES + input usuario | RUES/datos usuario | descripción estructurada |
| 2 | Sector GICS | Fundacional | clasificación industrial | descripción empresa + 25 grupos GICS | clasificación + análisis sectorial |
| 3 | Cap 2 Benchmarking | Analítico N1 | benchmarking competitivo | descripción + web/retrieval (14 actores) | análisis comparativo con citas |
| 4 (x3) | Mercado (opcional) | Analítico N1 | análisis de mercado | PDFs sectoriales, web | segmento mercado (opcional) |
| 5 | Gestiones Anexas | Procesamiento | refinar output mercado | salida anterior | mercado limpio |
| 6 | Cap 3 Tendencial | Analítico N1 | análisis tendencial (tecno/econ/social) | descripción + retrieval académico/web | tendencias con citas |
| 7 | Cap 4 Ecosistema | Analítico N1 | panorama ecosistema (local Medellín) | descripción + retrieval local/global | mapeo ecosistema |
| 8 | Cap 5 Convergencia | Analítico N1 | 4 áreas estratégicas convergentes | descripción + retrieval cruzado | convergencias identificadas |
| 9 | Cap 6 Accionables | Síntesis N2 | síntesis de Cap 2+3+4+5 | salidas de N1 | recomendaciones accionables |
| 10 | Párrafos Introductorios | Meta N3 | intro del informe | informe completo | párrafos contexto |
| 11 | Resumen Ejecutivo | Meta N3 | resumen de conclusiones | informe completo | resumen 1-2 págs |
| 12 | Referencias | Meta N3 | compilar citas en APA | todas las fuentes usadas | bibliografía APA |
| 13 | Evaluar Informe | Opcional | auditoría de calidad | informe completo | feedback de vacíos, fortalezas |

**Cada capítulo analítico (3, 6, 7, 8) trae pasos de refinamiento heredados de NotebookLM:**
- Ej. Cap 3 tiene: generación inicial → mejora → divide en párrafos → corrige formato
- **Decisión pendiente:** cuál se colapsa al system prompt (formato, división, prefijos) y cuál se conserva como paso real (porque requiere nueva llamada LLM).

---

## Decisiones ya tomadas

| Decisión | Valor |
|----------|-------|
| Motor de retrieval | RAG propio (pgvector + nomic-embed-text local) |
| NotebookLM en producción | NO — solo herramienta manual de exploración |
| Routing de modelos | Local primero (Ollama); escala a API solo si no pasa umbral de calidad |
| Control de presupuesto | Gateway LLM único (wrapper en infrastructure/) |
| Presupuesto/informe | ≤ 1 USD |
| Datos ausentes | Determinista: si retrieval no supera umbral, NO llama LLM; inserta párrafo ausencia + recomendación usuario |
| Fuentes automáticas | OpenAlex (primaria) + arXiv + Crossref + Semantic Scholar (opcional) + web (Tavily/DuckDuckGo) |
| Fuentes manuales | PDFs sin API: EMIS, informes sectoriales pago (Fortune, etc.) → mismo índice vectorial |
| Google Scholar | NO como fuente programática (bloquea scraping); solo descubrimiento manual |
| Ecuaciones búsqueda | Booleanas compactas para web; keywords + filtros estructurados para APIs académicas |
| Concurrencia | NO — un informe a la vez |
| Privacidad | No hay: solo datos libres/públicos, sin acceso a BDs privadas |
| Producto | Interno de Ruta N / equipo, sin necesidad de escalabilidad multi-usuario |

---

## Siguientes pasos en orden acordado

1. **Revisar prompts del piloto** (Descripción Empresa, Sector GICS, Benchmarking)
   - Leer cada uno, identificar pasos de refinamiento
   - Decidir cuál se colapsa al system prompt, cuál es paso real
   - Generar plantillas `.md` parametrizadas (con variables como `{nombre_empresa}`, `{sector_ciuu}`, etc.)
   
2. **Escribir CLAUDE.md y Prime Directive en el repo** (ya lo tienes, copia a `/docs/architecture/`)

3. **Fase 0: Andamiaje**
   - Estructura de carpetas (presentation/, domain/, data/, infrastructure/, shared/)
   - Docker compose, PostgreSQL + pgvector
   - `.env.example`
   - Esquema de BD inicial (tablas: Empresas, HistorialInformes, DocumentosLocales, EmbeddingsVectoriales)

4. **Fase 1-6 del piloto** (ya con especificación clara de prompts)

---

## Archivos generados que tienes

```
/adrs/
  ADR-001-rag-propio-reemplaza-notebooklm.md
  ADR-002-routing-local-primero-escalado-api.md
  ADR-003-estrategia-fuentes-doble-via.md

/proyecto/
  CLAUDE.md
  .claude/
    settings.json
    hooks/
      check-secrets.sh
      check-hardcoded-models.sh
      format-python.sh

/uploads/ (originales del usuario)
  011_Hoja_membreteESP.dotx (plantilla membrete)
  PRIME_DIRECTIVE.md
  roo-code-ollama-setup.md
  wsl2-llm-benchmark-report.md
  1__Prompt_Descripción_Empresa.docx
  2__Prompt_Sector_GIS_de_la_empresa.docx
  3__Prompt_-_Capítulo_2_-_Benchmarking.docx
  ... (18 prompts totales)
```

---

## Cómo proceder en Claude Code

1. Copia los ADRs, CLAUDE.md y hooks a tu repo (`docs/architecture/ADR-*.md`, `.claude/`, raíz del repo)
2. Copia la Prime Directive a `docs/architecture/PRIME_DIRECTIVE.md`
3. Abre Claude Code en el repo
4. Inicia con el prompt del siguiente chat pasándole este README completo
5. Primera tarea: leer y analizar los tres prompts del piloto (`1__Prompt_Descripción_Empresa.docx`, etc.)

**Instrucción para Claude Code:**
- Usa Plan Mode para todo lo no trivial
- Si la realidad (qué ves al leer los archivos) no coincide con supuestos del plan, vuelve a Plan Mode
- Los hooks se disparan automáticamente; no tienes que hacer nada especial
- Commitea frecuentemente (Conventional Commits)

---

Fin del contexto. Prosigue al siguiente chat.
