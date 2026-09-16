# Índice de Presión Residencial (IPR)

## Alcance

El resultado principal es un corte transversal de 2023. Se usa agosto de 2023
para turismo, el único snapshot mensual común y completo fijado por la
auditoría de integración. No se presenta una falsa serie homogénea 2005–2026.

## Orientación y normalización

Turismo, especulación, gentrificación y riesgo futuro crecen con la presión.
La capa de asequibilidad tiene orientación contraria: 100 significa mayor
asequibilidad. Solo en la integración se transforma como
`presión de acceso = 100 - asequibilidad`; la tabla original no se altera.

Los cinco scores orientados se vuelven a expresar como percentiles nacionales
0–100 en el corte 2023. Esta decisión:

- iguala la escala y evita que una capa gane influencia por tener mayor
  dispersión;
- es robusta ante extremos y distribuciones no normales;
- conserva el orden relativo, que es la información común realmente
  comparable entre capas.

Min–Max no es la opción base por su dependencia de extremos. El z-score robusto
es útil para diagnóstico, pero produciría valores sin límites naturales y una
interpretación menos directa. El IPR es relativo al universo de 306 municipios,
no un umbral absoluto de presión.

## Pesos

La especificación base es:

| Capa | Peso |
|---|---:|
| Presión de acceso/asequibilidad | 30 % |
| Presión turística | 20 % |
| Presión especulativa | 20 % |
| Riesgo de gentrificación | 15 % |
| Riesgo futuro | 15 % |

La asequibilidad recibe el mayor peso por medir el resultado residencial más
directo. Turismo y especulación representan mecanismos actuales. Las dos capas
de riesgo reciben un peso menor porque usan proxies más indirectos; además,
riesgo futuro contiene tendencias de capas previas y un peso alto aumentaría el
doble conteo. Los pesos no se presentan como estimaciones causales. Se
contrastan con pesos iguales, énfasis alternativos y exclusión del riesgo
futuro.

Para cada municipio:

`IPR-5 = 0,30 A + 0,20 T + 0,20 E + 0,15 G + 0,15 F`

La tabla final conserva score de origen, score orientado, percentil, peso y
contribución de cada capa.

## Cobertura y dos productos no equivalentes

El riesgo futuro tiene 303/306 observaciones válidas. Cádiz, San Fernando y
Getxo no devuelven series climáticas para las variables elegidas. No se
convierten en cero, no se imputan y no se renormalizan pesos por municipio.

- **IPR-5 prospectivo:** producto científico ampliado, cinco capas y 303
  municipios comparables. Combina presión actual con anomalías climáticas y
  tendencias; no es una quinta observación de 2023.
- **IPR-4 nacional observado:** producto complementario de cobertura, cuatro
  capas actuales y 306 municipios. Usa la misma composición para todos y no se
  presenta como equivalente al IPR-5 prospectivo.

Para los tres municipios sin IPR-5 prospectivo se publican cotas: contribución observada de
las cuatro capas más una contribución futura posible entre 0 y 15 puntos.

## Categorías

Las categorías muy baja, baja, media, alta y muy alta se asignan por quintiles
del ranking nacional del producto correspondiente. Son categorías relativas,
no límites sustantivos de habitabilidad o emergencia residencial.

## Redundancia y sensibilidad

Se calculan correlaciones Pearson y Spearman, VIF y PCA. PCA se usa solo como
contraste: no sustituye la estructura interpretable. VIF superior a 5 se
considera una señal de redundancia relevante.

La sensibilidad informa correlación de Spearman con el escenario base, cambio
medio y máximo de rango y solapamiento del decil superior. Los resultados
deben difundirse junto a las contribuciones, especialmente en municipios
próximos a límites de categoría.

## Limitaciones

- El IPR mide posición relativa en 2023, no causalidad.
- La unidad municipal oculta desigualdad entre barrios.
- Las capas tienen distinta profundidad temporal y distintas fuentes.
- Riesgo futuro combina clima y tendencias; por eso se limita su peso.
- No existe IPR-5 prospectivo nacional 306/306 sin introducir una imputación
  no observada.
