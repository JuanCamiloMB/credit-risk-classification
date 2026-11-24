## ¿Qué cambia y por qué?

<!-- Resumen breve del cambio y la motivación. Enlaza el issue si existe: Closes #... -->

## Tipo de cambio

- [ ] `feat` — nueva funcionalidad
- [ ] `fix` — corrección de un error
- [ ] `model` — reentrenamiento o cambio de modelos en `models/`
- [ ] `refactor` / `perf` / `docs` / `test` / `ci` / `build` / `chore`

## Checklist

- [ ] `make lint` y `make test` pasan en local
- [ ] Añadí o actualicé pruebas para el cambio
- [ ] Si cambian dependencias: actualicé `uv.lock` (`uv lock`)
- [ ] Si cambian los modelos: reporto las métricas en el holdout y el quality gate de `tests/test_models.py` pasa
- [ ] Actualicé la documentación (README / CONTRIBUTING) si aplica

## Métricas del modelo (solo si cambian los modelos)

| Modelo | Recall (antes → después) | ROC-AUC (antes → después) |
|--------|--------------------------|---------------------------|
|        |                          |                           |
