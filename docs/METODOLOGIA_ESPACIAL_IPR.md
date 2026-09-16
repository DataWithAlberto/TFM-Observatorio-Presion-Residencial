# Patrones espaciales del IPR — RQ2

**RQ2: ¿Existen patrones espaciales significativos en la distribución municipal de la presión residencial?**

Moran global contrasta la existencia de estructura espacial general. LISA permite
localizar asociaciones y posibles outliers. El análisis usa exclusivamente el
IPR-4 observado; no redefine el índice ni incorpora el componente prospectivo.

## Auditoría y población de referencia

La ejecución parte de `data/raw/municipios_306_con_geometria.gpkg` y del CSV
canónico `indice_presion_residencial_2023.csv`. Se enlazan por `cod_ine`, código INE
de cinco dígitos, mediante una correspondencia uno a uno por municipio y año.

Antes de construir pesos se validan códigos, duplicados por municipio-año,
geometrías nulas/vacías/inválidas/topológicamente iguales, polígonos, CRS,
correspondencia bidireccional, valores finitos de IPR y años válidos. Cualquier
fallo detiene la estimación y deja un informe de auditoría. No se reparan
polígonos, redondean coordenadas ni imputan puntuaciones automáticamente.

El resultado real es **306 geometrías válidas, EPSG:4326, sin duplicados ni
municipios sin correspondencia**. No se usa la geometría simplificada de la API
para calcular pesos. El identificador espacial coincide con el municipal; no es
necesario introducir otro identificador.

## Vecindad: elección anterior a la significación

Se utiliza **Queen**, mediante `libpysal.weights.Queen`: compartir frontera o
vértice. Es una definición territorial transparente, sin radio arbitrario.
Rook exige frontera compartida y se evalúa como sensibilidad geométrica. No se
elige el método según el p-valor ni la apariencia de los clústeres.

| Método | Enlaces dirigidos | Sin vecinos | Componentes | Vecinos mínimo/máximo/media |
|---|---:|---:|---:|---|
| Queen | 540 | 86 | 128 | 0 / 13 / 1,765 |
| Rook | 532 | 88 | 130 | 0 / 13 / 1,739 |

Queen incorpora ocho relaciones dirigidas adicionales de vértice y conserva
dos municipios más para la inferencia. Los códigos y las listas de vecinos se
ordenan antes de calcular; se registra una huella SHA-256 de las relaciones.
La matriz binaria es simétrica; la transformación por filas puede ser asimétrica:
`w_ij = 1 / número de vecinos de i`. Los municipios evaluados tienen suma de pesos
uno, diagonal cero y cada vecino cuenta por igual.

## Islas y muestra discontinua

El universo no cubre todos los municipios españoles. **Sin vecinos en la muestra
no equivale a isla geográfica.** Queen deja 86 aislados; sus códigos y candidatos
alternativos están en el [informe generado](../output/analisis_espacial/informe.md).

Se evaluó KNN con `k=1` sobre puntos representativos interiores, usando distancia
esférica en WGS84 para elegir el candidato (radio 6371,0088 km) y distancia
elipsoidal WGS84 para describir el enlace. Las distancias oscilan entre **7,2 y
162,8 km**, con mediana **30,4 km**. Es un diagnóstico reproducible, no una matriz
adoptada. Incluso el punto interior más cercano puede proponer relaciones entre
islas o a través de espacios rurales sin observaciones. Centroides o puntos
representativos tampoco equivalen a redes de transporte ni interacciones reales.

Se mantiene Queen sin añadir KNN. **Moran y LISA se estiman sobre 220 municipios
con vecinos**, incluidos sus componentes desconectados. La inferencia usa
permutaciones entre esos 220 municipios: presupone intercambiabilidad de sus
valores bajo H0, no un modelo específico por componente. Esta hipótesis y el
sesgo de selección limitan la generalización al conjunto nacional.

Los 86 aislados se conservan en los resultados y mapa con IPR original,
`eligible=false`, motivo `sin_vecinos_queen`, cero vecinos y estadísticos y
p-valores nulos. Se almacenan en NS, con `is_significant=false`, pero el mapa los
distingue como **no evaluables**. No se les asigna un p-valor ficticio de uno ni
se afirma ausencia de asociación.

## Moran global y scatterplot

Se usa `esda.Moran`. Para los n municipios evaluables y su IPR centrado `x`:

`I = (n / S0) × (x' W x) / (x' x)`.

Con filas normalizadas y sin aislados, `S0=n`; la pendiente del scatterplot es I.
El gráfico representa `z=(IPR-media)/desviación poblacional` frente a `Wz`, ambos
calculados en el backend sobre el mismo universo de inferencia. El scatterplot
no incluye aislados; no se sustituyen sus lags por ceros.

Bajo aleatorización, `E[I]=-1/(n-1)`. Se registran I, E[I], p-valor de
permutaciones, `z_sim` (distancia a la media simulada en desviaciones simuladas),
999 permutaciones, año, n, semilla 2023 y versión. El z-score no sustituye el
contraste de permutaciones. Se comprueban límites espectrales del operador
simetrizado y centrado: **no se impone incorrectamente I ∈ [-1,1]** para cualquier
matriz de pesos.

H0: valores intercambiables espacialmente, sin asociación con la vecindad.
H1 bilateral: asociación positiva o negativa. Para el valor observado T se
calcula `min(1, 2 × min((1+#Tsim≥T)/(B+1), (1+#Tsim≤T)/(B+1)))`.
Las colas incluyen empates. `two_tailed=True` de ESDA afecta p-valores analíticos;
no convierte automáticamente `p_sim` en bilateral. Por eso se usan las
simulaciones de ESDA y se explicita el contraste. La corrección +1 evita p=0.

El empate se compara con una tolerancia relativa de 1e-9 en lugar de con
igualdad exacta. Cuando una permutación reproduce la configuración observada el
estadístico simulado es el observado, pero lo calculan rutinas distintas (el
núcleo compilado de ESDA y la ruta directa de NumPy) y solo coinciden hasta el
último bit: con la igualdad exacta, el recuento de empates dependía de la
arquitectura y un municipio de un solo vecino podía mover su p-valor hasta
0,026 entre máquinas. Con tolerancia, el empate entra en ambas colas siempre y
el p-valor publicado es reproducible fuera de la máquina que lo generó.

Un I positivo indica tendencia a valores similares próximos; uno negativo,
contraste entre vecinos. Un valor próximo a cero puede ser compatible con
aleatoriedad; la conclusión depende del contraste, no solo del signo. Una subida
temporal de I mide estructura espacial, no aumento absoluto de presión.

## LISA y comparaciones múltiples

`esda.Moran_Local`, permutación condicional, `seed=2023`, `n_jobs=1`, 999
permutaciones y pesos R. El valor del municipio focal permanece fijo; sus
vecinos se comparan con selecciones aleatorias del resto del universo evaluable.
Se usa el mismo criterio bilateral inclusivo que para Moran global, aplicado a
cada distribución condicional. El esquema de cuadrantes de PySAL se traduce
explícitamente: 1=HH, 2=LH, 3=LL, 4=HL.

- **HH**: municipio por encima de la media rodeado de valores también elevados.
- **LL**: municipio por debajo de la media rodeado de valores también bajos.
- **HL**: valor alto frente a vecinos bajos; posible outlier espacial.
- **LH**: valor bajo frente a vecinos altos; posible outlier espacial.
- **NS**: no alcanza el criterio de significación elegido, o no es evaluable
  (en este último caso se identifica expresamente).

“Alto” y “bajo” son relativos a la media de los 220 evaluables; no equivalen a
los umbrales de categoría del IPR. Los puntos exactamente en un eje no se
asignan a un cuadrante ni se etiquetan como clúster significativo.

Se conservan p continuo, p ajustado, significación y clasificación tanto sin
corrección como con **Benjamini–Hochberg (FDR)**, usando
`scipy.stats.false_discovery_control`. La familia incluye los 220 contrastes
locales de cada año, incluso los que no resultan significativos; nunca solo
los seleccionados. Alfa=0,05. La vista principal usa FDR para moderar falsos
descubrimientos; la vista sin corrección está etiquetada como exploratoria.
BH tiene garantías bajo independencia o determinadas dependencias positivas;
los contrastes espaciales son dependientes y no se presume control exacto bajo
cualquier dependencia. Se trata de análisis exploratorio, no validación causal.

**Impacto real con 999 permutaciones:** 27 asociaciones sin corrección (13 HH,
10 LL, 3 HL, 1 LH) y **ninguna con FDR**. Los 306 registros se conservan en NS
bajo FDR, de los cuales 86 son no evaluables. No se identifican clústeres HH
confirmados por el criterio principal. Esto es compatible con Moran global
significativo: la evidencia global no garantiza localizar asociaciones tras
multiplicidad.

Con B=999 y el contraste bilateral, el p mínimo es 0,002; el primer umbral BH
es 0,05/220 ≈ 0,000227. La resolución y el número de descubrimientos conjuntos
limitan la potencia. El pipeline permite fijar más permutaciones **antes** de
un análisis; no se incrementan ni cambian parámetros sucesivamente hasta
conseguir significación. Estos resultados no prueban inexistencia de clústeres.

## Resultados y revisión visual

Moran global 2023: **I=0,535490; E[I]=-0,004566; z=7,706; p=0,002**.
El [informe](../output/analisis_espacial/informe.md) contiene gráficos exportables,
vecinos, pesos, puntuaciones y p-valores para revisar cada categoría. Los
polígonos y enlaces de la muestra se comprobaron visualmente:

| Ejemplo | Categoría exploratoria | Lectura de vecinos |
|---|---|---|
| Alhaurín de la Torre | HH | IPR 64,65; vecinos entre 83,24 y 90,36 |
| Villena | LL | IPR 31,65; Almansa 5,40 y Yecla 17,49 |
| Oviedo | HL | IPR 58,38; vecinos entre 13,52 y 47,64 |
| La Orotava | LH | IPR 40,87; vecinos entre 53,68 y 93,98 |

Ninguno supera FDR. El informe también incluye un caso NS sin significación
exploratoria. Las líneas entre puntos representan relaciones de la matriz;
no son rutas físicas ni límites de zonas de presión.

## Histórico y calidad

En esta revisión solo hay IPR comparable de 2023. Las series de componentes no
se presentan como histórico del índice. El pipeline acepta varios años si
mantienen exactamente el universo y las columnas `metodo` y
`version_metodologia`; quien prepare la entrada debe asegurar además idéntica
calibración y definición. Se conserva la geometría de referencia y se calculan
Moran/LISA por año, más transiciones municipio-año en `spatial_transitions.csv`.
Cambios de límites municipales o de calibración requieren una revisión previa;
no se asumen comparables por coincidir el código INE.

DQS (P2.3) **no está implementado en la base de esta rama**. Se expone nulo,
con disponibilidad falsa; la cobertura de fuentes existente no es un DQS.
No se multiplica IPR por DQS. La UI reserva la visualización separada y el aviso
para asociaciones con DQS bajo cuando una futura integración lo provea.

## Persistencia, API y ejecución

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements-spatial.txt
python 23_analisis_espacial_ipr.py
```

La ejecución genera:

- `data/processed/spatial/spatial_audit.json`: control previo y alternativas.
- `spatial_ipr.json`: resultados y metadatos, listas de vecinos, parámetros,
  versiones de librerías, huellas de fuentes y fecha UTC.
- `spatial_global.csv`, `spatial_lisa.csv`, `spatial_transitions.csv`.
- `output/analisis_espacial/informe.md` y figuras PNG.

Para reproducir los resultados, conservar fuentes, versiones y parámetros.
Las estadísticas son deterministas; la fecha de ejecución varía. Diferencias
entre plataformas pueden afectar últimos decimales y permutaciones Numba;
se registran las versiones y se verifica el entorno usado. La semilla local se
pasa a ESDA, pues una semilla NumPy externa no basta para Numba.

`sql/20_analisis_espacial.sql` define resultados globales por año y LISA por
`cod_ine + anio`, con claves y restricciones. Los metadatos de ejecución se
guardan con cada resultado global. Bootstrap valida las huellas de las fuentes
y carga ambos conjuntos atómicamente; no mezcla versiones ni duplica registros.
El arranque sirve resultados precalculados; no necesita PySAL ni recalcula.

```bash
docker compose up --build --wait
# Tras regenerar resultados:
docker compose run --rm -e FORCE_BOOTSTRAP=1 bootstrap
```

API existente, prefijo `/api/v1`:

- `GET /espacial/historico`: años disponibles y Moran global.
- `GET /espacial?anio=2023`: Moran global, resumen y valores LISA del mismo año.
- `GET /municipios/{cod_ine}/espacial?anio=2023`: IPR, LISA y vecinos ponderados.

La capa reutiliza `/mapa/geometrias`. Años no disponibles devuelven 422;
municipios no disponibles, 404; falta de cálculos, 503. El dashboard está en
`/espacial`, con selección de año, criterio, municipio, mapa categórico y
scatterplot precalculado. No estima estadísticos en el navegador.

## Validación de la implementación

- 23 pruebas propias del bloque: 19 de cálculo (auditoría, reproducibilidad de
  pesos y permutaciones, empates del p-valor, FDR, islas, histórico sintético) y
  4 de contrato de la API, todas superadas.
- La vista `/espacial` forma parte del recorrido Playwright del proyecto, con
  cambio de criterio, municipio y pantallas entre 320 y 1440 px.
- ESLint, TypeScript y compilación de producción correctos.
- Arranque Docker con PostGIS, carga de resultados y API verificados.
- Revisión visual de scatterplot, vecinos HH/LL/HL/LH/NS y dashboard en escritorio
  y móvil; el año simulado solo existe en pruebas, nunca en los datos publicados.

## Referencias

- [ESDA Moran](https://pysal.org/esda/v2.9.0/source/generated/esda.Moran.html): estadístico global y permutaciones.
- [ESDA Moran Local](https://pysal.org/esda/v2.9.0/source/generated/esda.Moran_Local.html): semilla, cuadrantes y permutación condicional.
- [libpysal Queen](https://pysal.org/libpysal/v4.14.1/generated/libpysal.weights.Queen.html): contigüidad y normalización.
- [libpysal KNN](https://pysal.org/libpysal/stable/generated/libpysal.weights.KNN.html): alternativa por vecinos más cercanos.
- [SciPy FDR](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html): Benjamini–Hochberg y supuestos de dependencia.

> La existencia de autocorrelación espacial indica que la distribución territorial del IPR no es independiente del entorno geográfico, pero no demuestra relaciones causales entre municipios.
