# Capa de Riesgo Futuro Residencial

## Definición

La capa estima la exposición relativa a factores estructurales que pueden
incrementar la presión residencial. No es una predicción aislada del precio ni
una probabilidad causal de desplazamiento.

El corte base es 2023 y el horizonte climático es 2041–2060 bajo SSP2-4.5. Se
emplea una ventana de veinte años porque las proyecciones climáticas no deben
interpretarse como pronósticos de un año concreto.

## Componentes principales

AdapteCCa (AEMET/OECC) proporciona anomalías proyectadas CMIP6 municipales
(`valueType=ANOMALY`). No son niveles climáticos absolutos. Para cada
municipio y año se conserva la mediana del ensemble, sus percentiles 25 y 75 y
el número de modelos. La señal climática usa:

- duración máxima de las olas de calor;
- grados-día de refrigeración;
- máxima racha seca.

Cada indicador se resume mediante la media 2041–2060. El servicio separa
Península/Baleares/Ceuta/Melilla y Canarias; el pipeline consulta ambos grupos.
La cobertura efectiva es 303/306 (99,02%). Cádiz, San Fernando y Getxo existen
en el catálogo municipal, pero no devuelven series para las variables elegidas.
Se mantienen como ausencias y quedan fuera del score, nunca se codifican como
cero.

Las tendencias de presión se estiman con la mediana de todas las pendientes
entre pares de años (Theil–Sen simplificado), exigiendo al menos tres años y
sin usar información posterior a 2023:

- presión de acceso, calculada como `100 - puntuación de asequibilidad`,
  entre 2015 y 2023;
- presión turística, usando exclusivamente los snapshots de agosto de
  2020–2023;
- riesgo de gentrificación, hasta 2023.

La presión especulativa se conserva como columna trazable, pero su tendencia y
percentil permanecen nulos: el score publicado solo abarca 2022–2023. La lista
de tendencias activas queda fijada en la versión 2.0 para impedir que una
variable se incorpore automáticamente sin una nueva decisión metodológica.
Prophet también se descarta porque las series comunes son demasiado cortas y
discontinuas para aportar una proyección defendible.

## Normalización y agregación

Los indicadores se winsorizan en P1–P99 y se transforman a percentiles,
preservando siempre los nulos. El
score se calcula únicamente cuando están presentes los tres indicadores
climáticos y al menos dos tendencias:

`RFR = 0,60 × riesgo climático + 0,40 × tendencia de presión`

Los pesos iguales dentro de cada bloque evitan una precisión ficticia. El
resultado se limita naturalmente a 0–100 y conserva todos los indicadores,
percentiles, reglas de elegibilidad, escenario y versión metodológica.

En 284 municipios se observan las tres tendencias activas. En 22 solo se
observan asequibilidad y turismo por falta de una serie suficiente de
gentrificación. Esta diferencia de composición se conserva explícitamente en
`n_tendencias_validas` y debe acompañar la interpretación del score.

## Variables complementarias descartadas del score

El SNCZI aporta cartografía oficial de inundación fluvial y costera, pero su
ausencia territorial no significa ausencia de riesgo. La propia publicación
T=100 informa de cobertura parcial de cauces estudiados. Se conserva como
fuente complementaria hasta poder medir cobertura municipal efectiva.

Los certificados energéticos dependen de registros autonómicos. No se ha
identificado un registro nacional municipal armonizado y reproducible; por
tanto, la eficiencia energética no entra en el score principal.

## Comparación exploratoria mediante Machine Learning

Se contrasta el índice interpretable con XGBoost mediante validación cruzada de
cinco particiones. La imputación se ajusta dentro de cada partición y la línea
base usa `DummyRegressor`. El modelo reduce el error respecto a una constante, pero su
objetivo es el propio índice construido, no una verdad externa observada.
Reproducir una fórmula conocida no valida capacidad predictiva. XGBoost se
conserva exclusivamente como análisis exploratorio, separado del score final.
La fórmula interpretable es el único resultado oficial.

SHAP explica el comportamiento de la aproximación XGBoost, no el fenómeno
residencial ni sus causas. La comparación reproducible, sus visualizaciones y
las limitaciones de target leakage se documentan en
[Análisis exploratorio mediante ML](../ml_exploratory_analysis.md).

Deep Learning se descarta por el tamaño de muestra, la ausencia de una etiqueta
externa y la pérdida de interpretabilidad.

## Limitaciones

- 303 municipios elegibles, no 306.
- El bloque climático mide cambio proyectado, no daños económicos.
- Racha seca es una señal de peligrosidad, no un modelo completo de incendio.
- Inundación y eficiencia energética permanecen fuera del núcleo.
- Las tendencias de las capas no constituyen una serie común 2005–2026.
- El índice ordena riesgo relativo dentro del universo analizado; no establece
  umbrales absolutos de habitabilidad ni causalidad.
- Las variables climáticas representan anomalías proyectadas respecto al
  periodo de referencia de AdapteCCa, no valores futuros absolutos.
