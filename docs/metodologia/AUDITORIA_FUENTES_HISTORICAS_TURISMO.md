# Auditoría de fuentes históricas para presión turística

## Conclusión

No se ha identificado una fuente que prolongue hacia atrás la capa VUT del INE
con el mismo constructo, cobertura nacional 306/306, granularidad municipal y
trazabilidad reproducible. La serie oficial utilizada —viviendas turísticas del
INE, tabla 39363— comienza en agosto de 2020. Sustituirla por plazas hoteleras,
pernoctaciones o actividad de plataformas produciría otra capa, no una
continuación homogénea.

## Comprobaciones realizadas

### INE: viviendas turísticas

La [tabla 39363](https://www.ine.es/jaxiT3/Tabla.htm?t=39363) publica snapshots
desde agosto de 2020. El fichero descargado se cruzó por código INE con el
universo del TFM: los 13 snapshots entre 2020-08 y 2026-05 contienen 306/306
municipios y valores válidos. Es la única alternativa revisada que coincide con
el constructo y el universo principal.

### INE: encuestas de ocupación

Las tablas de puntos turísticos tienen historia larga, pero solo publican
municipios seleccionados en los que la oferta turística es significativa. La
[metodología de la EOH](https://www.ine.es/daco/daco42/ocuphotel/notaeoh.htm)
confirma esa selección.

- Hoteles, [tabla 2076](https://www.ine.es/jaxiT3/Tabla.htm?t=2076):
  94 de los 306 municipios, con datos desde 2005.
- Apartamentos, [tabla 2083](https://www.ine.es/jaxiT3/Tabla.htm?t=2083):
  57 municipios del universo.
- Campings, [tabla 2085](https://www.ine.es/jaxiT3/Tabla.htm?t=2085):
  18 municipios.
- La unión de hoteles, apartamentos, campings y puntos de turismo rural alcanza
  111/306, no 306/306.

Estas fuentes miden alojamiento reglado convencional. Una ausencia de punto
turístico no significa presión cero.

### INE: Indicadores Urbanos

La [tabla 69335](https://www.ine.es/jaxiT3/Tabla.htm?t=69335) contiene filas para
los 306 municipios del TFM entre 2010 y 2024, pero muchos valores están
suprimidos o no publicados. La cobertura válida observada es:

| Año | Pernoctaciones | Plazas |
|---:|---:|---:|
| 2010–2013 | 57 | 57 |
| 2014 | 57 | 55 |
| 2015 | 60 | 60 |
| 2016 | 63 | 63 |
| 2017 | 64 | 64 |
| 2018 | 63 | 63 |
| 2019–2021 | 68 | 68 |
| 2022 | 94 | 94 |
| 2023 | 132 | 132 |
| 2024 | 129 | 129 |

El panel válido estable es de 50 municipios para pernoctaciones y 48 para
plazas en 2010–2024. Cruzado con las otras tres capas, el máximo panel estable
2018–2023 es de 57 municipios. Además, la
[metodología](https://www.ine.es/metodologia/iu/metodologia_IU.pdf) agrega
hoteles, apartamentos, alojamientos rurales y campings, y presenta un cambio
de composición en 2015. Es útil como sensibilidad de intensidad turística, no
como sustituto de VUT.

### Eurostat: plataformas de alquiler de corta estancia

Eurostat publica noches y estancias reservadas mediante plataformas desde
2018. La [nota metodológica](https://ec.europa.eu/eurostat/documents/7894008/12961561/CETOUR-Methodological-note.pdf/1dee049f-5612-1b47-c7ce-75eacaf49790)
limita la difusión municipal a ciudades seleccionadas y señala que la capacidad
o número de anuncios no formó parte de la primera publicación.

El listado oficial vigente contiene 39 ciudades españolas seleccionadas,
formadas por 155 LAU; 95 de esos componentes pertenecen al universo del TFM.
Los valores se publican para la ciudad agregada, por lo que no pueden asignarse
a cada municipio componente. Mide demanda realizada, no stock residencial.

### Inside Airbnb

[Inside Airbnb](https://insideairbnb.com/get-the-data/) publica datos abiertos
para áreas concretas, no un panel nacional de 306 municipios. Su
[política](https://insideairbnb.com/data-policies/) limita la descarga pública
ordinaria al último año y somete los archivos históricos a solicitud. Sus
[supuestos](https://insideairbnb.com/data-assumptions/) explican que ocupación e
ingresos son estimados y que un calendario bloqueado no equivale necesariamente
a una reserva. Sin obtener y auditar un extracto nacional, no puede afirmarse
que cubra el panel requerido.

### AirDNA

[AirDNA](https://www.airdna.co/how-it-works) declara datos desde 2015 y cambios
de modelo en 2018, 2019, 2023 y 2025. El acceso a su
[API empresarial](https://docs.airdna.co/) requiere credenciales comerciales.
No se ha podido verificar con datos descargables la cobertura histórica exacta
de los 306 municipios, la estabilidad retrospectiva ni una licencia
reproducible para el TFM. Se considera una vía comercial pendiente, no una
fuente validada.

### Registros autonómicos

Se comprobaron ejemplos oficiales de
[Castilla y León](https://datos.gob.es/es/catalogo/a07002862-registro-de-viviendas-de-uso-turistico1),
[Canarias](https://datos.gob.es/es/catalogo/a05003638-establecimientos-extrahoteleros-de-tipologia-vivienda-vacacional-inscritos-en-el-registro-general-turistico-de-canarias1),
[Cataluña](https://datos.gob.es/es/catalogo/a09002970-establecimientos-de-alojamiento-turistico-inscritos-en-el-registro-de-turismo-de-catalunya)
y la
[Comunitat Valenciana](https://datos.gob.es/es/catalogo/a10002983-datos-de-turismo-sobre-viviendas-de-uso-turistico-en-la-comunitat-valenciana).
Son registros administrativos actuales, con definiciones, fechas de comienzo y
campos distintos. Algunos no incluyen fecha de alta; cuando la incluyen, el
snapshot actual no permite reconstruir bajas históricas. Canarias sí publica
una [estadística municipal mensual desde 2019](https://datos.gob.es/es/catalogo/a05003423-viviendas-vacacionales-plazas-tasas-de-ocupacion-estancia-media-e-ingresos-islas-y-municipios-de-canarias-por-periodos),
pero solo puede cubrir como máximo los 19 municipios canarios del universo.

El Registro Único estatal regulado en
[2024](https://www.boe.es/eli/es/rd/2024/12/23/1312) tiene efectos desde 2025 y
no aporta una serie retrospectiva anterior a 2020.

## Decisión

1. Mantener VUT-INE y 2023 como base principal 306/306.
2. Usar agosto como corte turístico fijo para comparaciones 2020–2023.
3. Permitir como sensibilidad un panel fijo de 284 municipios en 2020–2023,
   recalculando todas las capas sobre ese universo.
4. No fusionar registros autonómicos ni imputar municipios no publicados.
5. Si se desea explorar 2018–2023, etiquetar el panel de 57 municipios basado
   en Indicadores Urbanos como otro constructo y no como índice principal.
