# Instrucciones de Arranque en VS Code

## Paso 1: Estructura de carpetas inicial

En tu máquina, crea la estructura del proyecto:

```bash
mkdir -p informesAuto
cd informesAuto

# Estructura base (ya incluida en los archivos que descargaste)
mkdir -p docs/architecture docs/prompts docs/decisions .claude/hooks config

# Copia los archivos descargados:
# - Copiar CLAUDE.md a la raíz del proyecto
# - Copiar .claude/hooks/*.sh a .claude/hooks/
# - Copiar .claude/settings.json a .claude/
# - Copiar ADR-*.md a docs/architecture/
# - Copiar PRIME_DIRECTIVE.md a docs/architecture/
# - Copiar README_CONTEXTO.md a la raíz
# - Copiar PROMPT_CLAUDE_CODE.md a la raíz
# - Copiar los 18 prompts .docx a una carpeta /source_prompts/ (referencia, no código)
# - Copiar 011_Hoja_membreteESP.dotx a templates/
```

## Paso 2: Inicializar git (obligatorio para que los hooks funcionen)

```bash
git init
git config user.email "alvaro.agudelo@rutanmedellin.org"
git config user.name "aagudeloRN"

# Crear .gitignore (crucial)
cat > .gitignore << 'EOF'
.env
.env.local
__pycache__/
*.pyc
.venv/
venv/
dist/
build/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.idea/
*.swp
*.swo
*~
.DS_Store
EOF

git add .
git commit -m "chore: estructura inicial del proyecto"
```

## Paso 3: Abrir en VS Code y activar Roo Code / Claude Code

```bash
code .
```

En VS Code:
1. Instala la extensión **Roo Code** o **Claude Code** (según cuál uses)
2. En la barra lateral, abre el panel de Roo Code / Claude Code
3. Elige tu entorno:
   - Si usas **Roo Code (local):** conecta a `http://localhost:11434/v1` (Ollama en host)
   - Si usas **Claude Code (web):** API de Anthropic (si tiene acceso)

## Paso 4: Copiar los tres ADRs a su lugar

Asegúrate de que estos archivos estén en `docs/architecture/`:
- `ADR-001-rag-propio-reemplaza-notebooklm.md`
- `ADR-002-routing-local-primero-escalado-api.md`
- `ADR-003-estrategia-fuentes-doble-via.md`

Y que `PRIME_DIRECTIVE.md` también esté ahí (es tu referencia viva).

## Paso 5: Copiar los prompts originales (para lectura)

Crea carpeta de referencia:

```bash
mkdir -p source_prompts
# Copiar todos los .docx de prompts aquí
```

Estos son solo de referencia; NO van a código. Claude Code los leerá, analizará y generará versiones `.md` parametrizadas en `docs/prompts/`.

## Paso 6: Verificar que los hooks se ven

En VS Code, abre la terminal integrada y corre:

```bash
ls -la .claude/hooks/
chmod +x .claude/hooks/*.sh
bash -n .claude/hooks/check-secrets.sh && echo "✓ sintaxis OK"
```

## Paso 7: Lanzar Claude Code

En el panel de Claude Code:
1. Click en "Start Chat"
2. Pega el contenido del archivo `PROMPT_CLAUDE_CODE.md` (o abre ese archivo y que lo lea Claude)
3. Alternativamente, abre `PROMPT_CLAUDE_CODE.md` en el editor y pasa su contenido como contexto

Claude Code debería cargar el CLAUDE.md automáticamente (se detecta al iniciar sesión).

---

## Checklist antes de empezar

- [x] Estructura de carpetas creada
- [x] Git inicializado (sin stage de código, solo estructura)
- [x] `.gitignore` en su lugar
- [x] Archivos ADR en `docs/architecture/`
- [x] PRIME_DIRECTIVE.md en `docs/architecture/`
- [x] CLAUDE.md en raíz
- [x] `.claude/` con hooks y settings.json
- [x] Prompts originales en `source_prompts/` (referencia)
- [x] Roo Code / Claude Code instalado y conectado

---

## Qué espera Claude Code

Cuando abras el chat con el PROMPT_CLAUDE_CODE.md, Claude espera que haya:
- README_CONTEXTO.md (para contexto)
- CLAUDE.md (reglas operativas)
- Los ADRs en docs/architecture/ (para referencia)
- Los 18 prompts .docx en algún lado accesible (source_prompts/)

Si algo falta, Claude lo pedirá antes de proceder. No es un problema.

---

## Comando útil durante sesión

Si necesitas verificar que todo sigue en su lugar:

```bash
git status
git log --oneline  # historial de commits
```

Claude Code puede hacer commits automáticamente si está configurado; si no, tú los haces con:

```bash
git add docs/prompts/prompt-*.md
git commit -m "docs: plantillas parametrizadas de prompts del piloto"
```

---

## Notas finales

- Los hooks de bloqueo (check-secrets, check-hardcoded-models) se activan en commit. Si alguno bloquea, leerás un error claro: sigue la instrucción.
- El hook de formato corre tras cada edición de .py, silenciosamente.
- Si en algún momento necesitas deshabilitar un hook temporalmente (ej. prueba rápida), puedes con `git commit --no-verify`, pero evítalo: los hooks están ahí por una razón.
- Todos los archivos que generes deben compilar/ejecutar. La Prime Directive lo exige.

---

Estás listo. Abre Claude Code y lanza el PROMPT_CLAUDE_CODE.md.
