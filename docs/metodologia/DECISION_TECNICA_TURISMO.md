# Decisión técnica — capa de presión turística

## Decisión

La capa nacional utiliza la estadística experimental homogénea del INE
**Viviendas turísticas en España**, tabla 39363. Cubre los 306 municipios en
las 13 observaciones disponibles entre agosto de 2020 y mayo de 2026.

Los registros autonómicos de VUT e Inside Airbnb quedan fuera del score
nacional. Se incorporarán posteriormente como módulo complementario de
validación y análisis espacial, sin sustituir ni corregir el valor nacional.

## Auditoría de fuentes

- Tabla INE 39363: 306/306 municipios en cada fecha.
- Encuesta de Ocupación Hotelera por puntos turísticos, tabla INE 75198:
  94/306 municipios (30,7 %). Se excluye del score porque la ausencia de un
  municipio no significa presión cero.
- Plazas y establecimientos de otras encuestas de ocupación: publicadas por
  puntos o zonas turísticas, no para los 306 municipios.
- Población: tablas provinciales 2854–2909 del Padrón municipal del INE,
  serie anual disponible hasta 2025.
- Superficie: geometría municipal CNIG ya incorporada al proyecto; área
  calculada en EPSG:3035.

## Variables

Score principal:

1. Viviendas turísticas por 1.000 habitantes.
2. Viviendas turísticas por km².

Ambas variables se transforman en percentiles dentro de cada fecha. Después de
comprobar cobertura, distribución y correlación de Spearman, se aplica una
media 50/50. El script se detiene si la correlación alcanza 0,90, evitando
publicar un score que duplique esencialmente la misma señal.

La ejecución validada obtuvo una correlación máxima de 0,732 entre ambas
dimensiones. Por ello se aceptó la ponderación 50/50. Las plazas por habitante
se excluyeron del score tras observar una correlación de Pearson de 0,989 con
las VUT por habitante.

Indicadores conservados pero no ponderados:

- plazas por 1.000 habitantes;
- plazas por vivienda turística;
- estacionalidad de la oferta VUT dentro del año.

## Variables descartadas

- Establecimientos turísticos por km²: cobertura municipal insuficiente.
- Pernoctaciones por habitante: cobertura limitada a puntos turísticos.
- Intensidad respecto al parque residencial: no existe todavía en el proyecto
  una serie municipal homogénea y temporalmente alineada con 2020–2026.
- Estacionalidad dentro del score: algunos años tienen una sola observación y
  cambiaría la composición del índice entre fechas.

## Limitaciones

La tabla 39363 estima oferta publicada en plataformas, no viviendas ocupadas ni
licencias autonómicas. Para 2026 se usa el último padrón disponible (2025), y
el campo `poblacion_desfasada` identifica cualquier denominador con más de un
año de desfase.

El score mide presión turístico-residencial relativa entre los 306 municipios.
No mide el turismo total ni demuestra causalidad sobre precios.

Palma constituye un caso de advertencia: la tabla del INE registra 538 VUT en
mayo de 2026 y produce un score de 52,30, muy inferior a la expectativa
turística general. No se corrige manualmente. Se contrastará posteriormente con
el registro autonómico balear dentro del módulo VUT complementario.

## Módulo VUT complementario

Los registros autonómicos e Inside Airbnb tendrán una tabla separada con:
`cod_ine`, `fecha`, `fuente`, `tipo_fuente`, `vut`, `plazas`,
`cobertura_geografica` y `calidad`. Solo se calculará un subíndice cuando la
fuente cubra íntegramente el municipio y tenga fecha verificable. Este
subíndice se mostrará junto al score nacional, pero nunca lo reemplazará ni se
usará para rellenar municipios sin registro.
