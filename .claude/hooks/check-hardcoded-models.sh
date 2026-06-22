#!/usr/bin/env bash
# check-hardcoded-models.sh — Hook PRE-COMMIT (BLOQUEANTE)
# Rechaza el commit si detecta nombres de modelo escritos directamente en código
# de aplicación. Materializa ADR-002: los modelos viven en .env + tabla de routing.
#
# Se permiten en: archivos de config, .env.example, tests, docs y los propios ADRs.
# Salida 0 = permitir. Salida != 0 = bloquear.
set -euo pipefail

STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
if [ -z "$STAGED" ]; then
  exit 0
fi

# Familias de nombres de modelo a vigilar. Ajustar a los modelos del entorno.
MODEL_PATTERNS=(
  'qwen[0-9]'
  'gemma[0-9]'
  'llama[0-9]'
  'nomic-embed'
  'claude-[a-z0-9]'
  'gemini-[0-9]'
  'gpt-[0-9]'
  'mixtral'
  'mistral-'
)

FOUND=0
for file in $STAGED; do
  # Solo código de aplicación Python. Excluir rutas donde SÍ se permite nombrar modelos.
  case "$file" in
    *.py) : ;;
    *) continue ;;
  esac
  case "$file" in
    config/*|configs/*|*/config/*|*/configs/*|*settings*|tests/*|*/tests/*|test_*|*_test.py|docs/*|*/docs/*) continue ;;
  esac
  [ -f "$file" ] || continue

  for pat in "${MODEL_PATTERNS[@]}"; do
    # Buscar el patrón dentro de comillas (literal en código).
    if git show ":$file" 2>/dev/null | grep -nEi "[\"'][^\"']*${pat}" >/dev/null 2>&1; then
      LINES=$(git show ":$file" 2>/dev/null | grep -nEi "[\"'][^\"']*${pat}" | head -3)
      echo "BLOQUEADO: nombre de modelo hardcodeado en '$file':"
      echo "$LINES" | sed 's/^/    /'
      FOUND=1
    fi
  done
done

if [ "$FOUND" -ne 0 ]; then
  echo ""
  echo "Commit detenido. Mueve el nombre del modelo a .env / tabla de routing (ADR-002)."
  echo "Si es un caso legítimo (config, test, doc), ubícalo en esas rutas."
  exit 1
fi

exit 0
