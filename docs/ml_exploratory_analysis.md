# Análisis exploratorio mediante Machine Learning

## Objetivo y decisión metodológica

**Índice publicado = fórmula interpretable.** El experimento responde únicamente a:
«¿Hasta qué punto un modelo no lineal puede aproximar la estructura del índice
compuesto utilizando sus componentes?». Se conserva la clasificación de P3.1:
**D — metodológicamente problemático para afirmar predicción**. Véase
[la auditoría original](ml_audit.md).

El experimento con XGBoost tiene carácter exploratorio. Dado que las variables
utilizadas como entrada participan en la construcción del índice objetivo, sus
resultados no constituyen evidencia de capacidad predictiva independiente ni
permiten realizar inferencias causales. Tampoco son una validación externa del
índice, de sus componentes o de sus pesos.

## Separación del resultado oficial

`17_indice_riesgo_futuro.py` calcula y, opcionalmente, persiste la fórmula 2.0
sin importar ni ejecutar XGBoost. Se conservan exactamente el cálculo, los
percentiles, los pesos y la elegibilidad. `18_indice_presion_residencial.py`, la
API, el bootstrap, los rankings y las páginas operativas no consumen el ML.

`25_analisis_ml_exploratorio.py` lee un snapshot del score y escribe artefactos
exploratorios. No tiene conexión a la base ni modifica el score. Se conserva el
nombre histórico `riesgo_futuro_comparacion_modelos.csv`, sus identificadores de
modelo y columnas principales. Su generación pasa al comando independiente.

La página `/analisis-ml`, titulada **Análisis exploratorio con Machine Learning**,
consume `apps/web/data/ml_exploratory.json`, versionado junto al código. La
importación estática incorpora el análisis al build: no se añade ningún endpoint
a la API productiva ni se entrena en peticiones web. Después de regenerar el
artefacto hay que reconstruir la aplicación para publicar el nuevo snapshot.

## Reproducción

Desde la raíz, con las versiones de numpy, pandas, scikit-learn y XGBoost de
`requirements.txt` instaladas:

```bash
python 17_indice_riesgo_futuro.py --no-db  # solo si se necesita regenerar el score
python 25_analisis_ml_exploratorio.py
python -m unittest discover -s tests -v
npm --prefix apps/web run lint
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

El análisis también puede ejecutarse sin tocar las salidas versionadas:

```bash
python 25_analisis_ml_exploratorio.py \
  --output /tmp/ml_exploratory.json --comparison /tmp/ml_comparison.csv
```

No se instalan SHAP ni librerías de gráficos Python adicionales: se usa TreeSHAP
exacto nativo de XGBoost y ECharts, ya presente en el dashboard. La API oficial de
[XGBoost](https://xgboost.readthedocs.io/en/release_3.2.0/python/python_api.html)
documenta `pred_contribs=True`: devuelve una contribución por feature y una
columna adicional con la base. `approx_contribs=False` evita la aproximación de
contribuciones. Con `reg:squarederror`, su suma reconstruye la salida en puntos
del índice. Las pruebas verifican esta identidad con tolerancia numérica.

## Flujo, conjunto elegible y modelos

1. Leer `data/processed/riesgo_futuro_residencial_score.csv` con códigos INE como
   texto y elegir exactamente sus filas con `elegible_score=True`.
2. Ordenar por código INE para estabilizar las particiones, incluso si cambia el
   orden físico del CSV. Se conservan 303 de los 306 municipios; Cádiz, San
   Fernando y Getxo siguen excluidos. El maestro INE solo aporta nombres.
3. Mantener el target `score_riesgo_futuro` y las mismas variables originales:
   tres anomalías climáticas y las tendencias de asequibilidad, turismo y
   gentrificación. La tendencia especulativa completamente nula se descarta,
   como ya hacía el experimento original. **Seis features efectivas**.
4. Usar `KFold(n_splits=5, shuffle=True, random_state=42)` con idénticas filas y
   particiones para ambos modelos. No hay búsqueda de hiperparámetros.
5. En cada fold ajustar la imputación por mediana **solo al entrenamiento**.
   `keep_empty_features=True` conserva la correspondencia de columnas incluso
   si una feature queda completamente vacía en un entrenamiento (en ese caso
   scikit-learn utiliza cero). Este caso no ocurre en el snapshot publicado.
   Se guardan valores originales y valores imputados, sin imputar el target.
6. Ajustar Dummy y XGBoost con el entrenamiento y obtener salidas de los
   municipios reservados. Calcular SHAP con ese mismo XGBoost y esas mismas
   entradas. No hay un ajuste final sobre todos los municipios ni mezcla de
   métricas de entrenamiento con salidas evaluadas.

| Referencia | Papel | MAE CV (puntos) |
|---|---|---:|
| A · Fórmula interpretable | Metodología oficial que define el target | No procede |
| B · DummyRegressor, media | Referencia mínima | 11,755791 |
| C · XGBRegressor | Aproximación exploratoria no lineal | 2,631587 |

El MAE es la media de los errores absolutos de los 303 municipios fuera de su
partición de entrenamiento (OOF). Es una media ponderada por el tamaño de cada
fold, no una media sin ponderar de cinco MAE. También se conservan los MAE y
los tamaños por fold para auditarla. No se añaden RMSE ni R²: el MAE proporciona
una medida directa en puntos del índice. No se asigna MAE cero a la fórmula
como si se hubiera validado: es la definición del target.

Se mantienen los hiperparámetros originales: 200 árboles, profundidad 3,
learning_rate=0.03, subsample=0.8, colsample_bytree=0.8,
objective=reg:squarederror, random_state=42 y n_jobs=1. No se modifica el target,
no se añaden fuentes y no se implementa forecasting.

## SHAP y visualizaciones

Todas las contribuciones son OOF y cubren el conjunto elegible completo.
Cada municipio se explica con el modelo que no lo incluyó en su entrenamiento.
La base SHAP es la salida esperada según las rutas de los árboles de ese modelo;
no debe confundirse con la salida de Dummy ni con el score oficial. Las bases
pueden cambiar entre folds.

- **Global:** contribución media absoluta por variable, agregando los cinco
  modelos sobre sus municipios reservados. No es la importancia de un único
  modelo final ni una validación de los pesos metodológicos.
- **Beeswarm:** todas las contribuciones, apiladas de forma determinista por
  intervalos horizontales. El desplazamiento vertical evita superposición; el
  color es el valor de entrada imputado normalizado al rango de cada variable.
- **Municipal:** selector de los 303 municipios, score metodológico, salida
  XGBoost OOF, diferencia firmada `XGBoost − fórmula`, error absoluto, base y
  todas las contribuciones, ordenadas por magnitud. Se señalan las entradas
  ausentes imputadas con medianas del entrenamiento.
- **Score vs aproximación:** dispersión OOF con ejes en la misma escala y
  diagonal de coincidencia.
- **Errores:** histograma del error absoluto con intervalos de dos puntos
  `[a, b)`, incluyendo el máximo. No es error de predicción futura.

**SHAP explica el comportamiento del modelo, no el fenómeno residencial.**
Se habla de contribuciones a la salida del XGBoost o importancia dentro de su
aproximación. No se atribuyen causas, efectos residenciales ni responsabilidad
por aumentos del índice. El dashboard incluye esta restricción junto a las
visualizaciones globales y municipales. El JSON completo se puede descargar
para examinar los valores sin depender de la lectura visual de los gráficos.

## Limitaciones del bloque de Machine Learning

1. El target deriva de los mismos componentes que las features: hay **target
   leakage estructural**. Una buena reconstrucción no valida el fenómeno.
2. La validación cruzada es transversal sobre un único corte temporal (2023).
   La winsorización y los percentiles del target ya se calcularon sobre el
   universo metodológico antes de los folds. La imputación interna no corrige
   esa dependencia; se mantiene la fórmula oficial sin alterarla.
3. No existe horizonte t+1. El escenario climático 2041–2060 no equivale a una
   etiqueta residencial futura observada.
4. No existe etiqueta externa independiente ni test temporal o geográfico.
   Municipios espacialmente relacionados pueden quedar en folds distintos.
5. Por tanto, no se afirma capacidad predictiva, anticipación de riesgo,
   generalización temporal, validación externa ni causalidad.

El valor académico del bloque reside en comparar una formulación interpretable
con su aproximación no lineal, examinar dónde difieren y explicar el
comportamiento de esta última. La metodología oficial conserva su primacía.

## Trazabilidad y P1

El JSON registra `generated_at` UTC, `pipeline_version` (variable de entorno
`PIPELINE_VERSION` o commit Git), `version_metodologia`, corte, universo y tamaño
elegible, features y exclusiones, semilla, configuración explícita y parámetros
resueltos del modelo, versiones de Python/librerías, folds, alcance SHAP y hashes
SHA-256 de los archivos de entrada y scripts. El valor `missing=NaN` de XGBoost
se registra como texto para conservar JSON estándar sin valores no finitos.

Los registros `files` usan `dataset`, `sha256`, `file_size` y `status`, compatibles
con el manifiesto P1. El hash del script distingue cambios sin commit. Esta rama
no contiene el paquete `reproducibilidad` ni el orquestador de P1; el análisis no
introduce una dependencia de esos módulos. Al integrar ambas ramas, P1 puede
inventariar el CSV experimental en `data/processed` y el JSON por su ruta propia.
No se sobrescribe su manifiesto ni se cambia la metodología para integrarlos.

La fecha de generación es el único campo necesariamente variable entre
repeticiones idénticas. Los resultados OOF y SHAP son deterministas con las
versiones registradas; las pruebas contrastan el artefacto versionado con una
regeneración y con el `cross_val_predict` original.

## Auditoría de nomenclatura

Se revisaron los archivos de texto del repositorio y los párrafos y tablas de
los dos DOCX. Las apariciones se clasifican en:

| Ubicación | Clasificación | Acción |
|---|---|---|
| `METODOLOGIA_RIESGO_FUTURO.md`, «Comparación predictiva» | Afirmación incorrecta del alcance ML | Cambiar a «Comparación exploratoria mediante Machine Learning» |
| Script 17, descripción de la comparación | Descripción técnica que deja de corresponder al flujo | Describir únicamente cálculo oficial; trasladar experimento al script 20 |
| Documentación, calidad, ficha, prospectiva y prototipo Mediterranean | Negaciones explícitas de predicción o explicación del escenario | Conservar: son restricciones correctas |
| Script 18, `predictores` en el cálculo VIF | Regresores de diagnóstico de colinealidad | Conservar: no afirma predicción residencial |
| Memoria DOCX, «Predicción del precio futuro de la vivienda» | Celda de la columna «No incluye» | Conservar: es exclusión de alcance |
| Memoria DOCX, MAE y comparación exploratoria | Narrativa ya prudente, sin detalle de SHAP y limitaciones P3.2 | Ampliar mediante la sección de memoria asociada a P3.2 |
| Documento `Observatorio de presión residencial.docx` | Sin coincidencias ML/predicción | Sin cambios |
| Auditoría `ml_audit.md` | Evidencia histórica, diagnósticos y propuestas fuera de alcance | Conservar y añadir enlace al estado P3.2 |
| `cross_val_predict`, `predict`, `pred_contribs`, `DummyRegressor` y nombres históricos | Identificadores de API/compatibilidad | Conservar |
| «Riesgo Futuro», «proyección» y horizonte climático | Denominación metodológica del escenario, no ML | Conservar |

Las nuevas menciones a predicción/forecasting documentan limitaciones o exclusión
de alcance. No se aplica una sustitución ciega a palabras técnicamente correctas.
