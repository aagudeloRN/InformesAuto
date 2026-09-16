# Feature Specification: 006 â€” EstabilizaciÃ³n, AlineaciÃ³n Documental y DefiniciÃ³n de Alcance de Inteligencia Competitiva

**Feature Branch**: `006-estabilizacion-alineacion-ic`
**Created**: 2026-09-16
**Status**: Draft (In Review / Awaiting User Success Criteria)
**Input**: AuditorÃ­a integral del sistema de generaciÃ³n de informes de inteligencia competitiva, identificaciÃ³n de discrepancias entre documentaciÃ³n, cÃ³digo y producto, estabilizaciÃ³n de tests y linter, saneamiento documental y definiciÃ³n del alcance del informe frente al patrÃ³n de referencia.

---

## Contexto del Componente y Foco del Proyecto

### 1. Foco del Producto: Informes de Inteligencia Competitiva para Empresas
El propÃ³sito fundamental de **InformesAuto** es automatizar la generaciÃ³n de informes ejecutivos de **Vigilancia e Inteligencia Competitiva** para empresas. El informe generado (en formato `.docx`) debe entregar valor estratÃ©gico C-Level a travÃ©s de una estructura de 8 bloques estÃ¡ndar:

1. **Resumen Ejecutivo (N3)**: SÃ­ntesis de alto nivel (~1 pÃ¡gina) con gancho estratÃ©gico, 3 hallazgos clave y llamado a la acciÃ³n.
2. **CapÃ­tulo 1 â€” DescripciÃ³n y ClasificaciÃ³n GICS (N0)**: IdentificaciÃ³n de la empresa focal a partir de CIIU/RUES y asignaciÃ³n canÃ³nica a uno de los 25 grupos GICS.
3. **CapÃ­tulo 2 â€” AnÃ¡lisis Competitivo (N1)**: 
   - *2.1 Jugadores Clave*: 14 actores estructurados en 3 tiers (8 globales, 3 regionales LatAm, 3 startups locales).
   - *2.2 Grupos EstratÃ©gicos*: Matriz 2Ã—2 y divisiÃ³n por enfoque de mercado y capacidades.
   - *2.3 DinÃ¡mica de Mercado*: Cuotas de mercado, volumen y contexto regional.
   - *2.4 MÃ³dulos de Competitividad*: InnovaciÃ³n, inversiÃ³n y talento.
   - *2.5 AnÃ¡lisis de Brechas*: Diferenciales competitivos frente a la empresa focal.
4. **CapÃ­tulo 3 â€” AnÃ¡lisis Sectorial Tendencial (N1)**: 6 tendencias (2 tecnolÃ³gicas, 2 econÃ³micas, 2 sociales), 4 categorÃ­as MECE y casos de estudio globales y locales.
5. **CapÃ­tulo 4 â€” Panorama del Ecosistema Empresarial (N1)**: Inversiones, integraciones verticales, M&A, Joint Ventures y alianzas estratÃ©gicas.
6. **CapÃ­tulo 5 â€” Convergencias EstratÃ©gicas (N2)**: AnÃ¡lisis multidimensional dividido en 3 ejes (tecnolÃ³gico, mercado, social/competitivo) mÃ¡s sÃ­ntesis integradora.
7. **Capitulo 6 â€” Accionables EstratÃ©gicos (N2)**: Recomendaciones prioritarias en tono propositivo para la toma de decisiones.
8. **Referencias BibliogrÃ¡ficas (N3)**: CitaciÃ³n APA 7 rigurosa, deduplicada y 100% trazable a chunks del Ã­ndice vectorial (pgvector).

---

### 2. DiagnÃ³stico de la AuditorÃ­a Integral (Estado al 2026-09-16)

La auditorÃ­a cruzada entre documentaciÃ³n, especificaciones previas (Specs 001â€‘005), base de cÃ³digo y suite de pruebas revelÃ³ cuatro grupos de discrepancias que deben abordarse bajo la metodologÃ­a *Spec-Driven*:

1. **RegresiÃ³n tÃ©cnica immediata**: El cierre de Spec 005 dejÃ³ 5 tests unitarios rotos en `ic.infrastructure.llm.gateway` y 8 errores de linter `ruff` (E501 en `scripts/`), contradiciendo la afirmaciÃ³n de `PROXIMA_SESION.md`.
2. **Desfase documental severo**: `README.md` y `ARQUITECTURA.md` permanecen congelados en Fase 8 (julio 2026); `CHANGELOG.md` no se actualiza desde v0.9.1; `ROADMAP.md` no incluye los Specs 001â€‘005; y faltan ADRs que formalicen las decisiones arquitectÃ³nicas de los Ãºltimos dos meses.
3. **Deuda tÃ©cnica estructural (Regla <300 LÃ­neas)**: Cuatro archivos crÃ­ticos superan holgadamente el lÃ­mite constitucional: `app.py` (585L), `generate_benchmarking.py` (520L), `generate_n1.py` (499L) y `_entidad_queries.py` (383L).
4. **Brechas de alcance en el informe y fuentes**: Disparidad en la madurez de las subsecciones de Cap 2 (2.3â€“2.5), riesgo de pÃ¡rrafos de ausencia (RN-001) para sectores sin suficientes fuentes locales sembradas, y pendiente la materializaciÃ³n del flujo HITL en la UI.

---

## User Scenarios & Acceptance Criteria (Spec-Driven)

### User Story 1 â€” Higiene TÃ©cnica y EstabilizaciÃ³n Inmediata (Priority: P1)

Como desarrollador o analista, necesito que la suite de pruebas unitarias y el linter del proyecto estÃ©n al 100% verdes, de modo que cualquier cambio posterior cuente con una base estable y verifique el comportamiento real sin falsos negativos.

**Why this priority**: Es el bloqueador tÃ©cnico nÃºmero uno. No se puede garantizar la integridad del sistema con 5 tests rotos y 8 errores de linter.

**Acceptance Criteria**:

1. **Given** el mÃ³dulo `src/ic/infrastructure/llm/gateway.py`, **When** se ejecuta `build_llm(settings)`, **Then** se resuelve correctamente el modelo analÃ­tico local desde `settings.llm_local_analytic_model` (sin invocar atributos inexistentes como `ollama_model`).
2. **Given** la funciÃ³n `_provider_base_and_key`, **When** se invoca con `(provider, settings, model)` o `hsettings, provider)`, **Then** la firma y sus tests asociados en `tests/test_gateway_robustez.py`stÃ¡n perfectamente alineados.
3. **Given** la funciÃ³n `build_api_llm(settings, tier="synth")`, **When** se solicita el tier de sÃ­ntesis, **Then** utiliza `settings.lm_api_synth_model` y respeta `llm_api_synth_provider`.
4. **Given** `build_resilient_api_llm`, **When** se invoca con configuraciones parciales o con fallback explÃ­cito, **Then** se construye la cadena de resiliencia sin errores posicionales ni de palabras clave en `test_fase15_resilience.py` y `test_gateway_robustez.py`.
5. **Given** los scripts en `scripts/` (`backfill_entidad_sectores.py`, `build_emis_index.py`, `seed_empresas_colombia.py`, `seed_informes_manuales.py`, `seed_startia.py`), **When** se ejecuta `uv run ruff check`, **Then** el resultado es **0 errores** (todas las lÃ­neas <= 100 caracteres).
6. **Given** el entorno local, **When** se ejecuta `uv run pytest -m "not slow and not integration"`, **Then** el 100% de las pruebas unitarias (>= 706 tests) pasan exitosamente (0 failed, 0 errors).

---

### User Story 2 â€” Saneamiento y AlineaciÃ³n Documental Completa (Priority: P1)

Como lÃ­der de proyecto o nuevo agente que ingresa al repositorio, necesito que la documentaciÃ³n viva (README, CHANGELOG, ROADMAP, ARQUITECTURA, REGLAS_NEGOCIO) refleje con exactitud la topologÃ­a actual, la historia de versiones y las decisiones vigentes.

**Why this priority**: La documentaciÃ³n desalineada induce a errores arquitectÃ³nicos en cascada y genera decisiones redundantes o destructivas.

**Acceptance Criteria**:

1. **gREADME.md`**: Actualizado para declarar el estado actual (Post Spec 005 / Spec 006 en curso), mÃ©tricas reales de cobertura y tests, arquitectura modular y guÃ­as de uso CLI/UI actualizadas.
2. **`CHANGELOG.md`**: Actualizado desde la versiÃ³n 0.9.1 asta la versiÃ³n actual (1.0.0-rc o correspondiente), registrando cronolÃ³gicamente los hitos de Fases 10â€“31 y Specs 001â€”ÀÀÔ¸(Ì¸€¨©I=5@¹µ‘€¨¨èÑÕ…±¥é…‘¼Á…É„É•™±•©…È±„½¹Í½±¥‘…§Í¸‘”MÁ•Ì€ÀÀÄ„€ÀÀÔä•ÍÑ…‰±••È±…ÌÁÉ¥½É¥‘…‘•Ì¡…¥„!%Q0äÉ½‰ÕÍÑ•è‘”™Õ•¹Ñ•Ì¸(Ğ¸€¨©IEU%QQUI¹µ‘€¨¨èÑÕ…±¥é…‘¼½¸‘¥…É…µ…Ìä‘•ÍÉ¥Á¥½¹•Ì‘”±„…ÉÅÕ¥Ñ•ÑÕÉ„µ½‘Õ±…É¥é…‘„è(€€€´‘”•¹•É…Ñ•%¹™½Éµ•€‘¥Ù¥‘¥‘¼•¸ÍÕ‰·Í‘Õ±½Ì€¡}¥¹™½Éµ•}½¹Ñ•áĞ¹Áå€°}¥¹™½Éµ•}¹½‘•Í}¸À¹Áå€°}¥¹™½Éµ•}¹½‘•Í}¸È¹Áå€°}¥¹™½Éµ•}¹½‘•Í}¸Ì¹Áå€¤¸(€€€´…Ñ•İ…ä114‘•Í…½Á±…‘¼€¡…Ñ•İ…ä¹Áå€°…Ñ•İ…å}•ÉÉ½ÉÌ¹Áå€°…Ñ•İ…å}µ½‘•±Ì¹Áå€°…Ñ•İ…å}ÁÉ¥¥¹œ¹Áå€¤¸(€€€´…Á„‘”ÁÉ•Í•¹Ñ…§Í¸‘•Í…½Á±…‘„Ûµ„Õ¥}ÅÕ•Éå}Í•ÉÙ¥•Ì¹Áå€¸(€€€´5½‘•±¼‘”½¹½¥µ¥•¹Ñ¼‘”•¹Ñ¥‘…‘•Ì€¡¹Ñ¥‘…‘€°¹Ñ¥‘…‘5•¹¥½¹€°µ•µ‰É•Ïµ…ÌÍ•Ñ½É¥…±•Ì¤¸(Ô¸€¨©H´ÀÄØäH´ÀÄÜ¨¨è½Éµ…±¥é…‘½Ì•¸‘½Ì½…É¡¥Ñ•ÑÕÉ”½€è(€€€´H´ÀÄÙ€è5½‘•±¼‘”	…Í”‘”½¹½¥µ¥•¹Ñ¼‘”¹Ñ¥‘…‘•Ì°5•µ‰É•Ïµ…Ì%Lä•‘ÕÁ±¥…§Í¸¸(€€€´H´ÀÄİ€è…Ñ•İ…ä5Õ±Ñ¤µAÉ½Ù••‘½ÈI•Í¥±¥•¹Ñ”€¡=Á•¹I½ÕÑ•È°½½±”•µ¥¹¤A$‘¥É•Ñ„°=±±…µ„¡½ÍĞ¤¸(Ø¸€¨©I1M}9=%<¹µ‘€¨¨èÑÕ…±¥é…‘¼Á…É„…±¥¹•…ÈI8´ÀÀÌ€¡µ½‘•±½ÌäÁÉ¥¥¹œ•µ¥¹¤½=Á•¹I½ÕÑ•È¤°I8´ÀÀÔ€¡…ÑÕ…°½¸…À€Èµ½‘Õ±…É¥é…‘¼¤äI8´ÀÄÄ¼ÀÄÈ€¡•ÍÑ…‘¼É•…°‘”!%Q0¤¸(Ü¸€¨©AÉ½µÁÑÌ¨¨èM¥¹É½¹¥é…§Í¸ä…Õ‘¥Ñ½Ëµ„‘”½¹Í¥ÍÑ•¹¥„•¹ÑÉ”‘½Ì½ÁÉ½µÁÑÌ½€°Í½ÕÉ•}ÁÉ½µÁÑÌ½€äÍÉŒ½¥Œ½‘½µ…¥¸½¡…¥¹Ì½€°…Í•ÕÉ…¹‘¼•°ÕµÁ±¥µ¥•¹Ñ¼‘•°Ñ½¹¼ÁÉ½Á½Í¥Ñ¥Ù¼€¡I8´ÀÀÜ€¼PµU$ÀÌ¤¸((´´´((ŒŒŒUÍ•ÈMÑ½Éä€ÌƒŠP•Õ‘„S¥¹¥„ÍÑÉÕÑÕÉ…°äÕµÁ±¥µ¥•¹Ñ¼‘”3µµ¥Ñ•Ì€ ğÌÀÀ3µ¹•…Ì¤€¡AÉ¥½É¥Ñäè@È¤()½µ¼…ÉÅÕ¥Ñ•Ñ¼‘”Í½™Ñİ…É”°É•ÅÕ¥•É¼ÅÕ”¹¥¹Ÿé¸…É¡¥Ù¼•¸•°É•Á½Í¥Ñ½É¥¼•á•‘„±…Ì€ÌÀÀ³µ¹•…Ì°…É…¹Ñ¥é…¹‘¼•°ÁÉ¥¹¥Á¥¼‘”É•ÍÁ½¹Í…‰¥±¥‘…ƒé¹¥„€¡M½¤ä™…¥±¥Ñ…¹‘¼•°µ…¹Ñ•¹¥µ¥•¹Ñ¼¸((¨©]¡äÑ¡¥ÌÁÉ¥½É¥Ñä¨¨èÌÕ¹„É•±„•ÍÑÉ¥Ñ„‘”±„½¹ÍÑ¥ÑÕ§Í¸‘•°ÁÉ½å•Ñ¼ä‘”AI%5%IQ%Yƒ
%a€¸É¡¥Ù½Ì‘”·…Ì‘”€ÔÀÀ³µ¹•…Ì…ÕµÕ±…¸‘•Á•¹‘•¹¥…Ì½Õ±Ñ…Ìä‘¥™¥Õ±Ñ…¸±„É•™…Ñ½É¥é…§Í¸•ÕÉ„¸((¨©•ÁÑ…¹”É¥Ñ•É¥„¨¨è((Ä¸€¨©ÍÉŒ½¥Œ½ÁÉ•Í•¹Ñ…Ñ¥½¸½…ÁÀ¹Áå€€ ÔàÕ0€´ø€ğÌÀÁ0¤¨¨è(€€€´1„³Í¥„‘”É•¹‘•É¥é…‘¼Í”‘¥Ù¥‘”•¸‘¥™•É•¹Ñ•ÌÙ¥ÍÑ…Ì‘•‘¥…‘…Ì€¡•¨¸…ÁÁ}•¹•É…Ñ½È¹Áä°…ÁÁ}¡¥ÍÑ½Éä¹Áä°…ÁÁ}…Õ‘¥Ğ¹Áä¤¸(€€€´…ÁÀ¹Áå€…Óé„•á±ÕÍ¥Ù…µ•¹Ñ”½µ¼‰½½ÑÍÑÉ…À°•¹ÉÕÑ…‘½È‘”Á•ÍÑ‡Å…Ìä±…å½ÕĞ•¹•É…°¸(È¸€¨©ÍÉŒ½¥Œ½‘½µ…¥¸½ÕÍ•}…Í•Ì½•¹•É…Ñ•}‰•¹¡µ…É­¥¹œ¹Áå€€ ÔÈÁ0€´ø€ğÌÀÁ0¤¨¨è(€€€´áÑÉ…§Í¸‘”ÕÑ¥±¥‘…‘•Ì‘”•¹É¥ÅÕ•¥µ¥•¹Ñ¼İ•ˆ‘”½µÁ•Ñ¥‘½É•Ìä³Í¥„‘”™½Éµ…Ñ•¼‘”Ñ…‰±…Ì½™¥¡…Ì„·Í‘Õ±½Ì½±…‰½É…‘½É•Ì½¡•Í¥Ù½Ì¸(Ì¸€¨©ÍÉŒ½¥Œ½‘½µ…¥¸½ÕÍ•}…Í•Ì½•¹•É…Ñ•}¸Ä¹Áå€€ Ğäå0€´ø€ğÌÀÁ0¤¨¨è(€€€´•Í½µÁ½Í¥§Í¸‘”±„½ÉÅÕ•ÍÑ…§Í¸‘”ÍÕˆµ·Í‘Õ±½Ì8Ää™¥±ÑÉ½Ì‘”•á±ÕÍ§Í¸•¸™Õ¹¥½¹•Ì¼±…Í•Ì…Õá¥±¥…É•Ì¸(Ğ¸€¨©ÍÉŒ½¥Œ½‘…Ñ„½É•Á½Í¥Ñ½É¥•Ì½}•¹Ñ¥‘…‘}ÅÕ•É¥•Ì¹Áå€€ ÌàÍ0€´ø€ğÌÀÁ0¤¨¨è(€€€´M•Á…É…§Í¸‘”½¹ÍÕ±Ñ…Ì‘”éÍÅÕ•‘„Á½È¹½µ‰É”½…±¥…Ì‘”±…Ì½¹ÍÕ±Ñ…Ì‘”µ•µ‰É•Ïµ…Ìä™¥±ÑÉ½ÌÍ•Ñ½É¥…±•Ì½µÁ±•©½Ì¸(Ô¸€¨©Y•É¥™¥…§Í¸‘”É•É•Í§Í¸¨¨èQÉ…Ì±…ÌÁ…ÉÑ¥¥½¹•Ì°•°€ÄÀÀ”‘”±½ÌÑ•ÍÑÌÕ¹¥Ñ…É¥½Ì”¥¹Ñ•É…‘½Ì…Í½¥…‘½Ì„•ÍÑ½Ì·Í‘Õ±½Ì½¹Ñ¥»é…¸Á…Í…¹‘¼¸((´´´((ŒŒŒUÍ•ÈMÑ½Éä€ĞƒŠP±¥¹•…§Í¸äI½‰ÕÍÑ•è‘•°%¹™½Éµ”‘”%¹Ñ•±¥•¹¥„½µÁ•Ñ¥Ñ¥Ù„€¡AÉ¥½É¥Ñäè@È¤()½µ¼ÕÍÕ…É¥¼™¥¹…°‘•°¥¹™½Éµ”€¡½¹ÍÕ±Ñ½È¼‘¥É•Ñ¥Ù¼•µÁÉ•Í…É¥…°¤°É•ÅÕ¥•É¼ÅÕ”•°¥¹™½Éµ”•¹•É…‘¼Ñ•¹„½‰•ÉÑÕÉ„…¹…³µÑ¥„½µÁ±•Ñ„°ÁÉ½™Õ¹‘¥‘…•¸‘…Ñ½Ì‘”µ•É…‘¼ä½µÁ•Ñ¥‘½É•Ì°äÁ•Éµ¥Ñ„±„Ù…±¥‘…§Í¸¡Õµ…¹„•¸ÁÕ¹Ñ½ÌËµÑ¥½Ì¸((¨©]¡äÑ¡¥ÌÁÉ¥½É¥Ñä¨¨èI•ÁÉ•Í•¹Ñ„•°Ù…±½È¹Õ±•…È‘•°ÁÉ½‘ÕÑ¼¸Í•ÕÉ„ÅÕ”•°¥¹™½Éµ”•¹•É…‘¼¹¼Í•„Õ¸Í¥µÁ±”É•ÍÕµ•¸ÍÕÁ•É™¥¥…°°Í¥¹¼Õ¹„¡•ÉÉ…µ¥•¹Ñ„‘”‘•¥Í§Í¸½µÁ•Ñ¥Ñ¥Ù„É¥ÕÉ½Í„¸((¨©•ÁÑ…¹”É¥Ñ•É¥„¨¨è((Ä¸€¨©…ÃµÑÕ±¼€È½µÁ±•Ñ¼¨¨è(€€€´%¹Ñ•É…§Í¸™½Éµ…°äÙ…±¥‘…‘„‘”±…ÌÍ•¥½¹•Ì€È¸Ä€¡)Õ…‘½É•Ì±…Ù”¤°€È¸È€¡ÉÕÁ½ÌÍÑÉ…Ó¥¥½Ì¤°€È¸Ì€¡¥»…µ¥„‘”5•É…‘¼¤°€È¸Ğ€¡7Í‘Õ±½Ì‘”½µÁ•Ñ¥Ñ¥Ù¥‘…¤ä€È¸Ô€¡	É•¡…Ì¤¸(€€€´•™¥¹¥§Í¸‘”±„Ù¥ÍÕ…±¥é…§Í¸½µÁ±•µ•¹Ñ…É¥„€¡Ñ…‰±„µ…ÑÉ¥¥…°•¹É¥ÅÕ•¥‘„¼É•…Ñ¥Ù…§Í¸‘•°É…‘…ÈÍ•Ÿé¸™••‘‰…¬‘”ÕÍÕ…É¥¼¤¸(È¸€¨©I½‰ÕÍÑ•è‘”Õ•¹Ñ•ÌäI•‘Õ§Í¸‘”C…ÉÉ…™½Ì‘”ÕÍ•¹¥„¨¨è(€€€´ÍÑÉ…Ñ•¥„‘”‹¥ÍÅÕ•‘„ä™…±±‰…¬Á…É„Í•Ñ½É•Ì™Õ•É„‘”±¥µ•¹Ñ½Ì€¡‘•™¥¹¥§Í¸‘”™Õ•¹Ñ•Ì‘”•¹É¥ÅÕ•¥µ¥•¹Ñ¼İ•ˆä‘¥É•Ñ½É¥½Ì±½…±•Ì¤¸(€€€´I•½¹¥±¥…§Í¸‘”•¹Ñ¥‘…‘•Ì5%L½9HÁ½È9%P€¡P´ÀÔÁˆ¤Á…É„•Ù¥Ñ…È½µÁ•Ñ¥‘½É•Ì‘ÕÁ±¥…‘½Ì¼µ…°Ñ¥Á¥™¥…‘½Ì¸(Ì¸€¨©±Õ©¼!%Q0€¡!Õµ…¸µ%¸µQ¡”µ1½½À¤=Á•É…Ñ¥Ù¼•¸U$¨¨è(€€€´A•ÍÑ‡Å„¼Á…¹•°‘”É•Ù¥Í§Í¸‘½¹‘”•°…¹…±¥ÍÑ„ÁÕ•‘”Ù•È±„±¥ÍÑ„‘”½µÁ•Ñ¥‘½É•Ì‘•Ñ•Ñ…‘½Ì…¹Ñ•Ì‘”±„•¹•É…§Í¸™¥¹…°°…É•…È½•±¥µ¥¹…È…Ñ½É•Ìµ…¹Õ…±µ•¹Ñ”ä…ÁÉ½‰…È±„Ù•ÉÍ§Í¸‘•™¥¹¥Ñ¥Ù„¸((´´´((ŒŒA±…¸‘”©•Õ§Í¸ä•Á•¹‘•¹¥…Ì((Ä¸€¨©A…Í¼€Ä¨¨èI•Í½±Ù•È€¨©ULÄ¨¨€¡!¥¥•¹”S¥¹¥„è€ÔÑ•ÍÑÌ€¬€à±¥¹Ñ•È•ÉÉ½ÉÌ¤¸(È¸€¨©A…Í¼€È¨¨è©•ÕÑ…È€¨©ULÈ¨¨€¡½Õµ•¹Ñ…§Í¸½µÁ±•Ñ„èI5°!91=°I=5@°IEU%QQUI°H´ÀÄØ¼ÀÄÜ°I1M}9=%<¤¸(Ì¸€¨©A…Í¼€Ì¨¨è©•ÕÑ…È€¨©ULÌ¨¨€¡5½‘Õ±…É¥é…§Í¸‘”…ÁÀ¹Áå€°•¹•É…Ñ•}‰•¹¡µ…É­¥¹œ¹Áå€°•¹•É…Ñ•}¸Ä¹Áå€°}•¹Ñ¥‘…‘}ÅÕ•É¥•Ì¹Áå€¤¸(Ğ¸€¨©A…Í¼€Ğ¨¨èQÉ…‰…©…È½¸•°ÕÍÕ…É¥¼•¸€¨©ULĞ¨¨Á…É„‘•™¥¹¥ÈÉ¥Ñ•É¥½Ì‘”ƒ¥á¥Ñ¼•ÍÁ•µ™¥½Ì‘”±…ÌÍ•¥½¹•Ì‘•°¥¹™½Éµ”ä™±Õ©¼!%Q0¸(