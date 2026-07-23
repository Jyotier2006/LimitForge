.PHONY: install test test-redis lint typecheck quality benchmark memory build clean

install:
	python -m pip install -e ".[dev]"

test:
	pytest -q --cov=limitforge --cov-report=term-missing

test-redis:
	LIMITFORGE_REDIS_URL=redis://localhost:6379/15 pytest -q tests/integration

lint:
	ruff check .

typecheck:
	mypy src/limitforge

quality: lint typecheck test

benchmark:
	python scripts/benchmark.py --operations 100000 --workers 1 --output docs/benchmarks.md

memory:
	python scripts/memory_benchmark.py --keys 20000 --output docs/memory-results.md

build:
	python -m build
	python -m twine check dist/*

clean:
	rm -rf build dist .coverage htmlcov .pytest_cache .mypy_cache .ruff_cache src/*.egg-info
