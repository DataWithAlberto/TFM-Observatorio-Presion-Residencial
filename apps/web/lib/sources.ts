/**
 * Procedencia de los datos publicados.
 *
 * Cada entrada nombra el organismo, el recurso concreto del que sale el dato y
 * el aviso legal que fija sus condiciones de reutilización. Se cita el recurso,
 * no la portada del organismo: una atribución que no permite llegar al fichero
 * usado no deja comprobar nada.
 *
 * Las condiciones se enlazan tal como las publica cada organismo. Solo se
 * nombra una licencia concreta donde el propio aviso legal la nombra; en el
 * resto se remite a sus condiciones, que no son equivalentes entre sí.
 */
export type DataSource = {
  organismo: string;
  recurso: string;
  aporta: string;
  /** Enlace al recurso concreto, cuando es accesible de forma directa. */
  url?: string;
  condiciones: string;
  condicionesUrl: string;
};

export const DATA_SOURCES: DataSource[] = [
  {
    organismo: "Instituto Nacional de Estadística",
    recurso: "Relación de municipios y códigos, diccionario 2025",
    aporta: "Universo municipal y códigos INE",
    url: "https://www.ine.es/daco/daco42/codmun/diccionario25.xlsx",
    condiciones: "Aviso legal del INE · CC BY 4.0 con atribución",
    condicionesUrl: "https://www.ine.es/dyngs/AYU/index.htm?cid=125",
  },
  {
    organismo: "Instituto Nacional de Estadística",
    recurso: "Atlas de distribución de renta de los hogares, tablas 30824, 30829, 30832 y 37677",
    aporta: "Renta de los hogares para la asequibilidad y la gentrificación",
    url: "https://www.ine.es/jaxiT3/Tabla.htm?t=30824",
    condiciones: "Aviso legal del INE · CC BY 4.0 con atribución",
    condicionesUrl: "https://www.ine.es/dyngs/AYU/index.htm?cid=125",
  },
  {
    organismo: "Instituto Nacional de Estadística",
    recurso: "Viviendas turísticas y plazas, tabla 39363",
    aporta: "Presión de las viviendas turísticas",
    url: "https://www.ine.es/jaxiT3/Tabla.htm?t=39363",
    condiciones: "Aviso legal del INE · CC BY 4.0 con atribución",
    condicionesUrl: "https://www.ine.es/dyngs/AYU/index.htm?cid=125",
  },
  {
    organismo: "Instituto Nacional de Estadística",
    recurso: "Población municipal por provincias, tablas 2854 a 2909",
    aporta: "Denominador de los indicadores por habitante",
    url: "https://www.ine.es/jaxiT3/Tabla.htm?t=2854",
    condiciones: "Aviso legal del INE · CC BY 4.0 con atribución",
    condicionesUrl: "https://www.ine.es/dyngs/AYU/index.htm?cid=125",
  },
  {
    organismo: "Instituto Nacional de Estadística",
    recurso: "Censo de población y viviendas 2021, tabla 59525",
    aporta: "Parque de vivienda y estructura de los hogares",
    url: "https://www.ine.es/jaxiT3/Tabla.htm?t=59525",
    condiciones: "Aviso legal del INE · CC BY 4.0 con atribución",
    condicionesUrl: "https://www.ine.es/dyngs/AYU/index.htm?cid=125",
  },
  {
    organismo: "Instituto Nacional de Estadística",
    recurso: "Estadística de migraciones, saldos municipales, tabla 69767",
    aporta: "Desplazamiento vecinal",
    url: "https://www.ine.es/jaxiT3/Tabla.htm?t=69767",
    condiciones: "Aviso legal del INE · CC BY 4.0 con atribución",
    condicionesUrl: "https://www.ine.es/dyngs/AYU/index.htm?cid=125",
  },
  {
    organismo: "Ministerio de Transportes y Movilidad Sostenible",
    recurso: "Valor tasado de la vivienda, boletín estadístico 35103500",
    aporta: "Precio de la vivienda para la asequibilidad",
    url: "https://apps.fomento.gob.es/boletinonline2/sedal/35103500.XLS",
    condiciones: "Condiciones generales de reutilización de la sede",
    condicionesUrl: "https://sede.transportes.gob.es/aviso-legal",
  },
  {
    organismo: "Ministerio de Transportes y Movilidad Sostenible",
    recurso: "Transacciones inmobiliarias de vivienda, boletín estadístico 34010210",
    aporta: "Rotación del mercado para las señales de especulación",
    url: "https://apps.fomento.gob.es/BoletinOnline2/sedal/34010210.XLS",
    condiciones: "Condiciones generales de reutilización de la sede",
    condicionesUrl: "https://sede.transportes.gob.es/aviso-legal",
  },
  {
    organismo: "Ministerio de Vivienda y Agenda Urbana",
    recurso: "Sistema estatal de referencia del precio del alquiler, serie VDP001",
    aporta: "Validación externa del índice frente al alquiler declarado",
    url: "https://cdn.mivau.gob.es/portal-web-mivau/Datos_MIVAU/CSV/VDP001_01.csv",
    condiciones: "Condiciones de reutilización del portal del Ministerio",
    condicionesUrl: "https://www.mivau.gob.es/el-ministerio/aviso-legal",
  },
  {
    organismo: "Dirección General del Catastro",
    recurso: "Estadísticas de titularidad de bienes inmuebles residenciales",
    aporta: "Titularidad corporativa para las señales de especulación",
    url: "https://www.catastro.hacienda.gob.es/es-ES/estadisticas_3_1.html",
    condiciones: "Condiciones de la propia estadística; no se les atribuye una licencia genérica",
    condicionesUrl: "https://www.catastro.hacienda.gob.es/es-ES/estadisticas_3_1.html",
  },
  {
    organismo: "AdapteCCa · AEMET y Oficina Española de Cambio Climático",
    recurso: "Escenarios de cambio climático CMIP6, trayectoria SSP2-4.5",
    aporta: "Riesgo futuro: clima y tendencias",
    url: "https://escenarios.adaptecca.es",
    condiciones: "Aviso legal de AdapteCCa · reutilización citando la fuente",
    condicionesUrl: "https://adaptecca.es/aviso-legal",
  },
  {
    organismo: "Centro Nacional de Información Geográfica",
    recurso: "Geometría municipal del Centro de Descargas",
    aporta: "Límites municipales del mapa",
    condiciones: "Política de datos del Centro de Descargas",
    condicionesUrl: "https://centrodedescargas.cnig.es/CentroDescargas/politica-datos",
  },
];

/** Los organismos, sin repetir, para la línea corta del pie. */
export const SOURCE_BODIES = [
  ...new Set(DATA_SOURCES.map((source) => source.organismo.split(" · ")[0])),
];
