# Capa de presión especulativa y financiarización residencial

## Alcance

La capa no identifica compras de fondos concretos. Los datos públicos no
permiten hacerlo de forma homogénea a escala municipal. Mide señales
compatibles con presión especulativa: intensidad de compraventas, aceleración
del precio y desacoplamiento entre precio y renta.

## Score nacional

El score principal usa tres indicadores disponibles para los 306 municipios:

1. **Tasa de rotación**: compraventas anuales / viviendas familiares
   convencionales del Censo 2021 × 100. El parque 2021 es un denominador fijo;
   permite comparación transversal, pero no representa altas y bajas anuales
   del parque.
2. **Aceleración del precio**: diferencia entre el crecimiento anual del precio
   tasado y el crecimiento del año anterior.
3. **Desacoplamiento precio-renta**: crecimiento anual del precio menos
   crecimiento anual de la renta neta media por hogar.

Cada variable se transforma en percentil anual 0–100. El score es la media
simple de los tres percentiles. Se usan pesos iguales para evitar una falsa
precisión antes de validar empíricamente pesos alternativos.

La robustez se contrasta con escenarios que asignan un 50 % a cada componente
por separado y un 25 % a los otros dos. Se publican correlación de Spearman,
cambios de rango y solapamiento del decil superior. Las correlaciones internas
se guardan por año para detectar redundancia.

Con las fuentes disponibles, los años completos son 2022 y 2023. La renta
municipal termina en 2023 y la aceleración exige dos variaciones consecutivas.
No se imputa ningún valor suprimido.

## Titularidad corporativa complementaria

El Catastro publica inmuebles residenciales por tipo fiscal. Se calcula:

`inmuebles de sociedades / inmuebles residenciales totales × 100`

El indicador representa propiedad societaria, no fondos de inversión ni
especulación probada. Incluye sociedades anónimas, limitadas, colectivas,
comanditarias, cooperativas y civiles.

La Dirección General del Catastro no cubre Navarra ni País Vasco. En el
universo del TFM quedan fuera 17 municipios, por lo que esta variable se
almacena y analiza como complemento (289/306) y no entra en el score nacional.
Los CSV homogéneos por tipo fiscal están disponibles para 2024 y 2025.

## Fuentes y límites

- MIVAU, tabla 2 de transacciones municipales: actividad notarial trimestral
  desde 2004. El año en curso se excluye hasta disponer de cuatro trimestres.
- INE, Censo 2021, tabla 59525: parque residencial municipal para el
  denominador de rotación.
- Ministerio de Vivienda: valor tasado ya integrado en el proyecto.
- INE, Atlas de renta: renta neta media por hogar ya integrada.
- Dirección General del Catastro: titularidad complementaria; territorio de
  régimen fiscal común.

El score detecta presión compatible con dinámica especulativa, pero no establece
causalidad ni identifica al comprador. Una rotación alta también puede responder
a movilidad residencial ordinaria y una aceleración de precios puede tener
causas de oferta o demanda no especulativas.
