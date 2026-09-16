# Auditoría previa de construcción del IPR

Issue #10. Auditoría del código realizada el 11 de septiembre de 2026, antes de
seleccionar el indicador y calcular asociaciones externas. Referencia:
`18_indice_presion_residencial.py`, metodología 2.0, corte 2023.

| Variable original | Fuente | Forma parte del IPR | Componente y uso |
|---|---|---|---|
| Valor tasado trimestral €/m² y número de tasaciones | Ministerio de Vivienda | Sí | Asequibilidad, especulación y gentrificación; media anual ponderada por tasaciones (simple si no hay pesos) |
| Renta neta media anual por hogar | INE Atlas 30824 | Sí | Asequibilidad y crecimiento de renta en especulación |
| Renta neta media por persona | INE Atlas 30824 | Sí | Cambio socioeconómico y presión residencial de gentrificación |
| Viviendas turísticas | INE 39363 | Sí | Turismo, snapshot agosto de 2023 |
| Población municipal | INE padrón | Sí | Denominador VUT/1.000 habitantes y comprobaciones de cobertura |
| Superficie municipal | Geometría municipal, área en EPSG:3035 | Sí | Denominador VUT/km² |
| Compraventas trimestrales | MIVAU, transacciones municipales tabla 2 | Sí | Suma de cuatro trimestres para rotación |
| Parque de viviendas 2021 | INE Censo 59525 | Sí | Denominador de rotación |
| % hogares unipersonales | INE Atlas 30832 | Sí | Cambio trianual y residuo de transformación de hogares |
| % menores de 18 y % mayores de 65 | INE Atlas 30832 | Sí, indirectamente | Controles de la regresión que residualiza hogares |
| Anomalías de duración de olas de calor, grados-día de refrigeración y racha seca | AdapteCCa, AEMET/OECC, CMIP6 | Sí, solo IPR-5 | Mediana del ensemble y media 2041–2060, SSP2-4.5 |
| Históricos de asequibilidad, turismo y gentrificación | Capas anteriores | Sí, indirectamente en IPR-5 | Mediana de pendientes entre pares de años, al menos tres observaciones hasta 2023 |
| Titularidad societaria | Catastro | No | Complementaria, no seleccionada por el score especulativo |
| Saldos migratorios | INE EMCR 69767 | No en fórmula; ya usados como contraste | Se unen en el paso 12, pero no están en `VARIABLES` del paso 13 ni determinan elegibilidad |
| Distribución de renta, Gini, P80/P20 | INE Atlas 30829/37677 | No en fórmula; ya usados como contraste | Comparten información de renta; no constituyen prueba nueva independiente |
| Precio del alquiler observado y su evolución | Fuente externa por investigar | No | Candidatos: el código no ingiere ni utiliza alquileres para construir capas |

## Transformaciones y pesos efectivos

1. **Asequibilidad** (pasos 02–04): precio anual × 90 m² / renta del hogar;
   percentil invertido anual. El paso 18 invierte el score de nuevo para
   expresar presión. Los 90 m² son un supuesto fijo, no un dato observado.
2. **Turismo** (05–07): media de los percentiles anuales de VUT/1.000 hab.
   y VUT/km², pesos 1/2. Plazas y estacionalidad no entran en el score.
3. **Especulación** (08–10): media de percentiles de compraventas/parque × 100,
   diferencia de crecimientos anuales del precio y crecimiento del precio
   menos crecimiento de renta del hogar; pesos 1/3.
4. **Gentrificación** (11–13): cambios logarítmicos trianuales de renta por
   persona, precio menos renta por persona y residuo del cambio en hogares
   unipersonales frente a cambios en menores/mayores. Winsorización P1–P99,
   percentiles anuales y pesos 1/3. Los saldos migratorios no intervienen.
5. **Riesgo futuro** (15–17): 60% clima, 40% tendencias, pesos iguales dentro
   de bloques, winsorización P1–P99 y percentiles. Exige tres señales climáticas
   y dos tendencias como mínimo. La tendencia especulativa permanece inactiva.

El paso 18 transforma cada score orientado a percentiles 0–100 con rango
medio: `100 × (rango - 1) / (N - 1)`. IPR-5: pesos 0,30 / 0,20 / 0,20 /
0,15 / 0,15; solo 303/306 municipios elegibles. IPR-4 observado nacional:
pesos fijos 0,30/0,85; 0,20/0,85; 0,20/0,85; 0,15/0,85; cobertura 306/306.
No existe una serie histórica de IPR compuesto en esta rama, solo 2023.

## Dependencias y límites de independencia

Precio y renta aparecen en varias capas. Riesgo futuro reutiliza sus
tendencias. Por ello, contrastar con esfuerzo de compra, crecimiento del
precio tasado, renta o tasas que los reutilicen sería circular. La evolución
de población/hogares también se solapa con insumos ya utilizados.

Una medición independiente del mercado del alquiler puede ser conceptualmente
próxima sin ser una transformación matemática del valor tasado de compraventa.
Debe documentarse su propia población y fuente; no se dividirá por la renta
del Atlas para crear un esfuerzo de alquiler. La independencia exigida es de
construcción, no independencia estadística entre fenómenos relacionados.

No se modificarán pesos, componentes, elegibilidad ni normalizaciones del IPR.
Los diagnósticos actuales del paso 19 son controles internos y no equivalen a
validación externa. No se ha encontrado `data_manifest` ni módulo P1 en esta
rama: la nueva ingesta deberá crear un registro explícito, sin atribuir a
descargas antiguas una fecha de descarga inventada.
