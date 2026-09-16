# Trabajo 5 — Riesgo Futuro Residencial

## Ejecución

Desde la raíz del repositorio, con el entorno virtual activo:

```bash
export PROJ_NETWORK=OFF
python 15_fuentes_riesgo_futuro.py
python 16_indicadores_riesgo_futuro.py
python 17_indice_riesgo_futuro.py --no-db
# Experimento independiente, opcional para el índice oficial:
python 25_analisis_ml_exploratorio.py
```

La primera descarga tarda varios minutos. Para auditar de nuevo los ficheros
ya descargados:

```bash
python 15_fuentes_riesgo_futuro.py --reuse
```

## PostGIS

Inicie Docker Desktop y el servicio de base de datos del proyecto:

```bash
docker compose up -d --wait db
docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/15_riesgo_futuro.sql
python 17_indice_riesgo_futuro.py
```

Puede sustituir la conexión con `DATABASE_URL` o `--db-url`.

## Salidas

- `data/raw/riesgo_futuro/adaptecca_mapeo_municipios.csv`
- `data/raw/riesgo_futuro/adaptecca_proyecciones_municipales.csv`
- `data/processed/auditoria_fuentes_riesgo_futuro.csv`
- `data/processed/indicadores_riesgo_futuro.csv`
- `data/processed/riesgo_futuro_residencial_score.csv`
- `data/processed/riesgo_futuro_comparacion_modelos.csv` (solo script 20)
- `apps/web/data/ml_exploratory.json` (solo script 20; métricas OOF, SHAP y trazabilidad)

## Validaciones

Los scripts detienen la ejecución ante:

- universo distinto de 306 municipios;
- duplicados de código INE o identificador AdapteCCa;
- cobertura climática inferior al 95%;
- menos del 90% de municipios elegibles;
- puntuaciones fuera de 0–100.
- cualquier tendencia que utilice información posterior a 2023;
- snapshots turísticos distintos de agosto de 2020–2023;
- conversión de una tendencia ausente en un percentil neutral.

Los valores ausentes nunca se sustituyen por cero. La descarga conserva
escenario, ensemble e incertidumbre. Cádiz, San Fernando y Getxo quedan
registrados sin score climático porque el servicio no devuelve datos para las
variables seleccionadas.

La versión metodológica vigente es la **2.0**. Incluye pruebas de regresión:

```bash
python -m unittest tests/test_riesgo_futuro.py -v
```

El script 17 calcula exclusivamente la fórmula oficial. El script 20 no
interviene en el score ni en su persistencia. Véase el
[análisis exploratorio](../ml_exploratory_analysis.md), que no constituye
validación predictiva independiente ni evidencia causal.
