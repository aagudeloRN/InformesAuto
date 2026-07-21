#!/usr/bin/env bash
# Bloquea el commit si ruff check detecta errores (DT-018).
# Corre antes de check-secrets y check-hardcoded-models en el PreToolUse de git commit.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
uv run ruff check src/ tests/
