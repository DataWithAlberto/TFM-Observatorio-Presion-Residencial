# Auditoría temporal del IPR — issue #9

## Decisión

Se selecciona **2020–2023 y un panel fijo de 277 municipios** para un producto
separado, **IPR-4 histórico relativo**. Conserva las cuatro capas observadas, su
orientación y los pesos del IPR-4 vigente. Se recalculan todas las distribuciones
y la regresión de hogares sobre ese panel. El corte nacional 306/306 de 2023 y
el IPR-5 prospectivo 303/306 conservan sus valores.

La selección se obtiene de los archivos disponibles, no de un intervalo
preestablecido. La auditoría es reproducible mediante
`python 20_ipr_historico.py --audit-only`. El resultado debe revisarse si cambian
las fuentes o su metodología: cobertura numérica no demuestra por sí sola
comparabilidad estadística.

## Evidencia y alcance

`data/processed/ipr_historical/coverage.csv` registra, para cada variable y año
entre 1996 y 2026, fuente, archivo, frecuencia, primer y último año con valor
finito, número de observaciones, municipios, porcentaje de cobertura, años
vacíos y notas metodológicas. Incluye las variables prospectivas para mostrar
por qué no son otra serie observada. Un cero de cobertura significa ausencia,
no presión cero. Una fila finita todavía puede no ser elegible.

`eligible_coverage.csv` aplica las reglas de elegibilidad y distingue el total
disponible en cada año de los municipios del panel seleccionado. Las dos
matrices no son intercambiables.

| Variable o grupo fuente | Primer–último año con valores en los archivos | Frecuencia | Limitación temporal |
|---|---|---|---|
| Valor tasado MIVAU | 2005–2026 | Trimestral | Años y municipios con trimestres no publicados; 2026 parcial |
| Renta neta por hogar, Atlas 30824 | 2015–2023 | Anual | Limita asequibilidad y desacoplamiento a 2023 |
| Renta por persona, Atlas 30824 | 2015–2023 | Anual | Ventana de tres años: componente desde 2018 |
| Hogares unipersonales y edades, Atlas 30832 | 2015–2023 | Anual | Ventanas trianuales y ajuste por edades |
| VUT y plazas, INE 39363 | 2020–2026 | Snapshots | Primer snapshot agosto 2020; fijar mes, sin interpolación |
| Población municipal, padrón INE | 1996–2025 | Anual | Ausencia de 1997; exigir año exacto del snapshot |
| Transacciones, MIVAU 34010210 | 2004–2026 | Trimestral | Solo sumas con cuatro trimestres; último año parcial |
| Parque residencial, Censo INE 59525 | 2021 | Censo fijo | Denominador constante; no es parque anual observado |
| Riesgo futuro y sus seis inputs efectivos | Base 2023 | Prospectiva | Clima 2041–2060 y tendencias previas; no observaciones anuales |

El área municipal procede de la geometría de referencia del proyecto: es una
constante geográfica, no una serie de superficies históricas. La titularidad
corporativa, migraciones, desigualdad y composición relativa de renta son
complementos/contrastes; no forman parte de la fórmula del IPR-4 y no restringen
su intersección temporal.

## Matriz de elegibilidad de las cuatro capas

Recuentos de municipios con los inputs requeridos y precios de cuatro
trimestres en todos los años empleados por cada indicador:

| Capa | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Asequibilidad | 276 | 275 | 281 | 281 | 281 | 302 | 306 | 306 | 306 | 0 |
| Turismo (agosto) | 0 | 0 | 0 | 0 | 0 | 306 | 306 | 306 | 306 | 306 |
| Especulación | 0 | 269 | 275 | 275 | 279 | 278 | 279 | 302 | 306 | 0 |
| Gentrificación | 0 | 0 | 0 | 275 | 275 | 279 | 281 | 281 | 302 | 0 |
| Panel histórico seleccionado | — | — | — | — | — | **277** | **277** | **277** | **277** | — |

Antes de 2020 falta VUT; después de 2023 falta renta y no pueden calcularse las
cuatro capas. Se enumeran los intervalos consecutivos de la intersección y se
escoge el más largo cuyo universo estable conserva al menos el 90% de los 306
municipios. Se mantiene el umbral de cobertura ya usado en gentrificación.
En empate se prioriza mayor universo, luego el periodo más reciente. Si no hay
al menos dos años consecutivos elegibles, el cálculo se detiene y conserva la
auditoría, sin generar un índice parcial.

Esta regla no elimina capas para ganar años. Un periodo 2018–2023 no es viable
con la definición completa. 2021–2023 o 2022–2023 permiten paneles más cortos;
no hacen falta para mantener las cuatro dimensiones en 2020–2023. No hay una
serie de varios años con cobertura 306/306 y las condiciones de esta auditoría.

## Universo y exclusiones

`historical_municipality_universe.csv` contiene los **306 códigos**, nombre,
inclusión, inicio/fin y motivos por capa, año, variable ausente y número de
trimestres. Se incluyen 277 (90,52%) y se excluyen 29 (9,48%). Nunca se filtran
los scores publicados para reutilizar sus percentiles nacionales.

La auditoría de integración anterior proponía 284 municipios a partir de
valores finitos. La revisión de los trimestres excluye además siete:

| Código | Municipio | Años con precio anual incompleto relevantes para el panel |
|---|---|---|
| 20030 | Eibar | 2017, 2018, 2019, 2020 |
| 20067 | Errenteria | 2017 |
| 48015 | Basauri | 2018 |
| 48027 | Durango | 2017, 2018, 2019, 2020 |
| 48036 | Galdakao | 2019 |
| 48054 | Leioa | 2020 |
| 48084 | Sestao | 2020 |

Los otros 22 son Campello, el (03050), Níjar (04066), Villanueva de la Serena
(06153), Pineda de Mar (08163), Sant Andreu de la Barca (08196), Santa Perpètua
de Mogoda (08260), Sitges (08270), Almassora (12009), Benicarló (12027), Onda
(12084), Ames (15002), Almuñécar (18017), Azuqueca de Henares (19046), Lepe
(21044), Navalcarnero (28096), La Oliva (35014), Cangas (36008), Candelaria
(38011), Lebrija (41053), Salou (43905), Illescas (45081) y Catarroja (46094).
Sus precios anteriores no permiten reconstruir todos los retardos de
especulación y gentrificación. El CSV registra el detalle individual.

Se usa el mismo código y la misma geometría del universo actual en todos los
años. No se retroproyectan fusiones ni se reasignan observaciones municipales.
El panel no representa todos los municipios españoles; describe la selección
del proyecto con cobertura estable.

## Cambios de fuente y comparabilidad

- **Turismo:** el INE sitúa el inicio de VUT en agosto de 2020. La serie del
  proyecto tiene 13 snapshots; agosto existe en 2020–2024, pero cambian los meses
  posteriores. Se usa exclusivamente agosto con población del mismo año.
  [Publicación inicial del INE](https://www.ine.es/prensa/experimental_viv_turistica.pdf).
- **Atlas:** el INE documenta un cambio del fichero poblacional hacia el censo
  anual y advierte de saltos demográficos en algunas secciones. También cambia
  en 2023 la referencia de los umbrales relativos de renta. Estos últimos no
  entran en el score principal. No se interpreta una variación demográfica
  municipal como transformación social demostrada. El informe estandarizado
  indica siete periodos comparables, pero no identifica por sí solo qué saltos
  municipales son de origen estadístico. Es una limitación de la interpretación,
  no una razón para imputar o corregir los datos.
  [Metodología ADRH, octubre 2025](https://www.ine.es/metodologia/metodologia_adrh.pdf),
  [apartado 15.2 del informe INE](https://www.ine.es/dynt3/metadatos/RespuestaDatos.html?oper=353).
- **Precios:** el parser distingue el formato XLS anterior a 2010. El panel
  utiliza 2017–2023 para los retardos; exige cobertura trimestral completa y
  mantiene la ponderación por tasaciones vigente. No extrapola precios ausentes.
- **Rotación:** se conserva el parque 2021 para todos los años. Su evolución
  recoge compraventas respecto a ese stock fijo, no cambios del parque anual.
- **Scores:** el universo de normalización y la regresión anual de hogares se
  recalculan. Los datos de origen no se sobrescriben. Riesgo futuro se excluye
  porque no puede constituir una quinta capa anual observada.

## Contraste de municipios

`python 21_validacion_ipr_historico.py` reproduce 12 casos de Madrid, Barcelona
y Gijón. Lee las hojas trimestrales originales de precios 2017–2023, VUT,
transacciones, Censo 2021 y el extracto demográfico del INE. Contrasta precios
ponderados, ratios, rotación, aceleración, brechas y diferencias demográficas
con los inputs del panel. Los parsers existentes escriben en un directorio
temporal, sin alterar fuentes ni resultados nacionales.

| Municipio | IPR 2020 | 2021 | 2022 | 2023 | Cambio 2023–2022 |
|---|---:|---:|---:|---:|---:|
| Madrid | 61,75 | 78,32 | 84,94 | 68,84 | −16,10 |
| Barcelona | 57,93 | 67,20 | 68,39 | 56,78 | −11,62 |
| Gijón | 61,46 | 51,75 | 63,46 | 61,03 | −2,43 |

Los valores fuente y las contribuciones revisados están en
`reference_checks.csv`. En Madrid, por ejemplo, el descenso de 2023 es un cambio
de posición relativa del compuesto; no demuestra una bajada absoluta de todos
los precios ni permite atribuir causalidad a una capa.

**Límite de esta comprobación:** el bruto `atlas_renta_30824.csv` está excluido
de Git y no está disponible en este checkout. La renta se ha contrastado entre
`renta_hogares.csv` y `variables_socioeconomicas_municipales.csv`, ambos derivados
del Atlas. El manifiesto registra `sha256: null` para el bruto ausente; no se
presenta ese contraste como una verificación independiente contra el bruto.
La reconstrucción desde el original se realiza con el paso 03 del pipeline.
