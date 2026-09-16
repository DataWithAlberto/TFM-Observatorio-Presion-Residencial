# Auditoría histórica e integración prospectiva

El script `14_auditoria_integracion.py` audita el panel histórico de las capas
1–4 y el corte prospectivo de cinco capas; no calcula el índice compuesto.

## Ejecución reproducible

Desde la raíz del repositorio:

```bash
source venv/bin/activate
python 14_auditoria_integracion.py
```

Genera:

- `data/processed/cobertura_temporal_capas.csv`
- `data/processed/cobertura_municipio_anio.csv`
- `data/processed/cobertura_escenarios_panel.csv`
- `data/processed/panel_estable_2020_2023.csv`
- `data/processed/validaciones_integracion.csv`
- `data/processed/cobertura_corte_ipr5_2023.csv`

La primera salida diferencia filas, valores válidos y elegibilidad. La segunda
contiene una fila por cada uno de los 306 municipios y año observado en el
rango conjunto, banderas por capa, número de observaciones y total de capas. La
tercera diferencia el score publicado de los inputs que permitirían recalcular
un panel parcial. La cuarta identifica los 284 municipios del panel estable
2020–2023.

## PostGIS en Docker (puerto 5433)

Primero inicie Docker Desktop y el servicio de base de datos del proyecto:

```bash
docker compose up -d --wait db
```

Verifique la conexión:

```bash
docker compose exec db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT PostGIS_Full_Version();"'
```

Compare los recuentos reales de las cuatro tablas con los CSV:

```bash
source venv/bin/activate
python 14_auditoria_integracion.py --check-db
```

La comparación incluye claves y scores fila a fila, además de los recuentos.
Un estado `AVISO` no detiene la ejecución; actualmente documenta tres columnas
legacy de gentrificación v1 presentes y totalmente nulas en PostGIS.

Solo después de una comparación correcta, cree y cargue las tablas de
metadatos:

```bash
docker compose exec -T db sh -c \
  'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < sql/14_cobertura_integracion.sql
source venv/bin/activate
python 14_auditoria_integracion.py --check-db --load-db
```

Puede sustituirse la conexión mediante `DATABASE_URL` o `--db-url`. Si
PostGIS no está activo, `--check-db` falla de forma explícita; el script no
presenta los CSV como si la base hubiese sido comprobada.

La auditoría conserva el panel histórico de cuatro capas y valida por separado
el corte IPR-5 prospectivo. La carga crea también
`cobertura_corte_ipr5_integracion`.
