# IPR-4 histórico relativo

## Producto y significado

El histórico `historico-relativo-1.0` contiene 1.108 puntuaciones (277 municipios
× 2020–2023) y 4.432 observaciones de componentes. La
[auditoría temporal](AUDITORIA_IPR_HISTORICO.md) justifica el periodo y enumera
las 29 exclusiones. El IPR-4 nacional 2023 y el IPR-5 prospectivo son productos
distintos: no se conectan con esta serie ni se comparan sus rankings como si
compartieran universo.

Un incremento del IPR histórico representa un aumento **relativo** de la presión
residencial medida por las cuatro capas dentro del universo fijo analizado.
Puede cambiar la puntuación aunque el valor original del municipio no cambie,
si cambian los demás municipios. Tampoco una puntuación estable implica que no
hayan subido precios o VUT en términos absolutos. No establece causalidad.

## Cálculo compartido y orientación

Se parte de los indicadores trazables de los pipelines 04, 06, 09 y 12. No se
reutilizan scores calculados sobre universos anuales diferentes.

| Capa | Inputs y tratamiento | Peso fijo |
|---|---|---:|
| Presión de acceso | Precio anual ponderado × 90 m² / renta anual por hogar; mayor ratio = mayor presión | 30/85 |
| Turismo | Media de percentiles de VUT/1.000 habitantes y VUT/km², snapshot de agosto | 20/85 |
| Especulación | Media de percentiles de rotación, aceleración del precio y desacoplamiento precio-renta | 20/85 |
| Gentrificación | Media de percentiles de crecimiento logarítmico trianual de renta por persona, brecha precio-renta trianual y transformación de hogares ajustada | 15/85 |

Los cuatro pesos suman uno y son los del IPR-4 vigente. El ajuste de hogares usa
OLS con intercepto y cambios trianuales en mayores de 65 y menores de 18. Se
reestima por año usando exactamente los 277 municipios. Después se winsoriza
cada input de gentrificación en p01/p99 del panel de ese año. No se aplica un
recorte adicional a las otras capas: los percentiles limitan la influencia de
la magnitud de extremos.

Para integrar las capas se vuelve a aplicar el percentil anual a cada score de
capa, como hace el paso 18. Para acceso esto equivale a invertir la orientación
del score original de asequibilidad. El percentil es
`100 × (rango_medio − 1) / (n − 1)`, con empates simétricos. Una distribución
constante con al menos dos valores recibe 50; una ausencia permanece ausente.
Se reutilizan la función de percentiles del IPR actual y la regresión de
hogares mediante `analytics/normalization.py`.

La persistencia exige todas las capas, scores finitos 0–100 y el mismo conjunto
de municipios todos los años. Los nulos no se sustituyen por cero y los pesos
no se renormalizan por municipio. No se interpola entre snapshots o años.

## Alternativas de normalización

1. **Percentiles anuales, panel fijo (seleccionada):** conserva la interpretación
   y fórmula relativa del índice vigente. Sirve para comparar posiciones y
   contribuciones relativas; puede ocultar subidas generales sin cambios de orden.
2. **Distribución de referencia congelada:** permitiría medir movimientos
   respecto a un año base, pero necesitaría fijar también los cortes de
   winsorización y el ajuste de hogares. Puede saturarse fuera del rango de
   referencia y cambia el significado del producto. No se adopta como cambio
   silencioso del IPR.
3. **Distribución conjunta de todos los años:** evita algunas saturaciones,
   pero añadir un año podría modificar todo el histórico. Exigiría otra versión
   y un producto identificado como tal.

Los tests incluyen una subida uniforme de todas las observaciones (percentiles
sin cambio), un municipio constante que cambia de posición por los demás y
empates/nulos. Estas limitaciones se indican en la ficha municipal y no se
ocultan bajo una etiqueta de presión absoluta.

## Métricas y convención

- `delta_ipr = IPR_t − IPR_t-1`: positivo = mayor presión relativa.
- `delta_since_start = IPR_t − IPR_inicio`: positivo = mayor presión relativa.
- `rank_change = rank_t − rank_t-1`: puesto 1 = mayor presión; positivo =
  desplazamiento hacia menor presión relativa. La dirección es inversa a
  `delta_ipr` y se explica en la interfaz.
- `delta_component` y `delta_contribution`: cambios en puntuación de capa y en
  su aporte ponderado. La suma de cambios de contribución coincide con
  `delta_ipr`, salvo redondeo visual.

El primer año no tiene cambio anual ni cambio de puesto: ambos son nulos.
`delta_since_start` sí es cero. El ranking usa `rank(method="min")` descendente,
con el mismo puesto para empates. Para ranking y percentil final se redondea el
score a diez decimales: así la lectura de CSV o diferencias de coma flotante
no deshacen un empate. Las puntuaciones y contribuciones conservan su precisión.
Los filtros territoriales conservan el ranking
del panel completo. No se publica variación porcentual sobre un índice ordinal.

La serie de cuatro años incluye pandemia y ventanas trianuales solapadas.
No permite concluir por sí sola que exista una tendencia estructural. Las
gráficas unen observaciones con segmentos rectos y conservan los huecos.

## Persistencia y trazabilidad

`sql/20_ipr_historico.sql` crea:

- `ipr_historical_runs`: versión, huella SHA-256, metadatos y `calculated_at`.
- `historical_municipality_universe`: 306 entradas por versión, inclusión y motivo.
- `ipr_historical_scores`: clave primaria `(cod_ine, anio, calculation_version)`,
  IPR, percentil, ranking y cambios.
- `ipr_historical_components`: clave adicional de componente, score de capa,
  score integrado, peso, contribución, cambios, valores de inputs y clave/archivo
  de origen. El ajuste de hogares es recalculado: su contexto es el panel y el
  método de la versión, no el residuo del CSV nacional.

El manifiesto conserva huellas de archivos procesados, originales disponibles y
código del cálculo. Los componentes apuntan a `cod_ine/año` o
`cod_ine/año-08-01`; los retardos y fuentes se describen en la auditoría.
`calculated_at` pertenece a la ejecución y se recupera junto al histórico; no
cambia al repetir una carga idéntica.

Las cuatro tablas se cargan en una transacción. Una versión ya persistida con
otra huella se rechaza: hay que publicar una versión nueva, sin sobrescribir
la anterior. El bootstrap valida las huellas de los tres CSV de resultados y
las invariantes antes de cargarlos. Cada versión conserva su universo; nunca se
mezclan observaciones de dos versiones en una consulta.

## Ejecución y API

```bash
python 20_ipr_historico.py --audit-only
python 20_ipr_historico.py --no-db
python 21_validacion_ipr_historico.py
# Con DATABASE_URL configurada:
python 20_ipr_historico.py
```

`--output` permite generar archivos en otro directorio. El bootstrap habitual
de Docker carga los CSV versionados sin recalcular los datos científicos.
`--audit-only` escribe en el subdirectorio `audit/` para no invalidar un
manifiesto de resultados ya calculados.

Se amplían endpoints existentes:

- `/api/v1/catalogo`: conserva `years` del corte nacional y añade `historical`
  con periodo, universo, versión, fecha de cálculo y trazabilidad.
- `/api/v1/municipios/28079/historico?serie=homogenea`: devuelve elegibilidad,
  motivo, metadatos y años con componentes y métricas. Un municipio excluido
  devuelve `included=false` y una lista vacía; uno desconocido devuelve 404.
  Sin el parámetro se conserva la respuesta anterior de series disponibles.
- `/api/v1/ranking?producto=historico&anio=2022`: ranking anual del panel,
  con los filtros territoriales existentes y exportación `formato=csv`.
- El mismo ranking admite `orden=incremento`, `descenso`, `subida_ranking` o
  `bajada_ranking`: solo cambios con el signo correspondiente. En el primer año
  devuelve listas vacías. Un año no disponible devuelve 422.

La ficha muestra la curva y tabla de IPR, selector anual, contribuciones,
evolución de componentes y ranking/cambios destacados. El mapa y el ranking
nacional conservan su corte de 2023; los años del panel se consultan en su
sección propia para mantener explícita la diferencia de universo.

## Validación

`tests/test_ipr_historical.py` comprueba selección sin fechas prefijadas,
continuidad, cobertura real, universo fijo, duplicados, nulos/infinito,
reproducibilidad al permutar filas, contribuciones, métricas, límites de la
normalización y regresión del IPR actual. Los tests de API comprueban consultas,
exclusiones, rankings por año, filtros de cambio y la restricción única en
PostgreSQL. Las pruebas web recorren selector, componentes y municipios excluidos.

El contraste reproducible de tres municipios y sus límites se describe en la
[auditoría](AUDITORIA_IPR_HISTORICO.md#contraste-de-municipios).
