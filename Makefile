# Atajos de desarrollo. Todos los comandos usan el entorno gestionado por uv.
#   make help   → lista de comandos

IMAGE ?= credit-risk-classification
TAG   ?= local
PORT  ?= 8501

.DEFAULT_GOAL := help
.PHONY: help setup install lint format test test-fast run docker-build docker-run docker-test requirements clean

help: ## Muestra esta ayuda
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: install ## Instala dependencias y los hooks de git (primera vez)
	uv run pre-commit install

install: ## Instala todas las dependencias (runtime + dev + notebooks)
	uv sync --locked

lint: ## Ejecuta todos los chequeos de pre-commit (los mismos que CI)
	uv run pre-commit run --all-files --show-diff-on-failure

format: ## Formatea y corrige automáticamente el código
	uv run ruff check --fix .
	uv run ruff format .

test: ## Ejecuta toda la suite de pruebas con cobertura
	uv run pytest

test-fast: ## Ejecuta las pruebas omitiendo las lentas (app completa)
	uv run pytest -m "not slow" --no-cov

run: ## Levanta la app en local
	uv run streamlit run app.py --server.port $(PORT)

docker-build: ## Construye la imagen de producción
	docker build -t $(IMAGE):$(TAG) .

docker-run: docker-build ## Construye y ejecuta la imagen en http://localhost:$(PORT)
	docker run --rm -p $(PORT):8501 $(IMAGE):$(TAG)

docker-test: ## Ejecuta las pruebas en Linux (útil en macOS sin libomp)
	docker run --rm -v "$(CURDIR)":/app -w /app \
		-e UV_PROJECT_ENVIRONMENT=/opt/venv -e UV_LINK_MODE=copy \
		ghcr.io/astral-sh/uv:0.13.9-python3.11-trixie-slim \
		sh -c "apt-get update -qq && apt-get install -y -qq --no-install-recommends libgomp1 >/dev/null \
		&& uv sync --locked --no-default-groups --group dev \
		&& uv run --no-sync pytest -p no:cacheprovider"

requirements: ## Regenera requirements.txt (solo runtime) desde uv.lock
	uv export --frozen --no-default-groups --output-file=requirements.txt

clean: ## Borra cachés y artefactos locales
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml htmlcov
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
