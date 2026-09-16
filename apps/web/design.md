# Sistema de diseño — Hoja catastral

Especificación de la interfaz del Observatorio de Presión Residencial. Describe
lo que hay implantado en `apps/web`. Las modificaciones visuales deben conservar
este contrato.

## Concepto

El observatorio se presenta como una **hoja cartográfica técnica**: papel claro,
tinta casi negra, marco de doble filete, retícula geográfica, barra de escala,
flecha de norte y una franja de metadatos al pie (el «cajetín» de los planos).
La rampa de datos es **carmín**, el color con que la cartografía urbana
tradicional rellenaba lo edificado.

El rigor se ve en la forma —código INE, corte, universo, fuentes y sistema de
referencia siempre accesibles— pero la pantalla se mantiene tranquila: una
lectura, una figura y una sola cosa en la columna lateral.

Público: tribunal del TFM, analistas, equipos técnicos y prensa. Debe seguir
siendo comprensible para cualquier vecino.

## Principios

1. **Lectura antes que datos.** Cada vista abre con un titular que dice qué se
   ve y una frase calculada con los datos visibles.
2. **Una cosa cada vez.** La columna lateral muestra *o* los diez primeros *o*
   el municipio elegido. Los filtros viven plegados y los activos se ven como
   fichas que se pueden quitar.
3. **El mapa es la figura.** Todo lo demás es marco. La leyenda va sobre el
   mapa, junto a lo que explica.
4. **Metadatos presentes, no protagonistas.** El cajetín es una franja de una
   línea; solo la ficha municipal y las páginas de lectura lo llevan entero.
5. **Filete antes que caja.** Se separa con líneas de 1 px, no con sombras ni
   esquinas redondeadas. Radio 0 en todo.
6. **Jerarquía por tamaño y peso, no por mayúsculas.**
7. **Nada decorativo que no signifique algo.** La retícula es de 2° reales, la
   escala es métrica real, los números de puesto son el ranking real.

## Color

Todos los tokens están en `apps/web/tokens.css`. Contrastes con la fórmula
WCAG 2.x.

### Interfaz

| Token | Hex | Uso | Contraste |
|---|---|---|---|
| `--color-paper` | `#F3F4EF` | Fondo de página y de hoja | — |
| `--color-paper-2` | `#E9ECE5` | *Hover* de filas y pestañas | — |
| `--color-ink` | `#17201B` | Texto principal, filetes de marco, pestaña activa, botón principal | 15,1:1 |
| `--color-ink-2` | `#36413A` | Texto secundario de párrafo | 9,6:1 |
| `--color-muted` | `#56615A` | Etiquetas, provincias, notas | 5,8:1 (AA) |
| `--color-rule-2` | `#9AA59E` | Filetes interiores decorativos — **no apto para texto ni bordes de control** | 2,3:1 |
| `--color-rule` | `#D2D8D3` | Separadores de fila, pistas de barras, retícula de gráficos | — |
| `--color-accent` | `#962C5E` | Enlaces, foco, contador de filtros, barras de factores | 6,7:1 |
| `--color-accent-strong` | `#561238` | *Hover* de enlaces, extremo de la rampa | 12,3:1 |
| `--color-accent-soft` | `#EBDDE3` | Fila seleccionada en tablas | tinta 12,7:1 |

Los bordes de campos, selectores y pestañas usan siempre `--color-ink`.

### Datos

| Rampa | Tokens | Uso |
|---|---|---|
| Secuencial carmín | `--data-seq-1…5` | Capas de puntuación 0–100 y leyenda por quintiles |
| Divergente | `--data-div-1…5` | Diferencia IPR-5 − IPR-4 (−15 a +15) |
| Sin dato | `--color-map-missing` | Municipios fuera del filtro o sin valor |
| Series de gráfico | `--data-series-1…5` | Líneas de evolución por factor |

Categorías (quintiles de 61–62 municipios): Muy baja, Baja, Media, Alta, Muy
alta, con los cinco colores de la rampa en ese orden.

**Ningún color literal fuera de `tokens.css`, `lib/mapTheme.ts` y
`lib/chartTheme.ts`.** Los dos últimos existen porque MapLibre y ECharts pintan
sobre lienzo y no resuelven `var(--…)`: `mapTheme` declara el tema del mapa y
`chartTheme` lee los tokens del documento en tiempo de ejecución.

## Tipografía

Dos familias variables de Google Fonts, cargadas con `next/font` en
`lib/fonts.ts` y expuestas en el `<body>`:

| Rol | Familia |
|---|---|
| Texto, titulares y cifras destacadas | **Archivo** (ejes `wght` y `wdth`) |
| Códigos, puestos, microetiquetas y columnas numéricas de tabla | **Spline Sans Mono** |

### Escala

| Nombre | Tamaño / interlínea | Peso · anchura | Estilo | Dónde |
|---|---|---|---|---|
| Marca | 15 / 1 | 760 · 125 % | MAYÚSCULAS, +0,05 em | Cabecera |
| Nombre de ficha | clamp(30, 4,4 vw, 58) / 0,98 | 800 · 125 % | MAYÚSCULAS, +0,01 em | H1 de la hoja municipal |
| Titular de vista | 26 / 1,1 (22 en móvil) | 720 · 112 % | Redonda, −0,01 em | H1 de cada página |
| Nombre en panel | 24 / 1,05 | 780 · 118 % | MAYÚSCULAS, +0,02 em | Municipio en la columna |
| Cifra grande | 56 (panel) · 76 (ficha) / 0,85 | 500 · 112 %, tabular | Redonda, −0,04 em | Puntuación |
| Lectura | 15 / 1,45 | 400 | Redonda | Frase bajo el titular |
| Cuerpo | 13–14 / 1,35 | 400; 600 énfasis | Redonda | Listas, navegación, pestañas |
| Título de sección | 11 / 1,2 | 700 · 118 % | MAYÚSCULAS, +0,08 em | «Los diez con más presión» |
| Etiqueta | 12 / 1,3 | 400 | Redonda, `muted` | Etiquetas de campo, notas |
| Microetiqueta | 8,5–9,5 / 1,2 | Spline Sans Mono 500 | MAYÚSCULAS, +0,08 em | Cajetín, cabeceras de tabla |

Reglas:

- **Mayúsculas solo en tres sitios**: la marca, los títulos de sección y el
  nombre del municipio en su ficha.
- **Monoespaciada solo** en códigos, puestos, microetiquetas y columnas
  numéricas de tabla. Las puntuaciones destacadas van en Archivo con cifras
  tabulares.
- Cifras con coma decimal y un decimal (`fmt()` en `lib/format.ts`).
- `font-variant-numeric: tabular-nums` en toda cifra que se compare en columna.
- `text-wrap: balance` en titulares; medida de párrafo entre 45 y 78 caracteres.
- Topónimos normalizados con `placeName()`: «PALMAS, LAS» → «Las Palmas».

## Espaciado, filetes y movimiento

- Escala de 4 px: `4 · 8 · 12 · 16 · 20 · 24 · 32 · 48` (`--space-*`).
- Margen exterior de la hoja: 14 px (8 en móvil). Doble filete: borde 1 px +
  contorno 1 px separado 3 px.
- Columna lateral del explorador: 340 px; de la ficha: 380 px.
- Altura de controles 32–40 px; pestañas 38 px; cabecera 52 px.
- Puntos de corte: **1100 px** (una columna por debajo) y **640 px** (móvil).
  Mínimo soportado 320 px.
- Radio 0 en todo. Sombras difusas prohibidas; la única sombra es plana
  (`--shadow-dialog`), para paneles emergentes.
- Casi ningún movimiento: cambios de estado instantáneos. Solo el mapa anima el
  encuadre (650 ms). Con `prefers-reduced-motion` toda transición dura ≤ 0,01 ms.

## Componentes

Viven en `apps/web/components/hoja/`, cada uno con su CSS Module.

| Componente | Qué hace |
|---|---|
| `Sheet` | Marco de doble filete. Una página marca su raíz con `data-sheet="fixed"` para que la hoja mida exactamente la ventana en escritorio y no haga *scroll*. |
| `Masthead` | Marca, navegación, buscador de municipio y paleta de comandos. Por debajo de 1100 px la navegación se pliega tras «Menú». |
| `MunicipalitySearch` | Campo de la cabecera; escribe `buscar` en la URL. |
| `LayerTabs` | Las seis capas como `radiogroup`, recorrible con flechas. |
| `FiltersPanel` | Botón «Filtros» con contador y panel emergente: comunidad, provincia, rango de puntuación con histograma y acciones. Admite controles extra. |
| `TitleBlock` | Titular, conmutador o nota, frase de lectura, clave y fichas. |
| `ProductSwitch` | IPR-4 / IPR-5 con su universo (306 / 303). |
| `ActiveChips` | Fichas de los filtros puestos, con «×» carmín. |
| `MapFrame` + `ExplorerMap` + `LocatorMap` | Marco del mapa, flecha de norte, leyenda y cromo de MapLibre. |
| `CategoryScale` · `CategorySwatch` | Escala de quintiles y cuadro de categoría. |
| `TopTen` · `MunicipalityPanel` | Los dos estados excluyentes de la columna lateral. |
| `RelationTable` | Relación completa, ordenable, con cabecera fija. |
| `FactorTable` · `DotPlot` · `LineChart` | Cuadro de factores, comparación con el entorno y serie histórica (SVG propio). |
| `Cartouche` · `CartoucheStrip` | Cajetín completo y franja. |
| `Status` | Estados de carga y error como una línea de texto. |

`components/Chart.tsx` conserva los dos gráficos de ECharts (`ComparisonChart`
y `ProspectiveScatterChart`) con los tokens aplicados.

## Frase de lectura

Cada vista abre con una frase **calculada con las filas visibles**, sin
interpretarlas. La del explorador está en `lib/reading.ts`:

```
sin filas          → "Ningún municipio cumple los filtros."
menos de 10        → "N municipios cumplen los filtros."
si no              → cuenta los 10 primeros por comunidad (o provincia si hay
                     comunidad filtrada) y toma la más frecuente:
  se repite ≥ 2    → "5 de los 10 municipios con más presión están en Andalucía."
  si no            → "Los 10 municipios con más presión se reparten entre N comunidades."
```

Las demás páginas siguen la misma regla: un recuento o una comparación directa
de lo que hay a la vista. Nunca texto valorativo ni métricas que no vengan de
la API.

## Honestidad de los datos

- El IPR-4 cubre **306** municipios; el IPR-5, **303**.
- Cádiz, San Fernando y Getxo no tienen IPR-5: se muestran como «—» y con el
  aviso correspondiente, **nunca como cero**.
- El IPR-5 **no** es una evolución temporal del IPR-4: añade un factor de
  riesgo futuro a la misma base de 2023.
- El percentil se trunca, nunca se redondea a 100.

## Accesibilidad

- Contraste AA en todo texto. Foco visible: contorno de 2 px carmín separado
  2 px, declarado una sola vez en `app/(app)/base.css`.
- Las pestañas de capa son un `radiogroup` que se recorre con flechas.
- El mapa tiene equivalente por teclado: la lista «Elegir municipio en lista»
  y la vista «Relación».
- Todos los controles tienen etiqueta accesible, oculta con `.visually-hidden`
  cuando hace falta (anclada a `top: 0; left: 0` para no desbordar).
- Ninguna página desborda en horizontal entre 320 y 1920 px. Las tablas anchas
  se desplazan dentro de su contenedor.

## Redacción

- En español, en segunda persona, frases cortas.
- Los nombres son los que reconoce un vecino: «Dificultad para pagar»,
  «Viviendas turísticas», «Desplazamiento vecinal».
- Los códigos acompañan al nombre, no lo sustituyen: «Situación actual · IPR-4».
- Botones con verbo y resultado: «Abrir la hoja del municipio», «Quitar
  filtros», «Listo».
- Errores que dicen qué pasó y qué hacer: «No se han podido cargar los datos.
  Reintentar».
- Prohibido el lenguaje valorativo o alarmista.

## Qué no hacer

- No volver a apilar pestañas, filtros, lista, ficha y cajetín a la vez.
- No usar el carmín como fondo de grandes superficies.
- No usar mayúsculas espaciadas en navegación, pestañas, botones ni párrafos.
- No usar monoespaciada para puntuaciones destacadas.
- No añadir esquinas redondeadas, sombras difusas, degradados ni iconos
  decorativos.
- No numerar secciones salvo el puesto real de un municipio.

## Estructura

```
apps/web/
  tokens.css                  ← todos los tokens
  app/(app)/base.css          ← reinicio mínimo y elementos base
  app/(app)/layout.tsx        ← Sheet + Masthead
  app/(app)/<ruta>/page.tsx   ← cada página con su *.module.css
  app/not-found.tsx           ← 404 dentro de la hoja
  components/hoja/            ← componentes del sistema
  lib/format.ts               ← rótulos, cifras y topónimos
  lib/reading.ts              ← frase de lectura del explorador
  lib/useExplorer.ts          ← estado del explorador (la URL manda)
  lib/fonts.ts · mapTheme.ts · chartTheme.ts
```

Los cuatro prototipos funcionales y la galería de direcciones anteriores se
retiraron al implantar el diseño; siguen en el historial de git.
