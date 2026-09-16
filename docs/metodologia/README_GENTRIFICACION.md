# Trabajo 4 — ejecución

Desde la raíz del repositorio, con el entorno virtual activo y la base iniciada:

```bash
export PROJ_NETWORK=OFF
docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/11_gentrificacion.sql
python 11_fuentes_gentrificacion.py
python 12_indicadores_gentrificacion.py
python 13_indice_riesgo_gentrificacion.py
```

La conexión por defecto es
`postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial`.
Puede sustituirse con `DATABASE_URL`.

Para validar sin escribir en PostgreSQL:

```bash
python 11_fuentes_gentrificacion.py --skip-download --no-db
python 12_indicadores_gentrificacion.py --no-db
python 13_indice_riesgo_gentrificacion.py --no-db
```

Salidas:

- `data/processed/variables_socioeconomicas_municipales.csv`
- `data/processed/saldos_migratorios_municipales.csv`
- `data/processed/indicadores_gentrificacion.csv`
- `data/processed/riesgo_gentrificacion_score.csv`
- `data/processed/gentrificacion_correlaciones.csv`
- `data/processed/gentrificacion_sensibilidad.csv`
- `data/processed/gentrificacion_validacion_externa.csv`

Validaciones automáticas:

- cobertura 306/306 en las fuentes socioeconómicas y demográficas;
- score anual 2018–2023 con cobertura observada mínima del 90 %;
- claves únicas municipio-año;
- ausencia de valores no finitos en componentes;
- score dentro de 0–100;
- redundancia Spearman inferior a 0,90;
- sensibilidad de pesos y contraste PCA;
- contraste con composición de renta y migración;
- grandes ciudades, capitales turísticas, municipios industriales e interiores.

La primera ejecución descarga el catálogo territorial de la API del INE y
guarda únicamente el mapeo de los 306 municipios. Las tablas de distribución,
desigualdad y demografía se consultan en lotes selectivos; no se descargan los
gigabytes correspondientes a distritos y secciones censales.
