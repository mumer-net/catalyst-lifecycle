.PHONY: test

test:
	uv run ruff check .
	uv run ruff format --check .
	uv run pytest -q
