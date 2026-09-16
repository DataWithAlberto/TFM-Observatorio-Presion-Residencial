# Auditoría metodológica del Machine Learning existente

## Alcance y conclusión ejecutiva

Esta auditoría inspecciona el código, los CSV procesados, las vistas de API, la documentación y la memoria del proyecto. No modifica el modelo ni el comportamiento productivo.

El único modelo de aprendizaje automático existente es un `XGBRegressor` incluido en `17_indice_riesgo_futuro.py` como comparación del índice de Riesgo Futuro Residencial. Es una regresión transversal sobre 303 municipios en el corte base 2023. No predice un valor observado posterior, no realiza forecasting y no existe un endpoint de predicción.

El target es `score_riesgo_futuro`, calculado por la propia metodología a partir de tres anomalías climáticas proyectadas y tres tendencias de presión. Por tanto, el modelo aprende una reconstrucción aproximada de una fórmula conocida. El MAE de validación cruzada registrado es 2,6316 para XGBoost frente a 11,7558 para un predictor de media (`n=303`), pero esa diferencia no demuestra capacidad predictiva independiente. La relación feature-target es circular por diseño y la distribución de los percentiles del target se calculó antes de la validación cruzada.

Clasificación final: **D — metodológicamente problemático para afirmar predicción**, aunque puede conservarse como comparación exploratoria documentada. Recomendación única para P3.2: **Opción 2 — mantener ML como análisis exploratorio** hasta disponer de un panel temporal y una etiqueta externa; no reformular todavía como predicción temporal.

## Inventario de componentes

| Archivo/componente | Función | Entrada | Salida | Dependencias |
|---|---|---|---|---|
| `15_fuentes_riesgo_futuro.py` | Descarga y audita AdapteCCa | API AdapteCCa, maestro de 306 municipios | `data/raw/riesgo_futuro/adaptecca_proyecciones_municipales.csv` y mapeo | requests, geopandas, pandas |
| `16_indicadores_riesgo_futuro.py` | Resume clima 2041–2060 y calcula tendencias hasta 2023 | CSV climático y scores de asequibilidad, turismo, especulación y gentrificación | `data/processed/indicadores_riesgo_futuro.csv` | pandas, numpy |
| `17_indice_riesgo_futuro.py` | Calcula el score interpretable y ejecuta la comparación XGBoost | indicadores de riesgo futuro | `riesgo_futuro_residencial_score.csv`, `riesgo_futuro_comparacion_modelos.csv` | scikit-learn, XGBoost |
| `18_indice_presion_residencial.py` | Integra las cinco capas en IPR-5 | scores de capas, corte 2023 | `indice_presion_residencial_2023.csv` y diagnósticos | scikit-learn (PCA, regresión auxiliar) |
| `19_validacion_indice_presion_residencial.py` | Comprueba cobertura, rangos y trazabilidad | resultados y diagnósticos IPR | `ipr_validaciones.csv` | pandas, numpy |
| `14_auditoria_integracion.py` | Genera cobertura temporal y panel potencial | scores históricos | `cobertura_temporal_capas.csv`, `panel_estable_2020_2023.csv` | pandas, geopandas |
| `METODOLOGIA_RIESGO_FUTURO.md` | Documenta definición y limitaciones | — | documentación | — |
| `apps/api/.../repositories/observatory.py` | Sirve históricos de capas y scores | PostgreSQL | API de observatorio | FastAPI, SQLAlchemy |

No hay notebooks, modelos serializados (`pickle`/`joblib`), SHAP, permutation importance, GridSearch, RandomizedSearch, Optuna ni un endpoint específico de ML. `requirements.txt` incluye `scikit-learn==1.9.0` y `xgboost==3.2.0`.

## Flujo real

```text
AdapteCCa (ANOMALY, SSP2-4.5) ─┐
Scores históricos de 4 capas ─┤
                               ▼
       16_indicadores_riesgo_futuro.py
       clima medio 2041–2060 + pendientes hasta 2023
                               ▼
       percentiles P1–P99 (winsorización) y elegibilidad
                               ▼
       y = 0,60 × media(percentiles clima)
           + 0,40 × media(percentiles asequibilidad, turismo, gentrificación)
                               ▼
       X = 3 variables climáticas + 4 tendencias
                               ▼
       Pipeline(SimpleImputer(median) → XGBRegressor)
                               ▼
       KFold(n_splits=5, shuffle=True, random_state=42)
                               ▼
       cross_val_predict → MAE XGBoost y MAE DummyRegressor
                               ▼
       CSV comparativo (no usado por el score ni por la API)
```

El score publicado se calcula directamente con la fórmula interpretable y se carga en PostgreSQL. La aplicación muestra IPR-4/IPR-5 y las capas; no consume predicciones XGBoost.

## Problema, unidad, features y target

La tarea es **regresión**. La unidad de observación es un municipio (`cod_ine`), con una sola fila en el corte base `anio_base=2023`. El horizonte del target no es `t+1`: el bloque climático resume un escenario 2041–2060, mientras que las tendencias usan información observada hasta 2023. En consecuencia, no es una predicción temporal coherente.

### Features de X

| Feature | Fuente | Papel respecto al target | Clasificación |
|---|---|---|---|
| `proyeccion_duracion_max_ola_calor_dias` | AdapteCCa, media 2041–2060 | entra en el bloque climático del target tras percentil | `DIRECT_TARGET_COMPONENT` |
| `proyeccion_grados_dia_refrigeracion` | AdapteCCa, media 2041–2060 | entra en el bloque climático del target tras percentil | `DIRECT_TARGET_COMPONENT` |
| `proyeccion_racha_seca_max_dias` | AdapteCCa, media 2041–2060 | entra en el bloque climático del target tras percentil | `DIRECT_TARGET_COMPONENT` |
| `tendencia_asequibilidad` | score de asequibilidad 2015–2023, invertido como presión | entra directamente en el bloque de tendencias | `DIRECT_TARGET_COMPONENT` |
| `tendencia_turismo` | snapshots de agosto 2020–2023 | entra directamente en el bloque de tendencias | `DIRECT_TARGET_COMPONENT` |
| `tendencia_especulacion` | score 2022–2023 | se pasa a X pero se excluye del score; permanece nula por diseño | `POTENTIAL_LEAKAGE` / variable no activa |
| `tendencia_gentrificacion` | score hasta 2023, mínimo tres años | entra directamente en el bloque de tendencias | `DIRECT_TARGET_COMPONENT` |

No hay una feature independiente del target. Los nombres distintos no rompen el linaje: las variables derivan de las mismas capas que definen `y`.

## Auditoría del target y leakage

`score_riesgo_futuro` se calcula después de winsorizar cada variable en P1–P99 y convertirla a percentil dentro de los 303 municipios. Exige las tres variables climáticas y al menos dos tendencias; la cobertura publicada es 303/306. La fórmula es:

`RFR = 0,60 × mean(percentil_clima) + 0,40 × mean(percentil_asequibilidad, percentil_turismo, percentil_gentrificación)`.

Se identifican estos riesgos:

1. **Target leakage estructural (grave):** X contiene los componentes directos de la función que genera y. El modelo aproxima una transformación aditiva/monótona ya definida; un error bajo es esperable y no valida una predicción externa.
2. **Leakage de distribución en validación (moderado):** winsorización y percentiles de `y` se calculan sobre los 303 municipios antes de construir los folds. El `SimpleImputer` sí está dentro del `Pipeline` y se ajusta en cada fold, pero la construcción del target no está encapsulada en una transformación ajustada solo con train.
3. **Leakage temporal para el uso actual:** no se observa información posterior a 2023 en las tendencias; AdapteCCa es una proyección de escenario, no una observación futura utilizada para predecir un pasado. El problema principal es que el experimento tampoco define un horizonte temporal real.
4. **Entity/geographic leakage:** hay una fila por municipio, por lo que no se repite el mismo municipio entre folds. `KFold` aleatorio sí mezcla municipios espacialmente relacionados; no mide generalización a municipios o regiones nuevas.
5. **Duplicados:** los scripts validan claves únicas y el CSV de score tiene 303 municipios elegibles. No se encontraron modelos serializados ni una segunda tabla de predicciones que sugiera duplicación train/test.

## Split, preprocessing y XGBoost

No existe `train_test_split`, conjunto de validación separado ni test hold-out. Se usa `KFold(n_splits=5, shuffle=True, random_state=42)` y `cross_val_predict`; aproximadamente cuatro quintas partes entrenan cada fold y una quinta parte se predice. No hay estratificación, agrupación geográfica ni validación temporal. Para una serie temporal, este esquema no representa el uso `t → t+1`.

El único preprocessing del pipeline ML es `SimpleImputer(strategy="median")`, correctamente ajustado dentro de cada fold. La normalización por percentiles y la winsorización se realizan antes, al construir el target y las features derivadas. No se usa scaling, encoding, PCA ni selección de variables dentro del modelo.

Parámetros explícitos de `XGBRegressor`:

| Parámetro | Valor |
|---|---:|
| `objective` | `reg:squarederror` |
| `n_estimators` | 200 |
| `max_depth` | 3 |
| `learning_rate` | 0,03 |
| `subsample` | 0,8 |
| `colsample_bytree` | 0,8 |
| `random_state` | 42 |
| `n_jobs` | 1 |
| regularización, `gamma`, early stopping, `eval_set` | no especificados; defaults de XGBoost |

No hay optimización de hiperparámetros ni evidencia de selección usando un test. El modelo no se serializa ni se usa para producir el score final.

## Tamaño efectivo y métricas

| Medida | Evidencia |
|---|---:|
| Universo municipal | 306 |
| Observaciones ML elegibles | 303 |
| Features pasadas a XGBoost | 7 |
| Train por fold | aproximadamente 242 |
| Validación por fold | aproximadamente 61 |
| Test independiente | 0 |
| Años del target ML | 1 (2023) |
| Municipios sin score futuro | 3 (Cádiz, San Fernando, Getxo) |

El CSV canónico `data/processed/riesgo_futuro_comparacion_modelos.csv` registra:

| Modelo | MAE CV | n | Interpretación |
|---|---:|---:|---|
| Dummy media | 11,7558 | 303 | baseline de referencia |
| XGBoost | 2,6316 | 303 | reconstrucción del índice |

No hay R², RMSE, MSE, accuracy ni métricas de train. La mejora frente al dummy no debe leerse como capacidad de anticipar presión residencial. No existe baseline temporal `IPR_t+1 = IPR_t` porque no existe target `t+1`.

## Interpretabilidad y reproducibilidad

No se calcula feature importance ni SHAP. La importancia de una variable en este experimento, si se añadiera, solo describiría su contribución a reconstruir el índice; no probaría causalidad, efecto sobre desplazamiento ni validez de los pesos del IPR.

La ejecución es reproducible en principio: el código fija `random_state=42`, las versiones están fijadas en `requirements.txt`, el escenario climático es `SSP2-4.5`, la ventana 2041–2060 y la versión metodológica es 2.0. Los CSV procesados actúan como snapshot de datos. No se registra una fecha de ejecución en el resultado ni existe un artefacto de modelo serializado. La memoria confirma los MAE publicados.

## Relación con el IPR

El IPR-5 integra cinco capas con pesos 0,30/0,20/0,20/0,15/0,15. El ML auditado no predice ese IPR-5: opera únicamente sobre la capa de riesgo futuro, que después se incorpora con 15 %. El IPR-5 se calcula directamente en `18_indice_presion_residencial.py`; la API expone el CSV validado y no la predicción XGBoost. El valor añadido del modelo actual es, por tanto, demostrativo/diagnóstico: confirma que un algoritmo flexible puede aproximar un índice compuesto con sus propios ingredientes.

## Histórico y viabilidad temporal

El inventario de integración muestra que las cuatro capas observadas no forman un panel completo común en todos los años. El único corte completo publicado para las cuatro capas es 2023. Recalculando percentiles sobre un universo fijo, `panel_estable_2020_2023.csv` identifica 284 municipios potenciales para los cuatro años 2020–2023; el CSV advierte que requiere recalcular los scores. Esto ofrece como máximo tres transiciones anuales y cobertura incompleta fuera de ese panel.

| Target futuro posible | Ventaja | Limitación actual | Juicio |
|---|---|---|---|
| `IPR_t+1` | nivel futuro interpretable para dashboard | solo tres transiciones, cambios de cobertura/metodología y sin etiqueta validada | viable con limitaciones, no ahora |
| `ΔIPR_t+1 = IPR_t+1 − IPR_t` | responde a incremento de presión y reduce dependencia del nivel | más ruido, tres transiciones y fuerte sensibilidad a revisiones de capas | viable con limitaciones, no ahora |
| Riesgo BAJO/MEDIO/ALTO | fácil de comunicar | umbrales arbitrarios y aún menos observaciones por clase | no recomendado ahora |

La viabilidad temporal para ML se clasifica **VIABLE_WITH_LIMITATIONS** solo como trabajo futuro de investigación: requiere congelar un panel, recalcular todas las normalizaciones sin mirar el futuro, usar validación rolling-origin y definir una etiqueta externa o un protocolo de evaluación. Con el estado actual no hay base suficiente para defender una reformulación predictiva en P3.2.

## Clasificación y recomendación

El modelo no es A porque no existe separación independiente entre features y target ni evaluación externa. No es B como predictor, aunque sí puede conservarse como análisis exploratorio si se etiqueta de forma explícita. La clasificación operativa del bloque existente es **D — metodológicamente problemático para los resultados predictivos actuales**, debido al target leakage estructural y a la validación aleatoria de un único corte. No se recomienda eliminarlo de inmediato: mantener el CSV comparativo como evidencia de auditoría y evitar presentarlo como validación.

Para P3.2 se recomienda **mantener ML como análisis exploratorio**. Antes de cualquier modelo temporal deben congelarse los datos por fecha, reconstruirse targets `t+1` y `ΔIPR`, decidir una unidad de generalización (municipio o región), documentar cambios metodológicos y evaluar contra baselines temporales. Estas correcciones quedan fuera de esta issue.

**¿El Machine Learning actual aporta capacidad predictiva independiente o está principalmente reconstruyendo información ya contenida en el IPR?** Está principalmente reconstruyendo información ya contenida en el índice de Riesgo Futuro y sus componentes; no aporta capacidad predictiva independiente demostrada.

**¿Existe suficiente información temporal para justificar una reformulación predictiva en P3.2?** Existe un panel potencial 2020–2023 de 284 municipios, pero solo tres transiciones, cobertura y metodologías no completamente homogéneas y ninguna etiqueta externa. No es suficiente para justificar todavía una reformulación predictiva defendible; solo permite preparar un estudio temporal con limitaciones explícitas.

## Continuidad P3.2

Esta auditoría conserva la fotografía de P3.1. La implementación posterior y
sus límites están en [Análisis exploratorio mediante ML](ml_exploratory_analysis.md).
El experimento se separa ahora en el script 20 y añade TreeSHAP OOF. Se mantiene
la clasificación D para afirmar predicción. Precisión de implementación: el
script original eliminaba columnas completamente nulas, por lo que usaba seis
features efectivas, aunque el inventario anterior enumera siete candidatas.
Los percentiles oficiales se calculan con los valores disponibles de cada
variable antes de filtrar las filas elegibles, no necesariamente sobre las
mismas 303 observaciones para todas las variables. Ninguna de estas precisiones
cambia el diagnóstico de circularidad.
