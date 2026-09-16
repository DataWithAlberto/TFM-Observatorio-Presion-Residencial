# Preguntas de investigación y marco interpretativo

El alcance analítico se fija antes de interpretar los resultados. La siguiente
matriz evita atribuir al sistema respuestas que todavía no puede producir.

| Pregunta | Datos | Metodología actual | Resultado esperado |
|---|---|---|---|
| **RQ1.** ¿Qué municipios presentan mayores niveles relativos de presión residencial según los indicadores seleccionados? | Corte integrado 2023, cuatro capas observadas y, cuando existe cobertura, riesgo futuro | Percentiles 0–100, suma ponderada IPR-4/IPR-5, ranking y componentes | Ranking relativo, categoría y contribución por capa |
| **RQ2.** ¿Existen patrones espaciales significativos en la distribución municipal? | Geometría municipal e IPR | Comparación cartográfica descriptiva; Moran's I y LISA quedan como fase posterior | Hipótesis espacial contrastable cuando se implemente el análisis inferencial |
| **RQ3.** ¿En qué medida el IPR se relaciona con indicadores externos de tensión no usados en su construcción? | Fuentes externas de validación, aún no incorporadas | Validación externa, fase posterior | Asociación externa cuantificada, sin afirmar causalidad |

## Cadena de interpretación

`dato observado → indicador derivado → índice compuesto → asociación estadística → causalidad`

Cada salto añade supuestos. El IPR es un índice compuesto y relativo al
universo analizado: sintetiza dimensiones relacionadas con presión residencial y
permite comparaciones, rankings y detección de patrones. No es un umbral
absoluto ni una estadística oficial.

Una correlación o cualquier asociación estadística no demuestra que una
variable provoque otra. El diseño transversal, la selección de proxies y la
unidad municipal limitan la inferencia causal. Los modelos de ML cuyo objetivo
es el propio IPR solo reproducen o explican el índice; no constituyen validación
predictiva externa. En particular, el contraste XGBoost documentado en Riesgo
Futuro no debe presentarse como evidencia independiente del IPR.

