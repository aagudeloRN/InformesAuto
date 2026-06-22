#!/usr/bin/env bash
# format-python.sh — Hook POST-EDIT (NO BLOQUEANTE)
# Tras editar un archivo .py, corre ruff (lint+fix) y black (formato) y reporta.
# NO interrumpe el plan en curso: solo mantiene el código limpio sobre la marcha.
#
# Claude Code pasa la ruta del archivo editado como $1 (o vía variable de entorno,
# según versión; este script acepta ambos).
set -uo pipefail

FILE="${1:-${CLAUDE_EDITED_FILE:-}}"

# Sin archivo o no es Python → no hacer nada.
[ -n "$FILE" ] || exit 0
case "$FILE" in
  *.py) : ;;
  *) exit 0 ;;
esac
[ -f "$FILE" ] || exit 0

echo "[format-python] $FILE"

# ruff: arregla lo auto-arreglable y reporta el resto. No aborta si falla.
if command -v ruff >/dev/null 2>&1; then
  ruff check --fix "$FILE" 2>&1 | sed 's/^/  ruff: /' || true
else
  echo "  ruff: no instalado (pip install ruff)"
fi

# black: formatea. No aborta si falla.
if command -v black >/dev/null 2>&1; then
  black --quiet "$FILE" 2>&1 | sed 's/^/  black: /' || true
  echo "  black: formateado"
else
  echo "  black: no instalado (pip install black)"
fi

# Siempre salir 0: este hook nunca bloquea.
exit 0
