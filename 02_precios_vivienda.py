import pandas as pd
import argparse
import re
import unicodedata
from pathlib import Path

from reproducibilidad.descargas import record_download
from utils_http import session_with_retries

RAW_DIR = Path("data/raw/ministerio_vivienda")
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

URL_MINISTERIO = "https://apps.fomento.gob.es/boletinonline2/sedal/35103500.XLS"
RAW_FILE = RAW_DIR / "valor_tasado_municipios_25000hab.xls"
MUNICIPIOS_FILE = PROCESSED_DIR / "municipios_ine.csv"
OUT_FILE = PROCESSED_DIR / "precios_vivienda_ministerio_final.csv"

# ============================================================
# DICCIONARIOS DE CORRECCIÓN — construidos y verificados
# manualmente contra el crudo del Excel del Ministerio y el
# callejero oficial del INE. Ver notas inline sobre el origen
# de cada corrección para la sección de limitaciones del TFM.
# ============================================================

# Correcciones de PROVINCIA aplicables a todas las filas de esa provincia_norm
# (celdas partidas en el Excel original, typos, o simple convención de
# nomenclatura bilingüe distinta a la usada por el INE)
MAPEO_PROVINCIAS = {
    'ALICANTE': 'ALICANTE/ALACANT',
    'VALENCIA': 'VALENCIA/VALENCIA',
    'ILLES BALEARS': 'BALEARS, ILLES',
    'LA CORUNA': 'CORUNA, A',
    'LA RIOJA': 'RIOJA, LA',
    'LAS PALMAS': 'PALMAS, LAS',
    'CORDABA': 'CORDOBA',                        # typo confirmado en fuente
    'VALLADODID': 'VALLADOLID',                   # typo confirmado en fuente
    'SANTA CRUZ DE': 'SANTA CRUZ DE TENERIFE',     # celda partida en el Excel origen
    'TENERIFE': 'SANTA CRUZ DE TENERIFE',          # celda partida en el Excel origen
}

# Correcciones de provincia para FILAS CONCRETAS — errores reales de la
# fuente donde el municipio está asignado a una provincia a la que
# geográficamente no pertenece. Verificado uno a uno contra el dato crudo.
CORRECCIONES_FILA = [
    # (provincia_norm_en_fuente, municipio_norm, provincia_norm_correcta)
    ('CACERES', 'AMES', 'CORUNA, A'),
    ('CUENCA', 'AZUQUECA DE HENARES', 'GUADALAJARA'),
    ('CORDOBA', 'ALMUNECAR', 'GRANADA'),
    ('OURENSE', 'CANGAS', 'PONTEVEDRA'),
    ('ALICANTE/ALACANT', 'ALMAZORA/ALMASSORA', 'CASTELLON/CASTELLO'),
    ('ALICANTE/ALACANT', 'BENICARLO', 'CASTELLON/CASTELLO'),
    ('GUADALAJARA', 'ILLESCAS', 'TOLEDO'),
]

# Typos/espacios puntuales de MUNICIPIO detectados en la fuente
MAPEO_MUNICIPIOS_TYPOS = {
    'SANTA CRUZ DETENERIFE': 'SANTA CRUZ DE TENERIFE',  # espacio perdido en fuente
}

# Diccionario final de municipios: bilingües con orden distinto al INE,
# nombres oficiales que han cambiado, artículo ausente en la fuente,
# y casos especiales de nomenclatura bilingüe con artículo intercalado.
# Verificado contra el callejero oficial del INE (municipios_ine.csv).
MAPEO_MUNICIPIOS_FINAL = {
    'ALCOY/ALCOI': 'ALCOI/ALCOY',
    'ALICANTE/ALACANT': 'ALACANT/ALICANTE',
    'CALPE/CALP': 'CALP',
    'ELCHE/ELX': 'ELX/ELCHE',
    'JAVEA/XABIA': 'XABIA/JAVEA',
    'SAN VICENTE DEL RASPEIG': "SANT VICENT DEL RASPEIG/SAN VICENTE DEL RASPEIG",
    'VITORIA': 'VITORIA-GASTEIZ',
    "HOSPITALET DE LLOBREGAT (L')": "HOSPITALET DE LLOBREGAT, L'",
    'EL PRAT DE LLOBREGAT': 'PRAT DE LLOBREGAT, EL',
    'SANTA COLOMA GRAMANET': 'SANTA COLOMA DE GRAMENET',
    'PUERTO DE SANTA MARIA': 'PUERTO DE SANTA MARIA, EL',
    'BURRIANA': 'BORRIANA/BURRIANA',
    'CASTELLON DE LA PLANA': 'CASTELLO DE LA PLANA/CASTELLON DE LA PLANA',
    "LA VALL D'UIXO": "VALL D'UIXO, LA",
    'VILLARREAL/VILA-REAL': 'VILA-REAL',
    'MAHON': 'MAO',
    'SANTA EULALIA DEL RIO': 'SANTA EULARIA DES RIU',
    'CORUNA (A)': 'CORUNA, A',
    'VELEZ MALAGA': 'VELEZ-MALAGA',
    'SAN CRISTOBAL LAGUNA': 'SAN CRISTOBAL DE LA LAGUNA',
    'SAGUNTO/SAGUNT': 'SAGUNT/SAGUNTO',
    'SAN SEBASTIAN/DONOSTIA': 'DONOSTIA/SAN SEBASTIAN',
    'PALMA DE MALLORCA': 'PALMA',
    'VILLAJOYOSA/VILA JOIOSA, LA': 'VILA JOIOSA, LA/VILLAJOYOSA',
    'ALMAZORA/ALMASSORA': 'ALMASSORA',
}


def normaliza_texto(s):
    if pd.isna(s):
        return None
    s = str(s).strip()
    if s == '':
        return None
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('utf-8')
    s = ' '.join(s.split())  # colapsa espacios múltiples
    return s.upper()


def normaliza_articulo(nombre):
    """Convierte artículos al formato INE 'Nombre, Articulo'.
    Maneja tanto sufijo '(La)' como prefijo 'La ...'."""
    if pd.isna(nombre):
        return nombre
    m = re.match(r'^(.+?)\s*\((EL|LA|LOS|LAS)\)$', nombre)
    if m:
        cuerpo, articulo = m.groups()
        return f"{cuerpo}, {articulo}"
    m2 = re.match(r'^(EL|LA|LOS|LAS)\s+(.+)$', nombre)
    if m2:
        articulo, cuerpo = m2.groups()
        return f"{cuerpo}, {articulo}"
    return nombre


def descarga_ministerio():
    resp = session_with_retries().get(URL_MINISTERIO, timeout=30)
    resp.raise_for_status()
    RAW_FILE.write_bytes(resp.content)
    record_download(
        RAW_FILE, URL_MINISTERIO, payload=resp.content,
        organism="Ministerio de Transportes y Movilidad Sostenible",
        resource="Valor tasado de la vivienda, boletín estadístico 35103500",
        license_url="https://sede.transportes.gob.es/aviso-legal",
    )
    print(f"Descargado: {RAW_FILE} ({len(resp.content)} bytes)")


def parsea_hoja(xls, nombre_hoja):
    nombre_limpio = nombre_hoja.strip()
    m = re.match(r"T(\d)A(\d{4})", nombre_limpio)
    if not m:
        print(f"AVISO: hoja '{nombre_hoja}' no matchea patrón trimestre, se omite")
        return None
    trimestre, anio = int(m.group(1)), int(m.group(2))
    mes_inicio = {1: 1, 2: 4, 3: 7, 4: 10}[trimestre]
    fecha = pd.Timestamp(year=anio, month=mes_inicio, day=1)

    df = pd.read_excel(xls, sheet_name=nombre_hoja, header=None)

    fila_cabecera = None
    for i in range(min(20, len(df))):
        if str(df.iloc[i, 1]).strip() == "Provincia":
            fila_cabecera = i
            break
    if fila_cabecera is None:
        print(f"AVISO: no se encontró cabecera 'Provincia' en {nombre_hoja}, se omite")
        return None

    formato_antiguo = df.shape[1] <= 6  # 2005-2009: 6 columnas; 2010+: 10 columnas
    inicio_datos = fila_cabecera + (2 if formato_antiguo else 3)
    datos = df.iloc[inicio_datos:].copy()
    datos = datos.dropna(how='all')

    if formato_antiguo:
        datos.columns = ['_', 'provincia', 'municipio', 'valor_total', '_2', 'num_tasaciones']
        datos['valor_5menos'] = None
        datos['valor_5mas'] = None
    else:
        datos.columns = ['_', 'provincia', 'municipio', 'valor_5menos', 'valor_5mas',
                          'valor_total', '_2', 'tas_5menos', 'tas_5mas', 'num_tasaciones']

    datos = datos[datos['municipio'].notna()].copy()
    datos = datos[datos['municipio'].astype(str).str.strip() != ''].copy()

    # Celdas vacías (no NaN) en provincia -> NaN real antes del ffill
    datos['provincia'] = datos['provincia'].replace(r'^\s*$', pd.NA, regex=True)
    datos['provincia'] = datos['provincia'].ffill()

    for col in ['valor_total', 'valor_5menos', 'valor_5mas', 'num_tasaciones']:
        datos[col] = pd.to_numeric(datos[col].replace('n.r', pd.NA), errors='coerce')

    datos['fecha'] = fecha
    datos['provincia_norm'] = datos['provincia'].apply(normaliza_texto)
    datos['municipio_norm'] = datos['municipio'].apply(normaliza_texto)

    return datos[['fecha', 'provincia', 'municipio', 'provincia_norm', 'municipio_norm',
                   'valor_total', 'valor_5menos', 'valor_5mas', 'num_tasaciones']]


def procesa():
    xls = pd.ExcelFile(RAW_FILE)
    resultados = [r for hoja in xls.sheet_names if (r := parsea_hoja(xls, hoja)) is not None]
    precios = pd.concat(resultados, ignore_index=True)

    # --- Aplicar correcciones ---
    precios['provincia_norm'] = precios['provincia_norm'].replace(MAPEO_PROVINCIAS)

    for prov_mal, muni, prov_bien in CORRECCIONES_FILA:
        mask = (precios['provincia_norm'] == prov_mal) & (precios['municipio_norm'] == muni)
        precios.loc[mask, 'provincia_norm'] = prov_bien

    precios['municipio_norm'] = precios['municipio_norm'].replace(MAPEO_MUNICIPIOS_TYPOS)
    precios['municipio_norm'] = precios['municipio_norm'].apply(normaliza_articulo)
    precios['municipio_norm'] = precios['municipio_norm'].replace(MAPEO_MUNICIPIOS_FINAL)

    precios = precios.sort_values(['provincia_norm', 'municipio_norm', 'fecha'])

    # --- Cruce contra municipios INE ---
    municipios = pd.read_csv(MUNICIPIOS_FILE)
    municipios['id_municipio'] = municipios['id_municipio'].astype(str).str.zfill(5)

    precios_final = precios.merge(
        municipios[['provincia_norm', 'municipio_norm', 'id_municipio']],
        on=['provincia_norm', 'municipio_norm'], how='left',
        validate='many_to_one',
    )

    sin_cruce = precios_final[precios_final['id_municipio'].isna()][
        ['provincia_norm', 'municipio_norm']
    ].drop_duplicates()

    print(f"Filas totales: {len(precios_final)}")
    print(f"Filas con id_municipio asignado: {precios_final['id_municipio'].notna().sum()}")
    print(f"Municipios únicos con id asignado: "
          f"{precios_final[precios_final['id_municipio'].notna()]['id_municipio'].nunique()}")
    print(f"Municipios sin cruce: {len(sin_cruce)}")
    if len(sin_cruce) > 0:
        raise ValueError(
            f"{len(sin_cruce)} municipios del Ministerio no cruzan con el "
            f"callejero INE (provincia_norm, municipio_norm):\n"
            f"{sin_cruce.to_string()}"
        )

    precios_final.to_csv(OUT_FILE, index=False)
    print(f"\nGuardado: {OUT_FILE}")
    return precios_final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true",
                        help="Vuelve a descargar aunque el fichero ya esté")
    args = parser.parse_args()
    if args.force_download or not RAW_FILE.exists():
        descarga_ministerio()
    procesa()