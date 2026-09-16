# Trabajo 6 — Índice de Presión Residencial

## Ejecución

Desde la raíz del proyecto:

```bash
source venv/bin/activate
python 18_indice_presion_residencial.py --no-db
python 19_validacion_indice_presion_residencial.py
```

Para crear y cargar las tablas de PostGIS:

```bash
docker compose up -d --wait db
source venv/bin/activate
python 18_indice_presion_residencial.py
python 19_validacion_indice_presion_residencial.py
```

La conexión puede sustituirse mediante `DATABASE_URL` o `--db-url`.

## Salidas

- `data/processed/indice_presion_residencial_2023.csv`
- `data/processed/ranking_ipr5_prospectivo_2023.csv`
- `data/processed/ipr_resumen_estadistico.csv`
- `data/processed/ipr_correlaciones.csv`
- `data/processed/ipr_vif.csv`
- `data/processed/ipr_pca_contraste.csv`
- `data/processed/ipr_sensibilidad_pesos.csv`
- `data/processed/ipr_validaciones.csv`
- `data/processed/ipr_municipios_referencia.csv`

El proceso es idempotente en PostGIS para el año 2023. Las cinco tablas de
origen se leen, pero nunca se modifican.

El fichero contiene dos productos distintos: IPR-4 observado para 306
municipios e IPR-5 prospectivo para 303. No deben presentarse como una única
serie.

## Histórico homogéneo

El producto separado **IPR-4 histórico relativo** cubre 2020–2023 con un universo
fijo de 277 municipios, seleccionado mediante auditoría de los inputs y de sus
trimestres. Conserva los resultados nacionales anteriores.

```bash
python 20_ipr_historico.py --audit-only
python 20_ipr_historico.py --no-db
python 21_validacion_ipr_historico.py
```

Para persistirlo, configurar `DATABASE_URL` y omitir `--no-db`. El arranque de
Docker también carga los resultados históricos incluidos en el repositorio.
La ficha municipal muestra el histórico y permite seleccionar año, componentes
y cambios destacados. Véanse la [auditoría](AUDITORIA_IPR_HISTORICO.md) y la
[metodología histórica](METODOLOGIA_IPR_HISTORICO.md).
# Validación externa independiente

Después de generar el IPR, ejecutar `python 24_validacion_externa_ipr.py`.
Usa el CSV oficial archivado (SHA-256 verificado); `--refresh` descarga una
nueva versión y registra su procedencia. No requiere base de datos ni modifica
la construcción del índice. Dependencias en `requirements.txt`.

- [Auditoría de construcción](../AUDITORIA_IPR_VALIDACION_EXTERNA.md).
- [Candidatos e hipótesis previa](../CANDIDATOS_VALIDACION_EXTERNA.md).
- [Resultados, figuras y limitaciones](../RESULTADOS_VALIDACION_EXTERNA.md).
- Datos separados en `data/processed/validacion_externa/` y trazabilidad en
  `data/processed/validacion_externa/manifest.json`. El registro se añade en esta rama, que todavía no
  contiene el sistema P1 completo.
- Dashboard: `/validacion-externa`, accesible desde metodología y navegación.
  Su instantánea se genera con el paso 20; reconstruir la web tras actualizarla.
