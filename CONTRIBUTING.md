# Guía de contribución y operación

Este documento describe cómo se trabaja en el repositorio: desde el primer
commit hasta que un cambio llega a producción.

## 🧰 Entorno local

```bash
make setup      # uv sync --locked + instala los hooks de git
make run        # app en http://localhost:8501
```

En macOS, LightGBM necesita OpenMP: `brew install libomp`. Si no quieres
instalarlo, `make docker-test` ejecuta las pruebas dentro de Linux.

Las dependencias se dividen en tres grupos de `pyproject.toml`:

| Grupo                 | Contenido                                        | Dónde se instala            |
|-----------------------|--------------------------------------------------|-----------------------------|
| runtime (`dependencies`) | Lo que la app necesita para servir los modelos | Local, CI, imagen Docker    |
| `dev`                 | ruff, pytest, pre-commit                         | Local y CI                  |
| `notebooks`           | pycaret, optuna, shap, jupyter…                  | Solo local                  |

`uv.lock` es la única fuente de verdad. Para añadir una dependencia:

```bash
uv add <paquete>                     # runtime
uv add --group dev <paquete>         # herramienta de desarrollo
uv add --group notebooks <paquete>   # solo para análisis
```

## 🌿 Flujo de trabajo (GitHub Flow)

1. Crea una rama corta desde `main`: `feat/…`, `fix/…`, `model/…`, `ci/…`, `docs/…`.
2. Haz commits pequeños siguiendo [Conventional Commits](https://www.conventionalcommits.org/es/):
   ```
   feat: agrega exportación de predicciones a CSV
   fix(predictor): corrige el rango del campo edad
   model: reentrena LightGBM con datos de 2026-Q3
   ```
   Tipos válidos: `feat`, `fix`, `model`, `refactor`, `perf`, `docs`, `test`, `ci`, `build`, `chore`, `style`, `revert`.
   El hook `commit-msg` rechaza mensajes que no cumplan el formato.
3. Abre un Pull Request y completa la plantilla.
4. CI debe quedar en verde y el PR necesita la aprobación de un code owner.
5. Merge con **squash** (el título del PR es el mensaje final, también en Conventional Commits) y borra la rama.

Nunca se hace push directo a `main`.

## ✅ Qué valida CI en cada PR

| Job                                   | Qué verifica                                                                                 |
|---------------------------------------|----------------------------------------------------------------------------------------------|
| Lint y formato                        | pre-commit: ruff (lint + formato), YAML/TOML, lockfile al día, esquema de workflows, claves privadas |
| Tests y quality gate de modelos       | pytest con cobertura ≥ 80 %: unitarias, contrato de los modelos, quality gate y smoke test de la app |
| Imagen Docker (build, smoke test y escaneo) | La imagen construye, el contenedor endurecido responde en `/_stcore/health`, Trivy sin CVE HIGH/CRITICAL con parche ni secretos, Dockerfile sin malas configuraciones |
| Revisión de dependencias              | Las dependencias nuevas del PR no traen vulnerabilidades altas                               |
| CodeQL                                | Análisis estático de seguridad del código Python y de los workflows                          |

Lo que corre en CI es lo mismo que `make lint` y `make test` en local.

## 🧪 Pruebas

```
tests/
├── test_metrics.py   # unitarias de utils/metrics.py
├── test_loaders.py   # carga y preprocesamiento de datos y modelos
├── test_models.py    # contrato + quality gate de los modelos serializados
└── test_app.py       # smoke tests de la app completa con streamlit.testing (AppTest)
```

`test_models.py` es el guardián del artefacto que se despliega:

- El modelo carga **sin** `InconsistentVersionWarning` (mismas versiones de scikit-learn con que se entrenó).
- Es un `Pipeline` completo, `predict_proba` devuelve probabilidades válidas y deterministas, y tolera categorías nuevas.
- **Quality gate** en el holdout del notebook 05 (`random_state=100`, 20 %): Recall ≥ 0.70 y ROC-AUC ≥ 0.93.

## 🤖 Reentrenar o cambiar modelos

`scikit-learn` y `lightgbm` están fijados a la versión exacta con que se
serializaron los modelos, y Dependabot los ignora a propósito: un modelo
`.joblib` solo es confiable con las mismas versiones con que se guardó.

1. Rama `model/<descripción>`.
2. Ejecuta los notebooks (`uv run jupyter lab notebooks/`) y guarda los modelos en `models/`.
3. Si actualizaste scikit-learn o lightgbm, cambia su versión en `pyproject.toml`, ejecuta `uv lock` y **reentrena** con las nuevas versiones.
4. Si cambia el split de validación, actualiza `HOLDOUT_SEED` / `HOLDOUT_SIZE` en `tests/test_models.py`.
5. `make test` debe pasar. Si el modelo nuevo no supera el quality gate, no se despliega. Solo sube los umbrales `MIN_RECALL` / `MIN_ROC_AUC` (nunca los bajes sin justificarlo en el PR).
6. Abre el PR con commit `model: …` y la tabla de métricas antes/después de la plantilla.

## 🚀 Releases y despliegue

Versionado [SemVer](https://semver.org/lang/es/): `MAJOR` cambios incompatibles
(p. ej. el modelo requiere columnas nuevas), `MINOR` funcionalidad o modelo
nuevo compatible, `PATCH` correcciones.

| Evento              | Resultado                                                                                   |
|---------------------|---------------------------------------------------------------------------------------------|
| Merge a `main`      | CI completo → imagen `ghcr.io/juancamilomb/credit-risk-classification:main` y `:sha-<commit>` (amd64 + arm64, SBOM y provenance) → escaneo publicado en *Security* |
| Tag `vX.Y.Z`        | Lo anterior + tags `:X.Y.Z`, `:X.Y`, `:latest` → GitHub Release con notas generadas → despliegue al environment `production` |

Para publicar una versión:

```bash
git switch main && git pull
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

El job de despliegue llama al webhook del secreto `DEPLOY_HOOK_URL` del
environment `production` con la imagen **por digest** (lo desplegado es
exactamente lo que se probó). Sirve para cualquier plataforma que acepte
deploy hooks (Render, Railway, Coolify, Portainer, etc.). Si el secreto no
existe, el job termina sin desplegar y deja la imagen lista en GHCR.

**Rollback:** vuelve a ejecutar el job *Desplegar a producción* del release
anterior desde la pestaña *Actions*, o apunta tu plataforma al tag/digest previo.

## ⚙️ Configuración única del repositorio en GitHub

Estos ajustes no viven en el código y hay que hacerlos una vez (Settings):

1. **Branches → Branch protection / Rulesets para `main`:**
   - Require a pull request before merging (1 aprobación, *Require review from Code Owners*, descartar aprobaciones viejas).
   - Require status checks to pass: `Lint y formato`, `Tests y quality gate de modelos`, `Imagen Docker (build, smoke test y escaneo)`, `Revisión de dependencias`, `Analizar (python)`, `Analizar (actions)`.
   - Require branches to be up to date, block force pushes y deletions.
2. **General → Pull Requests:** permitir solo *squash merge* y activar *Automatically delete head branches*.
3. **Environments → `production`:** *Required reviewers* (aprobación manual antes de desplegar), *Deployment branches and tags* limitado a tags `v*`, y el secreto `DEPLOY_HOOK_URL`.
4. **Code security:** activar *Dependabot alerts*, *Dependabot security updates*, *Secret scanning* y *Push protection*.
5. **Actions → General:** *Workflow permissions* en *Read repository contents* (cada workflow pide solo los permisos que necesita).
6. **Packages:** tras la primera publicación, revisar la visibilidad del paquete en GHCR (pública si se quiere `docker pull` sin login).

## 🔐 Datos y secretos

- Nunca subas credenciales: usa secretos de GitHub (CI/CD) y `.streamlit/secrets.toml` (ignorado por git) en local.
- `data/raw/*.csv` está ignorado: los datos crudos no deberían versionarse. Si contienen información personal de asociados, no deberían estar en un repositorio público.
