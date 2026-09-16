# Trabajo 3 — ejecución

Desde la raíz del repositorio, con el entorno virtual activo y la base iniciada:

```bash
export PROJ_NETWORK=OFF
docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/08_especulacion.sql
python 08_fuentes_especulacion.py
python 09_indicadores_especulativos.py
python 10_indice_presion_especulativa.py
```

La conexión por defecto es
`postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial`.
Puede sustituirse con `DATABASE_URL`.

Opciones útiles:

```bash
python 08_fuentes_especulacion.py --skip-download --no-db
python 08_fuentes_especulacion.py --force-download
python 09_indicadores_especulativos.py --no-db
python 10_indice_presion_especulativa.py --no-db
```

Salidas:

- `data/processed/transacciones_vivienda_municipal.csv`
- `data/processed/parque_viviendas_2021.csv`
- `data/processed/titularidad_corporativa_catastro.csv`
- `data/processed/indicadores_especulativos.csv`
- `data/processed/presion_especulativa_score.csv`
- `data/processed/especulacion_correlaciones.csv`
- `data/processed/especulacion_sensibilidad.csv`

Validaciones automáticas:

- 306 municipios en transacciones y parque;
- 289 municipios por año en titularidad estatal y exclusión foral explícita;
- claves únicas municipio-periodo;
- cuatro trimestres para los indicadores anuales;
- porcentajes y score dentro de 0–100;
- score principal únicamente en años con cobertura 306/306;
- casos de referencia: Madrid, Barcelona, València, Málaga y Gijón.
- correlaciones internas y sensibilidad del ranking a pesos alternativos.
