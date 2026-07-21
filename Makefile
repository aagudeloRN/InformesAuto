.PHONY: check lint test

check: lint test

lint:
	uv run ruff check src/ tests/

test:
	uv run pytest -m "not slow" -q
