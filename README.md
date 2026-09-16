# Observatorio de Presión Residencial

**Trabajo Fin de Máster** · Máster en Data Science, Big Data & Business Analytics
(Universidad Complutense de Madrid) · Alberto Llaneza Tabares

Sistema reproducible para medir la presión residencial en 306 municipios
españoles. Integra fuentes públicas en PostGIS, calcula un índice compuesto
interpretable (IPR) y lo publica en una aplicación web con API propia.

Repositorio: <https://github.com/DataWithAlberto/TFM-Observatorio-Presion-Residencial>

La memoria del trabajo está en
[`memoria/`](memoria/Memoria_Observatorio_Presion_Residencial_Alberto_Llaneza_Tabares.docx).

## Productos del índice

El corte integrado vigente es 2023:

- **IPR-4 observado:** 306 municipios y cuatro dimensiones observadas
  (asequibilidad, presión turística, presión especulativa y riesgo de
  gentrificación).
- **IPR-5 prospectivo:** 303 municipios; añade riesgo climático y tendencias.
  Cádiz, San Fernando y Getxo no se imputan porque no tienen cobertura climática
  suficiente. El contraste entre ambos no es una evolución temporal.
- **IPR-4 histórico relativo 2020–2023:** panel fijo de 277 municipios, con su
  propio universo. La [auditoría temporal](docs/metodologia/AUDITORIA_IPR_HISTORICO.md)
  documenta las 29 exclusiones y la
  [metodología](docs/metodologia/METODOLOGIA_IPR_HISTORICO.md) explica cómo
  interpretar los cambios.

## Estructura del repositorio

```text
.
├── 00_…py – 25_…py        Pipeline científico: descarga, indicadores e índices
├── pipeline.py            Ejecuta el pipeline completo con registro auditable
├── utils_http.py          Descargas HTTP con reintento
├── analytics/             Lógica del histórico homogéneo y la normalización
├── spatial_ipr/           Análisis espacial (Moran global y LISA)
├── reproducibilidad/      Manifiesto de datos, traza de descargas y geometría
├── sql/                   Esquema analítico de PostGIS
├── database/              Carga inicial (bootstrap) y vistas que consume la API
├── apps/
│   ├── api/               API FastAPI y sus pruebas
│   └── web/               Aplicación Next.js y pruebas Playwright
├── config/                Programación del pipeline y protocolo de validación externa
├── data/
│   ├── raw/               Fuentes originales descargadas
│   ├── processed/         Resultados del pipeline (los carga la aplicación)
│   └── data_manifest.json Tamaño, SHA-256 y procedencia de cada fichero
├── docs/                  Documentación técnica y resultados
│   └── metodologia/       Metodología, auditoría y ejecución de cada dimensión
├── memoria/               Memoria del TFM
├── output/analisis_espacial/  Figuras e informe del análisis espacial
├── tests/                 Pruebas de Python del pipeline y los análisis
├── docker-compose.yml     Base de datos, carga, API y web
└── requirements*.txt      Dependencias de Python
```

Dos ficheros brutos superan el límite de tamaño de GitHub y no se incluyen:
`data/raw/ine_renta/atlas_renta_30824.csv` y
`data/raw/ine_turismo/poblacion_municipal_33943.csv`. Los descargan
`03_renta_ine.py` y `05_turismo_ingesta.py` al reconstruir desde las fuentes; no
hacen falta para levantar la aplicación.

## Puesta en marcha con Docker

Requisitos: Git y Docker Desktop con Docker Compose. No hace falta tener
PostgreSQL, Python ni Node instalados.

```bash
git clone https://github.com/DataWithAlberto/TFM-Observatorio-Presion-Residencial.git
cd TFM-Observatorio-Presion-Residencial
cp .env.example .env
docker compose up --build --wait
```

La primera ejecución crea un volumen propio, carga los resultados procesados
de `data/processed` y publica:

- aplicación: http://localhost:3000
- documentación de la API: http://localhost:8000/api/docs
- comprobación de disponibilidad: http://localhost:8000/ready

La carga comprueba su huella digital: en arranques posteriores solo se repite si
cambian los datos o los esquemas.

```bash
docker compose down            # detiene los servicios y conserva la base
docker compose down -v         # elimina el volumen del proyecto
docker compose up --build --wait
```

Los valores de `.env.example` son solo para desarrollo local. Antes de exponer
los servicios en otra red debe cambiarse `POSTGRES_PASSWORD`.

La aplicación ofrece estas vistas: observatorio (mapa), ranking, ficha municipal,
comparación, prospectiva, calidad del dato, análisis espacial, validación
externa, análisis exploratorio con ML y metodología.

## Variables de entorno

Docker Compose lee automáticamente el archivo `.env` de la raíz:

| Variable | Valor de ejemplo | Uso |
| --- | --- | --- |
| `POSTGRES_DB` | `tfm_presion_residencial` | Nombre de la base de datos. |
| `POSTGRES_USER` | `postgres` | Usuario de PostgreSQL. |
| `POSTGRES_PASSWORD` | `tfm_pass` | Contraseña local de PostgreSQL. |
| `POSTGRES_PORT` | `5433` | Puerto de PostgreSQL en el anfitrión. |
| `API_PORT` | `8000` | Puerto público de la API. |
| `WEB_PORT` | `3000` | Puerto público de la aplicación. |
| `CORS_ORIGINS` | `http://localhost:3000` | Orígenes permitidos por la API, separados por comas. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL de la API visible desde el navegador; se incorpora al compilar la web. |
| `FORCE_BOOTSTRAP` | `0` | Con `1`, vuelve a cargar los datos procesados. |

Si cambia `API_PORT`, actualice también `NEXT_PUBLIC_API_URL`. Si cambia
`WEB_PORT`, actualice `CORS_ORIGINS`. Las credenciales o el puerto de PostgreSQL
que se cambien en `.env` deben reflejarse también en `DATABASE_URL` al ejecutar
los scripts Python fuera de Docker.

Los scripts científicos leen `DATABASE_URL` del entorno y aceptan además
`--db-url`. `PROJ_NETWORK=OFF` evita descargas implícitas de recursos de
proyección. Las pruebas web aceptan `PLAYWRIGHT_BASE_URL` para comprobar una
instancia ya iniciada en vez de levantar servidores locales.

## Reconstrucción científica desde las fuentes

El arranque con Docker reproduce la **aplicación a partir de resultados
validados**. Para regenerar esos resultados desde las fuentes se necesita además
Python 3.11:

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export PROJ_NETWORK=OFF
export DATABASE_URL=postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial
docker compose up -d --wait db
python pipeline.py
```

`pipeline.py` ejecuta los scripts en este orden:

| Etapa | Scripts |
| --- | --- |
| Universo municipal y precios | `01_municipios.py`, `02_precios_vivienda.py`, `00_carga_postgis_base.py` |
| Asequibilidad | `03_renta_ine.py`, `04_indice_asequibilidad.py` |
| Presión turística | `05_turismo_ingesta.py`, `06_turismo_indicadores.py`, `07_indice_presion_turistica.py` |
| Presión especulativa | `08_fuentes_especulacion.py`, `09_indicadores_especulativos.py`, `10_indice_presion_especulativa.py` |
| Riesgo de gentrificación | `11_fuentes_gentrificacion.py`, `12_indicadores_gentrificacion.py`, `13_indice_riesgo_gentrificacion.py` |
| Integración | `14_auditoria_integracion.py --check-db --load-db` |
| Riesgo futuro | `15_fuentes_riesgo_futuro.py`, `16_indicadores_riesgo_futuro.py`, `17_indice_riesgo_futuro.py` |
| Índice y validación | `18_indice_presion_residencial.py`, `19_validacion_indice_presion_residencial.py --strict` |
| Histórico | `20_ipr_historico.py`, `21_validacion_ipr_historico.py` |
| Calidad del dato | `22_data_quality_score.py` |
| Análisis espacial | `23_analisis_espacial_ipr.py` |
| Validación externa | `24_validacion_externa_ipr.py` |
| ML exploratorio | `25_analisis_ml_exploratorio.py` |

```bash
python pipeline.py --dry-run                 # muestra las etapas sin ejecutarlas
python pipeline.py --from-stage calculo_ipr  # reanuda desde una etapa
```

Tras regenerar los CSV procesados, se sincroniza la base y se recrean las vistas:

```bash
docker compose run --rm -e FORCE_BOOTSTRAP=1 bootstrap
docker compose up -d api web
```

## Reproducibilidad y trazabilidad de las fuentes

Cada ejecución de `pipeline.py` genera un `run_id` único. Cada etapa deja dos
registros estructurados (inicio y resultado) en `data/runs/<run_id>.jsonl`, con
duración, intento, salida y error cuando corresponda. Las descargas son las
únicas etapas con reintento automático, porque son las susceptibles de fallos
transitorios.

Cada descarga deja al lado un `<fichero>.metadata.json` con la dirección
exacta, el instante en UTC, la huella de lo recibido y el aviso legal del
organismo. La fecha de modificación del archivo no vale para esto: se pierde al
copiar o al clonar, y entonces todas las fuentes parecen bajadas el mismo día.
Para registrar las once fuentes basta con volver a ejecutar las etapas de
descarga:

```bash
python 01_municipios.py --force-download
python 02_precios_vivienda.py --force-download
python 03_renta_ine.py --force-download
python 05_turismo_ingesta.py --force-download
python 08_fuentes_especulacion.py --force-download
python 11_fuentes_gentrificacion.py --force-download
python 15_fuentes_riesgo_futuro.py --force-download
python 24_validacion_externa_ipr.py --refresh
```

La geometría municipal es la excepción: llegó al repositorio ya hecha y ningún
script la descarga. Conserva el campo `CODNUT2`, propio de los recintos
municipales INSPIRE del Instituto Geográfico Nacional, pero eso es una pista y
no una atribución. Para cerrarla, descargue la capa del Centro de Descargas del
CNIG y compruébelo:

```bash
python -m reproducibilidad.verificar_geometria ruta/a/la/capa.shp \
  --url "https://centrodedescargas.cnig.es/..." \
  --recurso "Líneas límite municipales"
```

Compara los 306 municipios uno a uno y solo anota la procedencia si los límites
coinciden. Si no, lo dice y no escribe nada.

Al finalizar se actualiza [`data/data_manifest.json`](data/data_manifest.json),
que recoge esa traza y añade tamaño y SHA-256 de cada fichero de `data/raw` y
`data/processed`, la fecha del commit que lo incorporó al repositorio, como cota
superior comprobable, y la versión Git del pipeline. `download_date` queda vacío
mientras la fuente no se haya vuelto a descargar con el registro activo: sin
traza no hay fecha que afirmar. La programación orientativa para cron está en
[`config/pipeline.json`](config/pipeline.json); no se añade un orquestador
externo porque el runner y cron cubren la periodicidad requerida con menor
complejidad operativa.

## Pruebas

```bash
source venv/bin/activate
docker compose up -d --wait db
python -m pytest -q
```

Las pruebas de `tests/` cubren el pipeline y los análisis; las de
`apps/api/tests` comprueban los contratos de la API y necesitan la base de datos
levantada con los datos cargados.

Las comprobaciones web necesitan Node.js 22 y la aplicación iniciada con Docker
Compose:

```bash
npm --prefix apps/web ci
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
npm --prefix apps/web exec -- playwright install chromium
PLAYWRIGHT_BASE_URL=http://localhost:3000 npm --prefix apps/web run test:e2e
```

## Resultados y análisis complementarios

**Calidad del dato.** Cada municipio y año del IPR-4 lleva un Data Quality Score
con su desglose y motivos. Evalúa cobertura y actualidad; la consistencia queda
como no evaluable por falta de evidencia municipal. No altera el índice.
[Metodología y auditoría del DQS](docs/DATA_QUALITY_SCORE.md).

**Patrones espaciales.** Sobre el corte 2023 hay 306 geometrías válidas y 220
municipios evaluables por contigüidad Queen; los 86 sin vecinos se conservan como
no evaluables. Moran I = 0,535 (p bilateral = 0,002). Ninguna asociación local
supera la corrección FDR al 5 %; sin corrección aparecen 27.
[Metodología](docs/METODOLOGIA_ESPACIAL_IPR.md) ·
[informe y figuras](output/analisis_espacial/informe.md).

**Validación externa.** El IPR-4 2023 se contrasta con la mediana del alquiler de
vivienda colectiva (MIVAU, SERPAVI), que no interviene en su construcción:
Spearman ρ = 0,54 en 295 municipios (p por permutación < 0,001). Es un contraste
convergente limitado al coste del alquiler, no una certificación del índice.
[Candidatos e hipótesis](docs/CANDIDATOS_VALIDACION_EXTERNA.md) ·
[auditoría](docs/AUDITORIA_IPR_VALIDACION_EXTERNA.md) ·
[resultados](docs/RESULTADOS_VALIDACION_EXTERNA.md).

**Machine Learning exploratorio.** Compara la fórmula oficial con un modelo Dummy
y XGBoost, con errores fuera de muestra y contribuciones SHAP. El modelo
reconstruye el índice con sus propios componentes: no demuestra capacidad
predictiva independiente ni causalidad, y el índice publicado se calcula solo con
las fórmulas interpretables.
[Análisis](docs/ml_exploratory_analysis.md) · [auditoría previa](docs/ml_audit.md).

## Documentación

| Documento | Contenido |
| --- | --- |
| [Preguntas de investigación](docs/PREGUNTAS_INVESTIGACION.md) | Preguntas RQ1–RQ3 y marco interpretativo |
| [Arquitectura](docs/ARQUITECTURA_PLATAFORMA.md) | Base de datos, API y aplicación web |
| [Contraste prospectivo](docs/CONTRASTE_PROSPECTIVO.md) | Diferencia entre IPR-4 e IPR-5 |
| [Limitaciones](docs/LIMITACIONES_PLATAFORMA.md) | Limitaciones conocidas de la plataforma |
| [Sistema de diseño](apps/web/design.md) | Especificación de la interfaz |
| [`docs/metodologia/`](docs/metodologia) | Metodología, auditoría y ejecución de cada dimensión |
