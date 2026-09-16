# Evaluación previa de indicadores externos

Issue #10. Evaluación posterior a la [auditoría](AUDITORIA_IPR_VALIDACION_EXTERNA.md)
y anterior a implementar el análisis. Solo se inspeccionaron esquema, unidades,
periodos, claves y cobertura; no se calcularon correlaciones para seleccionar.

| Indicador y definición | Fuente y URL | Unidad; geografía; periodo comprobado | Cobertura sobre los 306 | Relación teórica e independencia | Ventajas y limitaciones | Decisión |
|---|---|---|---|---|---|---|
| Mediana de la cuantía de alquiler de vivienda colectiva | [MIVAU, CSV VDP001_01](https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP001_01.csv), SERPAVI | €/mes; municipio; fichero 2011–2024, corte 2023 | 295/306 valores publicados; faltan Álava y Bizkaia en este universo | Mayor tensión puede acompañar alquileres mayores. No reutiliza valor tasado, renta del hogar ni componentes del IPR | Medición tributaria pública y contemporánea. No mide esfuerzo, contratos nuevos, alquiler informal ni desplazamiento; depende de superficie y composición del parque | ACEPTADO, único contraste principal |
| Esfuerzo de compra o alquiler calculado con renta del Atlas | [INE Atlas 30824](https://www.ine.es/jaxiT3/Tabla.htm?t=30824) y fuentes de precio auditadas | Ratio; municipio; 2023 | Compra 306/306 en el pipeline; alquiler condicionado a fuente | Conceptualmente directo, pero reutiliza el denominador de asequibilidad y otras capas | Fácil de calcular, pero circular para esta issue | DESCARTADO |
| Ejecuciones hipotecarias sobre viviendas | [INE, resultados EH](https://www.ine.es/dyngs/INEbase/es/operacion.htm?c=Estadistica_C&cid=1254736176993&idp=1254735576606&menu=resultados) | Recuento; provincia; serie incluye 2023 | Sin observaciones municipales identificadas | Dificultades de permanencia; independiente del IPR | Oficial; no permite asignar eventos a los 306 municipios | DESCARTADO para contraste municipal |
| Lanzamientos practicados | [CGPJ, PxWeb](https://www6.poderjudicial.es/PxWeb2023v1/pxweb/es/10.-Juzgados%20de%20Primera%20Instancia%20e%20Instrucci%C3%B3n/-/OUJII021.px/), [resumen 2023](https://www.poderjudicial.es/portal/site/cgpj/menuitem.65d2c4456b6ddb628e635fc1dc432ea0/?vgnextoid=6934da53a159f810VgnVCM1000004648ac0aRCRD) | Recuento; órganos/partidos judiciales; 2023 | No equivalente a municipios; no se ha construido correspondencia | Relación con pérdida de vivienda, sin participación en fórmula | Próximo al fenómeno, pero sede del juzgado no es municipio del evento; no repartir por población | DESCARTADO para contraste municipal |
| Carga del gasto de vivienda y dificultades de acceso | [INE ECV, carga por urbanización](https://ine.es/jaxi/Tabla.htm?L=0&tpx=66501), [módulo acceso 2025](https://www.ine.es/dyngs/Prensa/m3ECV2025.htm) | % hogares/personas; agregados, urbanización y CCAA; módulo 2025 | No se identifican estimaciones para los 306 municipios | Relación directa con dificultades; encuesta externa | Conceptualmente preferible; geografía incompatible y módulo posterior a 2023 | DESCARTADO para contraste municipal |
| Saldo migratorio interior: entradas menos salidas entre municipios españoles | [INE EMCR 69767](https://www.ine.es/jaxiT3/Tabla.htm?t=69767) | Personas; municipio; CSV local 2021–2024 | 306/306 en la ingesta existente | Posible salida por tensión, pero también empleo, estudios y suburbanización. No entra en score | Cobertura completa; ya examinado como contraste de gentrificación, signo ambiguo, escala dependiente del tamaño; tasa por población comparte denominador con turismo | POSIBLE solo como estudio exploratorio futuro; no seleccionado |
| Evolución de población y hogares | [INE Atlas 30832](https://www.ine.es/jaxiT3/Tabla.htm?t=30832), padrón del pipeline | Personas, hogares y %; municipio; hasta 2023 | 306/306 en las capas actuales | Puede reflejar permanencia, pero población/estructura de hogares ya intervienen en construcción | Buena cobertura, solapamiento de variables y procesos demográficos | DESCARTADO |
| Declaración de zona tensionada | [BOE, primera relación de 2024](https://www.boe.es/buscar/doc.php?id=BOE-A-2024-5214) | Estado administrativo; municipio; 2024 | Relación selectiva de Cataluña, no muestra nacional comparable | Relacionada con precios/renta que fundamentan la declaración | No declarado no significa ausencia de tensión; selección institucional y posterior al corte | DESCARTADO |
| Crecimiento del precio de alquiler | [INE IPVA 59060](https://www.ine.es/jaxiT3/Tabla.htm?t=59060) | Índice/variación anual; municipios >10.000 habitantes; catálogo hasta 2023 | No cuantificada en esta evaluación; no aceptado por presunción | Mercado distinto a compraventa, sin identidad matemática con IPR | Posible sensibilidad futura; crecimiento anual y nivel de presión son conceptos diferentes | POSIBLE; no se incorpora automáticamente |

## Selección y comprobaciones de la fuente

Se elige **cuantía mediana mensual, vivienda colectiva**, filtros del CSV
`ELEMENTO=PRECIO`, `TIPO_VIVIENDA=COLECTIVA`, `TIPO_MEDIDA=MEDIANA`.
No es precio de oferta ni el límite individualizado de un contrato.
La [metodología SERPAVI, apartados 3–4 y 8](https://cdn.mivau.gob.es/portal-web-mivau/vivienda/alquila/2025-09-10_Metodolog%C3%ADa_SERPAVI.pdf)
describe explotación de alquileres habituales declarados, cuantía en €/mes,
tipologías separadas y publicación municipal sujeta a tamaño suficiente.
El fichero descargado incluye años posteriores a esa edición metodológica;
se utiliza 2023, comprendido en ella. La unidad se contrastó además con
[tablas oficiales SERPAVI 2025](https://publicaciones.transportes.gob.es/downloadcustom/sample/3808)
(Madrid 2023: 825 €/mes).

El campo del CSV llamado `COD_POSTAL` contiene aquí **códigos municipales INE**:
28079 Madrid y 08019 Barcelona, entre otros. Se conserva la denominación de
origen y se valida su prefijo provincial y su pertenencia al universo. No se
hacen uniones por nombre, inferencias a partir de códigos postales ni
correspondencias manuales. La lista de ausencias se genera en el análisis.

Independencia de construcción no implica fuentes estadísticas totalmente
inconexas: SERPAVI y el Atlas explotan información fiscal, pero miden objetos
distintos (inmuebles alquilados frente a ingresos de hogares residentes).
La cuantía municipal no es un término ni una transformación de la renta media
del Atlas, el valor tasado, las compraventas o sus denominadores. No se divide
por renta ni se combina con componentes del índice. Esta es una validación
convergente limitada al coste del alquiler, no una verdad externa sobre toda
la presión residencial. La composición del parque, ingresos, localización y
otras variables omitidas pueden explicar parte de la asociación.

## Protocolo previo al análisis

El archivo `config/validacion_externa.json` fija el contraste antes de ejecutar
el paso 20. **H1:** municipios con mayor IPR-4 observado en 2023 tenderán a
presentar mayor mediana mensual del alquiler de vivienda colectiva en 2023.
Se espera signo positivo por competencia por vivienda y costes de acceso en
mercados tensionados. **H0:** rho poblacional igual a cero; a nivel operativo,
no rechazar H0 representa ausencia de evidencia estadística de asociación.

Contraste principal: Spearman bilateral, alfa 0,05, casos completos, cobertura
mínima 90% del universo fijada antes de los resultados. Se usa prueba de
permutación reproducible por el tamaño muestral y empates; se publica también
el p asintótico como referencia, con su método identificado. No se ponderan
municipios por población. No se excluyen valores extremos en el contraste
principal ni se buscan transformaciones que eleven la asociación.

Robustez predefinida: retirar extremos fuera de P1–P99 en cualquiera de las dos
variables; IPR-5 en casos disponibles; IPR-4 en la misma muestra del IPR-5;
IPR-4 2023 frente a alquiler 2022 y 2024 en muestra común a los tres años.
Estas comparaciones son exploratorias, no nuevas pruebas confirmatorias ni
predicción. No existe histórico compuesto del IPR para analizar IPR_t.
Pearson no se ejecuta por defecto: este protocolo evalúa asociación monótona,
sin asumir linealidad ni normalidad. Se publican distribuciones y extremos.

Cuartiles: límites del IPR-4 de todo el universo, antes del join; los empates
permanecen juntos. Medianas, P25/P75, N y Kruskal–Wallis global exploratorio.
No se interpreta este último como prueba específica Q1 contra Q4. Si los
límites coinciden se omite el contraste de cuatro grupos y se documenta.

Se publicarán igualmente asociaciones nulas, negativas o no significativas.
Los p-values suponen intercambiabilidad/independencia municipal; la dependencia
territorial puede hacerlos optimistas. No son evidencia causal, capacidad
predictiva ni certificación de que el IPR sea correcto. No se optimiza el IPR.
