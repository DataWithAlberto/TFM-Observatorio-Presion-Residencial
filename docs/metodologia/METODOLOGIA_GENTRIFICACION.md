# Capa de riesgo de gentrificación y transformación socioeconómica

## Definición

La capa mide transformaciones municipales compatibles con procesos de
gentrificación. No clasifica municipios como «gentrificados», no observa
desplazamientos individuales y no establece causalidad.

La versión 2.0 genera una serie anual 2018–2023 mediante ventanas móviles de
tres años. Prioriza datos observados: no imputa precios municipales con
variaciones provinciales ni convierte la ausencia de datos en valor cero.

## Componentes del score principal

1. **Cambio socioeconómico:** cambio logarítmico trianual de la renta neta
   media por persona del Atlas de Renta del INE.
2. **Presión residencial:** crecimiento logarítmico trianual del precio tasado
   menos el crecimiento de la renta por persona.
3. **Transformación de hogares:** aumento trianual de hogares unipersonales
   residualizado mediante una regresión anual contra los cambios en población
   mayor de 65 años y menor de 18 años. Así se descuenta la parte atribuible a
   envejecimiento y estructura por edades.

Cada componente se winsoriza en los percentiles 1 y 99 y se transforma a un
percentil anual 0–100. El score v2.0 es la media con pesos iguales.

## Cobertura temporal

| Año | Municipios | Cobertura |
|---:|---:|---:|
| 2018 | 280 | 91,5 % |
| 2019 | 283 | 92,5 % |
| 2020 | 284 | 92,8 % |
| 2021 | 284 | 92,8 % |
| 2022 | 284 | 92,8 % |
| 2023 | 306 | 100,0 % |

El Atlas cubre 2015–2023. La ventana trianual sitúa el primer score en 2018.
La pérdida de cobertura anterior a 2023 procede del valor tasado municipal del
Ministerio: algunos municipios que hoy forman parte de la muestra no estaban
publicados en años anteriores.

Se usa un panel observado anual con cobertura mínima del 90 %. El CSV registra
el tamaño del universo de normalización y si el año alcanza 306/306. Los
percentiles de distintos años deben compararse teniendo presente el cambio de
universo.

## Variables de contraste

- Cambio en población por debajo del 60 % y por encima del 200 % de la mediana.
- Índice de Gini y ratio P80/P20.
- Edad media, menores de 18, mayores de 65 y tamaño medio del hogar.
- Saldo migratorio interior desde 2021.
- Scores turístico y especulativo, sin incorporarlos para evitar doble conteo
  en el índice compuesto general.

La composición de renta tiene pequeñas supresiones oficiales antes de 2021 y
se excluye del score principal. No se imputa.

## Validación

La correlación Spearman del score con la sustitución observada de composición
de renta es positiva en todos los años y se sitúa entre 0,33 y 0,57. Esto apoya
la interpretación del indicador sin usar esa variable incompleta para
construirlo.

El saldo migratorio interior presenta correlación de −0,20 en 2023. Por tanto,
no funciona como proxy nacional directo de desplazamiento residencial y queda
correctamente relegado a contraste.

Las correlaciones máximas entre componentes son 0,25–0,55, por debajo del
umbral de redundancia 0,90. El PCA se conserva como contraste y no sustituye la
interpretación causal de los componentes.

Los escenarios alternativos de peso muestran correlaciones de 0,76–0,86 con el
score base. El ranking debe mostrarse acompañado de componentes y sensibilidad,
especialmente en el decil superior.

## Limitaciones

- La serie no puede extenderse de forma homogénea a 2005 sin imputar renta,
  hogares y precios municipales.
- La transformación de hogares es una señal compatible, no prueba de
  sustitución social.
- La renta media puede estar influida por valores altos; la winsorización limita
  su efecto, pero no lo elimina conceptualmente.
- La unidad municipal oculta diferencias entre barrios.
- La pandemia afecta varias ventanas trianuales y debe mencionarse al
  interpretar 2020–2022.

## Interpretación

Un valor alto señala coincidencia relativa de mejora de renta, precios creciendo
por encima de la renta y aumento de hogares unipersonales no explicado por la
estructura de edades. Es un indicador comparativo anual, no un umbral absoluto
ni una declaración de gentrificación observada.
