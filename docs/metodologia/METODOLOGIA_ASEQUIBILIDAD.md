# Capa de asequibilidad

## Fuentes y unidad de análisis

- **Renta:** renta neta media anual por hogar del Atlas de distribución de
  renta de los hogares del INE, tabla nacional 30824, serie 2015–2023.
- **Precio:** valor tasado de vivienda libre del Ministerio de Vivienda,
  expresado en euros por metro cuadrado.
- **Clave:** código INE de municipio de cinco dígitos y año.

La descarga del Atlas incluye municipios, distritos y secciones censales. La
ingesta selecciona exclusivamente las filas municipales (distrito y sección
vacíos) y valida todos sus códigos contra el callejero oficial procesado por
`01_municipios.py`.

## Construcción del indicador

Para cada municipio y año, los valores trimestrales de precio se agregan
mediante una media ponderada por el número de tasaciones. Si los pesos no están
disponibles se usa la media simple. El coste representativo de adquisición es:

```
precio_vivienda = precio_m2_anual × 90 m²
```

Y el esfuerzo o ratio de asequibilidad:

```
ratio_asequibilidad = precio_vivienda / renta_neta_media_anual_hogar
```

El resultado se interpreta como el número de rentas anuales netas de un hogar
necesarias para adquirir una vivienda representativa de 90 m². No representa
una cuota hipotecaria ni incorpora entrada, intereses, impuestos o patrimonio.
La superficie es un parámetro reproducible y se puede cambiar mediante
`--superficie-m2`.

## Normalización

Se usa el **percentil invertido por año**, en una escala de 0 a 100:

- 100: mayor asequibilidad relativa (ratio más bajo).
- 0: menor asequibilidad relativa (ratio más alto).

Formalmente, para cada año: `100 × (n − rango) / (n − 1)`, donde el rango
ascendente 1 corresponde al ratio más bajo. Los empates reciben el rango medio.

La elección es robusta frente a municipios con precios extremos y no presupone
una distribución normal. Se conserva el ratio original, lo que permite probar
posteriormente Min–Max o z-score sin repetir la ingesta.

## Ejecución

```bash
venv/bin/python 03_renta_ine.py
venv/bin/python 04_indice_asequibilidad.py
```

Para generar y validar los CSV sin cargar PostgreSQL:

```bash
venv/bin/python 03_renta_ine.py --no-db
venv/bin/python 04_indice_asequibilidad.py --no-db
```

La conexión se configura con `DATABASE_URL` o `--db-url`. Ambas cargas usan
clave primaria `(cod_ine, anio)` y `ON CONFLICT`, por lo que son idempotentes.
