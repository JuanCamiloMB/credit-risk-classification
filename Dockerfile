# syntax=docker/dockerfile:1.7
# ─────────────────────────────────────────────
# Imagen de producción de la app Streamlit.
#   - Multi-stage: las herramientas de build (uv) no llegan a la imagen final.
#   - Solo dependencias de runtime (sin notebooks, pycaret ni herramientas de dev).
#   - Usuario no-root y HEALTHCHECK contra el endpoint de salud de Streamlit.
# Las imágenes base van fijadas por digest; Dependabot las mantiene al día.
# ─────────────────────────────────────────────

ARG PYTHON_IMAGE=python:3.11.18-slim-trixie@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.13.9@sha256:d3b601f0c7b118bc1753febf7c41cc80981df678445e0254284eecf84db79a7d

FROM ${UV_IMAGE} AS uv

# ── Etapa 1: resolver e instalar dependencias en un virtualenv ──────────────
FROM ${PYTHON_IMAGE} AS builder

COPY --from=uv /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Solo se usan pyproject.toml + uv.lock: esta capa se cachea mientras
# no cambien las dependencias, aunque cambie el código.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-default-groups --no-install-project

# ── Etapa 2: runtime mínimo ─────────────────────────────────────────────────
FROM ${PYTHON_IMAGE} AS runtime

# Parches de seguridad del SO publicados después de la imagen base, y
# libgomp1: runtime de OpenMP que necesita LightGBM.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# La app corre desde /opt/venv: pip/setuptools/wheel del Python del sistema
# no se usan y solo amplían la superficie de ataque.
RUN python -m pip uninstall -y pip setuptools wheel

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home app

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_FILE_WATCHER_TYPE=none \
    STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=type \
    STREAMLIT_CLIENT_TOOLBAR_MODE=minimal

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Código y artefactos que la app necesita en tiempo de ejecución
# (propiedad de root: el usuario de la app solo puede leerlos).
COPY .streamlit/ .streamlit/
COPY app.py config.py styles.py ./
COPY tabs/ tabs/
COPY utils/ utils/
COPY models/gbc_best_model.joblib models/lightgbm_best_model.joblib models/
COPY data/processed/02_datos_ajustados_cooperativa.parquet data/processed/

USER app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4)"]

CMD ["streamlit", "run", "app.py"]
