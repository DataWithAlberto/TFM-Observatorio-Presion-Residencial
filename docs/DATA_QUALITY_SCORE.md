# Data Quality Score del IPR-4 — versión dqs-ipr4-1.0

El Data Quality Score no mide presión residencial. Evalúa la calidad, cobertura
y actualidad de los datos utilizados para estimar el IPR de cada municipio.

El alcance de esta versión es el **IPR-4 observado**. La calidad de la proyección
climática no se infiere de su año base: el horizonte 2041–2060 es un escenario,
no un periodo observado reciente. Por eso no se publica un DQS del IPR-5. En
su ficha se identifica expresamente el DQS como correspondiente al IPR-4.
El DQS no modifica el índice, sus contribuciones, percentiles ni rankings.
**DQS ≠ intervalo de confianza; DQS ≠ probabilidad de que el IPR sea correcto.**
No se calcula `IPR × DQS` ni intervalos artificiales.

## Auditoría previa de la evidencia disponible

Se revisaron los CSV procesados, los scripts 03–14 y 18–19, las metodologías de
las cuatro capas y las vistas de calidad existentes. El único corte integrado
validado de esta rama es 2023; el histórico de capas no equivale a un histórico
homogéneo del IPR. El universo se verifica contra el GeoPackage de 306 municipios.
La auditoría reproducible se exporta en `data/processed/dqs_auditoria.csv`.

| Componente / fuentes efectivamente utilizadas | Cobertura 2023 | Periodo estadístico | Serie de score | Missing del score / duplicados en clave | Actualización de fuente |
| --- | ---: | --- | --- | --- | --- |
| Asequibilidad: valor tasado MIVAU y renta INE | 306/306 (100 %) | Precio y renta 2023; 4 trimestres en los 306 | 2015–2023 | 0 / 0 | No trazable por observación |
| Turismo: INE VUT, población INE y geometría municipal | 306/306 (100 %) | Agosto 2023; población 2023 en los 306 | Agosto 2020–mayo 2026, snapshots | 0 / 0 | No trazable por observación |
| Especulación: transacciones, precio, renta y parque INE | 306/306 (100 %) | Flujos 2023; 4 trimestres de precio y transacciones; **parque 2021** | 2022–2023 | 0 / 0 | No trazable por observación |
| Gentrificación: Atlas INE, precio y estructura de hogares | 306/306 (100 %) | Ventana de cambios **2020–2023** | 2018–2023 | 0 / 0 | No trazable por observación |
| Riesgo futuro (fuera del DQS observado) | 303/306 (99,02 %) | Base 2023, anomalías 2041–2060 | Un corte prospectivo | 3 scores ausentes / 0 | No comparable con actualidad observada |

Las coberturas históricas están en `cobertura_temporal_capas.csv` y
`cobertura_municipio_anio.csv`; por ejemplo gentrificación tiene 280 municipios
en 2018, 284 en 2022 y 306 en 2023. La auditoría turística del DQS selecciona el
mes guardado en el IPR, no el último snapshot del archivo ni todas las fechas
del año. La fecha de cálculo del DQS no se utiliza como fecha de actualización.

| Componente | Granularidad, transformaciones y controles existentes | Imputación / limitaciones |
| --- | --- | --- |
| Asequibilidad | Municipio/año; precio ponderado por tasaciones, vivienda de 90 m², ratio con renta, percentil invertido. Ingesta valida códigos y nivel municipal, claves únicas y valores positivos. | Sin imputación de observaciones; media simple cuando faltan pesos de tasación. No hay bitácora municipal del uso de ese fallback. |
| Turismo | Municipio/snapshot; VUT por población y superficie, media de dos percentiles. Uniones por código y fecha, validación de denominadores y claves. Se conserva `anio_poblacion` y `poblacion_desfasada`. | Sin imputación del score; el pipeline puede utilizar población anterior y deja evidencia del desfase. El área es una característica espacial, sin «caducidad anual». |
| Especulación | Municipio/año; rotación, aceleración y desacoplamiento precio-renta; media de tres percentiles. Controles de elegibilidad, claves y cobertura. Se conserva `anio_referencia` del parque. | Parque censal fijo 2021, no estimación anual. Catastro cubre 289 municipios en 2024/2025 y es complementario: **no se penaliza su ausencia porque no entra en el IPR**. |
| Gentrificación | Municipio/año; logcambios trianuales, residualización de hogares, winsorización p01–p99 y percentiles. Controles de elegibilidad, rango, claves y cobertura anual ≥90 %. | Sin imputar fuentes suprimidas. Los ceros imputados a pesos de tasación no son observaciones de precio imputadas. No hay registro municipal de todas las transformaciones fallidas o descartes. |

`validaciones_integracion.csv` y `ipr_validaciones.csv` registran pruebas globales
con estado OK/AVISO/ERROR. No contienen un denominador de controles aplicables y
fallidos por municipio, fuente y año, ni un historial de descartes. **No es
posible convertirlos en una puntuación municipal de Consistency defendible.**
Se conserva `consistency_score = null` (y `consistency = null` en API), se explica
«No evaluable» en pantalla y se retira su peso. Un OK global no se convierte en
100 para cada municipio. Los errores estructurales detectados bloquean la carga;
los motivos observables quedan en `issues`, sin inventar un subscore.

## Definición y fórmula

Unidad: `(cod_ine, anio, calculation_version)`. Se utiliza la misma evidencia
seleccionada para el IPR, cotejando cada `score_origen_*` con su fuente para
rechazar resultados desincronizados. El valor numérico del IPR no entra en DQS.

**Coverage**, escala 0–100:

`C = 100 × número de componentes utilizables / 4`.

Utilizable significa score presente, finito y entre 0 y 100, con clave inequívoca.
Se usan pesos iguales entre capas: todas son necesarias para el IPR-4 y un peso
mayor en el fenómeno no demuestra mayor importancia de su calidad. Se evalúa la
disponibilidad de las capas finales, no la proporción de cada dato bruto que ha
sobrevivido al pipeline. Los 4 trimestres disponibles se auditan, pero no se
presenta la cobertura final como exhaustividad de microdatos.

**Recency**, escala 0–100:

`lag_j = año_IPR − año_estadístico_j`

`R_j = max(0, 100 − 10 × max(0, lag_j − 1))`.

Un año de desfase no penaliza, respetando los ciclos anuales de publicación.
Desde el segundo año se restan 10 puntos por año; el suelo es cero. Es una regla
explícita de diagnóstico, no una estimación del error estadístico. No se compara
con el año del reloj del ordenador: el DQS 2023 evalúa la medición de 2023.

- Asequibilidad: año de precio/renta de la fila anual.
- Turismo: el menor entre el año del snapshot y `anio_poblacion`.
- Especulación: `anio_referencia` del parque, el soporte temporal más antiguo de
  los niveles empleados; no se etiqueta todo como 2023 por el año del score.
- Gentrificación: final de la ventana trianual. El inicio de la ventana es parte
  de la definición del cambio, no evidencia desactualizada. El mismo criterio
  evita penalizar los lags necesarios para medir aceleraciones de precio.

`R` es la media simple de `R_j` de las capas utilizables. Una capa ausente reduce
Coverage; no se considera falsamente una fuente antigua ni actual. Su Recency
es null y su calidad de componente es 0. Si no hay ninguna capa utilizable, o
una capa disponible carece de periodo trazable, el DQS agregado es **null**. No
se rellenan periodos desconocidos ni se calculan scores con evidencia insuficiente.
Una fecha posterior al año del IPR o un año fuera de 1900–2100 es un error.

**DQS = 0,625 C + 0,375 R**.

Se redistribuyen proporcionalmente los pesos orientativos 0,50 y 0,30 al retirar
Consistency: 0,50/0,80 y 0,30/0,80. Se mantiene más importancia para la existencia
de información que para su desfase, sin estimar ni optimizar pesos con el IPR.
La calidad de cada componente disponible usa esos mismos pesos con C_j = 100.
El DQS global se calcula desde sus dimensiones; no es necesariamente la media de
las calidades de componente si hay capas ausentes, porque R es condicional a la
disponibilidad. Ningún score se redondea antes de clasificarlo.

Categorías: **alta ≥85; media ≥70 y <85; baja ≥50 y <70; muy baja <50**.
Se conservan los umbrales propuestos porque no hay evidencia que justifique
ajustarlos. No son cuantiles ni buscan distribuir artificialmente municipios.
La interfaz redondea a un decimal y mantiene la categoría del valor completo.
En baja/muy baja muestra cautela contextual y conserva el IPR visible.

## Resultado observado y sensibilidad

Los 306 municipios tienen C=100 y R=97,5: asequibilidad, turismo y gentrificación
obtienen R_j=100; especulación R_j=90 por el denominador censal 2021.
El DQS principal es **99,0625 (alta)** en todos ellos. Esto refleja la limitada
resolución de las métricas disponibles, no una garantía universal de exactitud.
No se crea variación artificial para que el mapa resulte más interesante.

| Configuración C/R | DQS en los 306 | Diferencia respecto a principal | Cambios de categoría | Cambio máximo de rango |
| --- | ---: | ---: | ---: | ---: |
| Principal 62,5/37,5 | 99,0625 | 0 | 0 | 0 |
| Iguales 50/50 | 98,75 | −0,3125 | 0 | 0 |
| Alternativa 75/25 | 99,375 | +0,3125 | 0 | 0 |

La correlación Spearman es **no definida** en los tres escenarios porque todos
los rankings están empatados; no se informa falsamente de una correlación 1.
`dqs_sensibilidad.json` conserva la correlación, cambios de score/rango y códigos
que cambian de categoría. La estabilidad del corte real no valida empíricamente
los pesos para futuras distribuciones; debe repetirse al cambiar las fuentes.
Los tests también incluyen una muestra heterogénea para verificar que el análisis
detecta cambios reales de categoría y calcula correlaciones cuando son definibles.

Casos controlados revisados (fixtures, no incidencias reales atribuidas a municipios):

| Caso | C | R | DQS | Resultado |
| --- | ---: | ---: | ---: | --- |
| Cuatro componentes actuales | 100 | 100 | 100 | Alta |
| Cuatro componentes de 2010 frente a 2023 | 100 | 0 | 62,5 | Baja; explica desfase |
| Una capa ausente, otras tres actuales | 75 | 100 | 84,375 | Media; identifica la ausencia |
| Una capa con valor imposible 101 | 75 | 100 | 84,375 | Media; identifica valor inválido, Consistency null |
| Todas ausentes | 0 | null | null | Información insuficiente |
| Capa disponible con periodo desconocido | 100 | null | null | No se inventa actualidad |

## Pipeline, persistencia y contratos

Después de ejecutar la validación 19 y antes de publicar los resultados:

```bash
python 22_data_quality_score.py --no-db
# O, para persistir en la base configurada por DATABASE_URL:
python 22_data_quality_score.py
```

El comando descubre los CSV `indice_presion_residencial_*.csv` realmente presentes
y calcula cada municipio/año. No extrapola el único corte 2023. Para publicar
futuros cortes también deberá ampliarse el catálogo de seeds del bootstrap,
actualmente limitado al IPR 2023. El módulo de cálculo y el esquema ya admiten
más de un año sin mezclar sus claves ni sus análisis de sensibilidad.

Salidas: `dqs_municipal.json`, `dqs_componentes.csv`, `dqs_auditoria.csv` y
`dqs_sensibilidad.json`. `calculated_at` es UTC y cambia en cada recálculo;
las puntuaciones son deterministas para la misma evidencia y versión.

El bootstrap calcula DQS con el mismo módulo, antes de publicar las vistas. Su
huella incluye los CSV de evidencia, informes de validación, módulo y esquema;
no confía en un JSON de DQS que pudiera haber quedado desactualizado. Las cargas
se detienen si los informes tienen errores o estados desconocidos, hay claves
repetidas, municipios ajenos, años inválidos o discordancias entre fuentes e IPR.

`sql/20_data_quality.sql` crea `data_quality_municipal` con FK a municipios, clave
única municipio/año/versión, restricciones de escala y de categoría y fecha de
cálculo. Los sub-scores y puntuación global son columnas; los cuatro componentes,
periodos y motivos se conservan en JSONB `details`. Esto evita crear otra tabla
que replique los indicadores de cobertura ya existentes. La escritura utiliza
UPSERT transaccional; repetirla no duplica claves ni elimina otras versiones/años.
La vista selecciona explícitamente `dqs-ipr4-1.0`, nunca una «última versión» ambigua.

Se amplían los contratos JSON existentes, sin nuevos endpoints:

- `/municipios/{cod_ine}`, `/indice`, `/ranking`, `/comparacion` y `/calidad`:
  `data_quality` con score, level, coverage, recency, consistency, scope,
  componentes, motivos, versión y fecha. Se conserva el contrato previo del IPR.
- `/calidad/resumen`: media DQS y recuentos de categorías.
- `/mapa/valores?capa=calidad` y `/indice?capa=calidad`: selección de DQS en una
  escala independiente. No se inventa un percentil DQS en el contrato del índice.

La ficha municipal permite abrir el desglose y explica las limitaciones. El mapa
usa otra paleta, etiquetas de calidad y umbrales propios; nunca multiplica o
combina la escala de presión con la de calidad. La página de fuentes muestra la
metodología breve y enlaza con esta capa.

## Límites y revisión futura

El DQS actual no mide exactitud frente a fuentes externas, sesgo de selección,
representatividad dentro del municipio, calidad de geometrías, tamaños muestrales
ni incertidumbre de la residualización. La fuente puede estar sesgada aunque su
score final exista y su periodo sea reciente. No se finge una evaluación de todos
los errores del pipeline. Para incorporar Consistency será necesario registrar
controles aplicables, resultados, descartes y transformaciones por municipio,
componente y año. Ese cambio requiere nueva versión metodológica y sensibilidad.

## Verificación de la entrega

Verificado con un proyecto Docker Compose aislado (`tfm-issue12`):

- 46 pruebas Python: cálculo, extremos, temporalidad, API, restricciones SQL,
  UPSERT sin duplicados y conservación exacta de las filas IPR.
- 15 pruebas Playwright: recorridos existentes, desglose DQS, selección del mapa,
  persistencia de la selección al recargar, ranking de calidad y advertencia de
  calidad baja sin ocultar el IPR; comprobación móvil sin desbordamiento.
- Lint, comprobación TypeScript y compilación de producción correctos.
- Las 14 comprobaciones de `19_validacion_indice_presion_residencial.py --strict`
  pasan sin errores ni avisos. Los CSV originales del IPR permanecen sin cambios.
- Inspección visual de la ficha y del mapa con su escala de calidad independiente.

La selección y los filtros del observatorio actualizan la URL con History,
sin esperar una navegación al servidor; los datos se siguen consultando mediante
React Query. La selección por teclado y la restauración al recargar se prueban
junto con los filtros originales.
