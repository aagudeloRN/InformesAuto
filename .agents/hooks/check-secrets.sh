#!/usr/bin/env bash
# check-secrets.sh — Hook PRE-COMMIT (BLOQUEANTE)
# Rechaza el commit si detecta credenciales, claves o tokens en los cambios staged.
# Materializa la regla de la Prime Directive: nunca commitear secretos. Usar .env.
#
# Salida 0 = permitir commit. Salida != 0 = bloquear.
set -euo pipefail

# Solo revisa lo que está staged para commit.
STAGED=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null || true)
if [ -z "$STAGED" ]; then
  exit 0
fi

# Patrones de secretos comunes. Ampliar según necesidad del proyecto.
# Se buscan asignaciones tipo KEY="valor", no la mera mención de la palabra.
PATTERNS=(
  'api[_-]?key[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{12,}'
  'secret[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{8,}'
  'password[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{6,}'
  'token[[:space:]]*=[[:space:]]*["'"'"'][^"'"'"']{12,}'
  'sk-[A-Za-z0-9]{20,}'              # claves estilo OpenAI/Anthropic
  'AKIA[0-9A-Z]{16}'                 # AWS access key id
  'AIza[0-9A-Za-z_-]{30,}'           # Google API key
)

FOUND=0
for file in $STAGED; do
  # Nunca escanear el propio .env de ejemplo ni binarios.
  case "$file" in
    *.env.example|*.png|*.jpg|*.pdf|*.docx|*.dotx) continue ;;
  esac
  [ -f "$file" ] || continue

  for pat in "${PATTERNS[@]}"; do
    if git show ":$file" 2>/dev/null | grep -nEi "$pat" >/dev/null 2>&1; then
      echo "BLOQUEADO: posible secreto en '$file' (patrón: ${pat:0:24}...)"
      FOUND=1
    fi
  done
done

# Además: ningún .env real debe ir staged (solo .env.example).
for file in $STAGED; do
  case "$file" in
    *.env|.env) echo "BLOQUEADO: '$file' no debe commitearse. Usar .env.example." ; FOUND=1 ;;
  esac
done

if [ "$FOUND" -ne 0 ]; then
  echo ""
  echo "Commit detenido. Mueve los secretos a .env (en .gitignore) y reintenta."
  exit 1
fi

exit 0
