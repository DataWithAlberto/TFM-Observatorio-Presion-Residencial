# Estrategia de integración histórica y corte prospectivo de cinco capas

> Actualización issue #9: el panel candidato de 284 municipios descrito aquí
> se revisa a **277 municipios en 2020–2023** al exigir cuatro trimestres de
> precios también en los retardos. Véanse la [auditoría específica](AUDITORIA_IPR_HISTORICO.md)
> y la [metodología del histórico](METODOLOGIA_IPR_HISTORICO.md).

## Resultado de la auditoría

El universo de referencia son 306 municipios. La auditoría se basa en los CSV
procesados que alimentan los scores y en sus claves naturales; no presupone
cobertura a partir de la documentación. El 25 de julio de 2026 se contrastaron
los recuentos por año de los cuatro CSV con las tablas PostGIS reales. Las
cuatro comparaciones resultaron idénticas y quedaron registradas en
`data/processed/validaciones_integracion.csv`.

La intersección de los **scores ya publicados** es 2022–2023. En 2022 queda
limitada a 284 municipios por la cobertura de gentrificación. En 2023 las
cuatro capas tienen valores válidos y elegibles para 306/306 municipios. Por
tanto, **2023 es el último y único año común completo observado**, y el
candidato defendible para el corte transversal del índice compuesto. No existe
un índice compuesto completo y homogéneo para 2005–2026.

La capa especulativa exige una precisión adicional. Su fichero de indicadores
contiene inputs elegibles para 280 municipios en 2016, 284 en 2017–2021 y 306
en 2022–2023. El score publicado conserva únicamente los años 306/306
(2022–2023). Por eso, la ausencia de score en 2020–2021 no equivale a ausencia
total de datos: esos años podrían incorporarse a un panel fijo de 284
municipios, pero habría que recalcular los percentiles de **todas** las capas
sobre ese mismo universo.

## Tres conceptos de cobertura

- **Cobertura de filas:** existe al menos un registro en el archivo de score.
- **Cobertura de valor válido:** el score no es nulo y está dentro de 0–100.
- **Cobertura elegible:** el registro ya ha superado las reglas metodológicas
  propias de su capa y puede entrar en una integración. Los CSV de score
  contienen solo registros elegibles; el script no reconstruye ni imputa
  observaciones descartadas.

Turismo conserva fechas de observación y puede tener varios snapshots por
municipio-año. Para la matriz anual, disponibilidad significa al menos un
snapshot válido; el número de observaciones se conserva aparte. Esta reducción
no convierte los snapshots en una falsa serie anual homogénea. Para el corte
2023 se propone fijar **agosto de 2023**. Es el mismo mes disponible de forma
continua en agosto de 2020, 2021, 2022 y 2023, con 306/306 municipios en cada
fecha. No debe mezclarse febrero, agosto y medias anuales sin recalcular y
documentar la capa.

## Propuesta para el índice compuesto

El producto principal debe ser un índice transversal observado para **2023**.
Una unidad solo es elegible si dispone de las cuatro capas válidas en ese año.
Un nulo o una fila ausente se mantiene como ausencia y nunca se codifica como
cero. No se recomienda publicar una puntuación compuesta cuando falte una capa.

Antes de calcular el índice deberán fijarse, justificarse y someterse a
sensibilidad la orientación de cada capa, su normalización común y los pesos.
Esta auditoría no fija pesos ni calcula el índice definitivo.

Los resultados deben etiquetarse en tres familias incompatibles entre sí:

1. **Observado completo:** cuatro capas observadas y elegibles; actualmente,
   306 municipios en 2023.
2. **Histórico parcial observado:** una a tres capas observadas. Puede
   describirse por capa o usarse en análisis exploratorios, pero no presentarse
   como la misma medida que el índice completo.
3. **Proyectado:** cualquier estimación futura o retroproyección. Debe guardarse
   y visualizarse separada, con método, horizonte e incertidumbre explícitos.

## Alternativas evaluadas

**Índice histórico parcial.** Es aceptable únicamente como producto
exploratorio claramente rotulado. Su composición cambia con la disponibilidad,
por lo que no constituye una serie directamente comparable con 2023.

**Pesos renormalizados entre capas disponibles.** Se descartan para la serie
principal: dos municipios o años podrían obtener la misma cifra a partir de
constructos diferentes, y los pesos efectivos variarían en el tiempo. Podrían
usarse solo en una sensibilidad separada, mostrando qué capas entran en cada
observación.

**Panel estable con scores publicados.** Es utilizable en 2022–2023 para 284
municipios. Mantiene los scores existentes, pero es una ventana temporal muy
corta.

**Panel estable recalculado.** Los inputs permiten un panel de 284 municipios
en 2020–2023. Es la mejor extensión temporal compatible con la fuente VUT del
INE. Requiere volver a calcular los percentiles anuales de las cuatro capas
sobre esos mismos 284 municipios, incluido 2023, y fijar el snapshot turístico
de agosto. No basta con filtrar los scores existentes, porque fueron
normalizados sobre universos distintos. Debe publicarse como análisis de
robustez y no sustituye al resultado nacional 306/306 de 2023.

**Sustitución de turismo por alojamiento convencional.** Indicadores Urbanos
del INE permite un panel de 57 municipios con las cuatro capas entre 2018 y
2023. Se descarta como serie principal: mide plazas o pernoctaciones en
establecimientos turísticos, no stock de viviendas turísticas, y selecciona
municipios con mayor actividad y disponibilidad estadística. Puede conservarse
como sensibilidad externa con otro nombre.

Antes de 2020 no existe ningún municipio con las cuatro capas usando la fuente
turística elegida, porque la serie VUT comienza en agosto de 2020. Si se omite
turismo, la intersección de asequibilidad, especulación elegible y
gentrificación es de 280 municipios en 2018 y 283 en 2019; eso es un diagnóstico
de tres capas, no el índice completo.

## Regla mínima defendible

Para el índice completo: universo registrado, año observado, cuatro de cuatro
capas válidas, ninguna imputación débil y trazabilidad hasta el archivo y
periodo fuente. Para comparaciones temporales: misma composición, mismas reglas
de normalización y mismo universo; si alguna condición cambia, el resultado se
publica como análisis distinto, no como continuación de una única serie.

## Decisión recomendada

El producto principal será el corte transversal 2023 para 306 municipios,
usando agosto de 2023 en turismo. Como sensibilidad longitudinal puede
prepararse posteriormente el panel fijo 284/306 de 2020–2023, con
renormalización completa de las cuatro capas. No se recomienda sustituir VUT
por otra variable solo para ganar años ni presentar una serie anterior a 2020
como si midiera el mismo constructo.

La comprobación CSV–PostGIS compara recuentos, claves naturales y scores fila a
fila. La diferencia máxima observada en columnas `NUMERIC` es inferior a
0,00005 por redondeo de almacenamiento. PostGIS conserva tres columnas
obsoletas de gentrificación v1, todas nulas; se registra como aviso de esquema,
no como dato válido ni como fallo de la capa v2.

## Incorporación separada del riesgo futuro

La auditoría histórica anterior se mantiene con las cuatro capas actuales. El
riesgo futuro no se inserta en ese panel porque combina anomalías climáticas
2041–2060 y tendencias hasta 2023: es una dimensión prospectiva, no otra
observación anual de 2020–2023.

Se genera un corte separado:

- **IPR-4 observado 2023:** 306/306 municipios.
- **IPR-5 prospectivo 2023:** 303/306 municipios.

El corte fija turismo en `2023-08-01`, exige cuatro scores actuales válidos y
añade el riesgo futuro versión 2.0. Cádiz, San Fernando y Getxo conservan las
cuatro capas observadas, pero no son elegibles para IPR-5 por ausencia de las
tres anomalías climáticas. No se imputa ni renormaliza el peso por municipio.

La salida trazable es
`data/processed/cobertura_corte_ipr5_2023.csv` y su tabla PostGIS es
`cobertura_corte_ipr5_integracion`.
