"""Verifica conectividad con todos los servicios externos del proyecto.

Uso:
    uv run python scripts/test_connections.py

Costo estimado por ejecución:
    - Ollama / PostgreSQL / OpenAlex: $0.00
    - OpenRouter (free): $0.00
    - Tavily: 1 crédito (de ~1000/mes del free tier)

No ejecutar este script en loops ni en CI — es para validación manual de credenciales.
"""

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

import httpx
import sqlalchemy

VERDE = "\033[92m✅"
ROJO = "\033[91m❌"
AMARILLO = "\033[93m⚠️"
RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {VERDE} {msg}{RESET}")


def err(msg: str) -> None:
    print(f"  {ROJO} {msg}{RESET}")


def warn(msg: str) -> None:
    print(f"  {AMARILLO} {msg}{RESET}")


def _section(title: str) -> None:
    print(f"\n{'─' * 55}")
    print(f"  {title}")
    print(f"{'─' * 55}")


# ── 1. Ollama ──────────────────────────────────────────────────────────────────
def check_ollama(base_url: str) -> bool:
    _section("Ollama (local, sin costo)")
    try:
        t0 = time.time()
        resp = httpx.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        elapsed = time.time() - t0
        if models:
            ok(f"{len(models)} modelos disponibles ({elapsed:.1f}s):")
            for m in sorted(models, key=lambda x: x["size"]):
                gb = m["size"] / 1e9
                safe = "✅ WSL-safe" if gb < 7 else "⚠️  >7GB"
                print(f"       {m['name']:<40} {gb:.1f} GB  {safe}")
        else:
            warn("Ollama responde pero no hay modelos instalados")
        return True
    except Exception as e:
        err(f"Ollama no disponible: {e}")
        return False


# ── 2. PostgreSQL ──────────────────────────────────────────────────────────────
def check_postgres(database_url: str, schema: str) -> bool:
    _section("PostgreSQL + pgvector (sin costo)")
    try:
        t0 = time.time()
        engine = sqlalchemy.create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(
                sqlalchemy.text(
                    f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_schema = '{schema}'"
                )
            ).fetchall()
        engine.dispose()
        elapsed = time.time() - t0
        tablas = [r[0] for r in result]
        ok(f"Conectado — schema '{schema}', {len(tablas)} tablas ({elapsed:.1f}s):")
        for t in sorted(tablas):
            print(f"       · {t}")
        return True
    except Exception as e:
        err(f"PostgreSQL no disponible: {e}")
        return False


# ── 3. OpenRouter ──────────────────────────────────────────────────────────────
def check_openrouter(base_url: str, api_key: str, model: str, tier: str) -> bool:
    if not api_key:
        warn(f"OpenRouter {tier}: OPENROUTER_API_KEY vacía — saltar")
        return False
    if not model:
        warn(f"OpenRouter {tier}: modelo no configurado en .env — saltar")
        return False
    try:
        t0 = time.time()
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/aagudeloRN/informes-ic",
                "X-Title": "InformesAuto-IC",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Responde solo: OK"}],
                "max_tokens": 5,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        usage = data.get("usage", {})
        elapsed = time.time() - t0
        ok(
            f"OpenRouter [{tier}] — {model}\n"
            f"       Respuesta: '{content}' | "
            f"tokens in={usage.get('prompt_tokens','?')} "
            f"out={usage.get('completion_tokens','?')} | "
            f"{elapsed:.1f}s"
        )
        return True
    except httpx.HTTPStatusError as e:
        err(f"OpenRouter [{tier}] HTTP {e.response.status_code}: {e.response.text[:200]}")
        return False
    except Exception as e:
        err(f"OpenRouter [{tier}]: {e}")
        return False


# ── 4. Tavily ─────────────────────────────────────────────────────────────────
def check_tavily(api_key: str) -> bool:
    _section("Tavily (⚠️  1 crédito del free tier — ~1000/mes)")
    if not api_key:
        warn("TAVILY_API_KEY vacía — usando DDG automáticamente en producción")
        return True
    try:
        t0 = time.time()
        resp = httpx.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": "Colombia sector alimentos procesados tendencias",
                "max_results": 3,
                "search_depth": "basic",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        elapsed = time.time() - t0
        ok(f"{len(results)} resultados en {elapsed:.1f}s (1 crédito Tavily consumido)")
        for r in results:
            print(f"       · {r.get('title','?')[:60]}")
        return True
    except httpx.HTTPStatusError as e:
        err(f"Tavily HTTP {e.response.status_code}: {e.response.text[:200]}")
        return False
    except Exception as e:
        err(f"Tavily: {e}")
        return False


# ── 5. OpenAlex ───────────────────────────────────────────────────────────────
def check_openalex(email: str) -> bool:
    _section("OpenAlex REST API (sin costo, sin API key)")
    try:
        t0 = time.time()
        params = {
            "search": "food industry trends Colombia Latin America",
            "per-page": "3",
            "sort": "cited_by_count:desc",
        }
        if email:
            params["mailto"] = email

        resp = httpx.get(
            "https://api.openalex.org/works",
            params=params,
            timeout=15,
            headers={"User-Agent": f"InformesAuto/0.5 (mailto:{email or 'anon'})"},
        )
        resp.raise_for_status()
        data = resp.json()
        works = data.get("results", [])
        meta = data.get("meta", {})
        elapsed = time.time() - t0
        pool = "polite pool ✅" if email else "anonymous pool"
        ok(
            f"{len(works)} trabajos devueltos de {meta.get('count','?')} totales "
            f"| {pool} | {elapsed:.1f}s"
        )
        for w in works:
            titulo = w.get("title", "Sin título")[:70]
            año = w.get("publication_year", "?")
            citas = w.get("cited_by_count", 0)
            print(f"       · [{año}] {titulo} ({citas} citas)")
        return True
    except Exception as e:
        err(f"OpenAlex: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    print("\n" + "═" * 55)
    print("  VERIFICACIÓN DE CONEXIONES — InformesAuto")
    print("═" * 55)

    from ic.shared.config import get_settings
    s = get_settings()

    resultados: dict[str, bool] = {}

    resultados["Ollama"] = check_ollama(s.ollama_base_url)
    resultados["PostgreSQL"] = check_postgres(s.database_url, s.db_schema)

    _section("OpenRouter (sin costo — modelos free)")
    resultados["OpenRouter free"] = check_openrouter(
        s.openrouter_base_url, s.openrouter_api_key, s.llm_api_free_model, "free"
    )
    resultados["OpenRouter synth"] = check_openrouter(
        s.openrouter_base_url, s.openrouter_api_key, s.llm_api_synth_model, "synth"
    )

    resultados["Tavily"] = check_tavily(s.tavily_api_key)
    resultados["OpenAlex"] = check_openalex(s.openalex_email)

    # ── Resumen ────────────────────────────────────────────────────────────────
    print("\n" + "═" * 55)
    print("  RESUMEN")
    print("═" * 55)
    todos_ok = True
    for nombre, estado in resultados.items():
        simbolo = f"{VERDE}" if estado else f"{ROJO}"
        print(f"  {simbolo} {nombre}{RESET}")
        if not estado:
            todos_ok = False

    if todos_ok:
        print(f"\n  {VERDE} Todos los servicios operativos — listo para Fase 5B{RESET}")
    else:
        print(f"\n  {AMARILLO} Algunos servicios necesitan atención{RESET}")

    sys.exit(0 if todos_ok else 1)


if __name__ == "__main__":
    main()
