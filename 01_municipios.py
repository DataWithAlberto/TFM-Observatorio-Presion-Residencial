import pandas as pd
import argparse
import unicodedata
from pathlib import Path

from reproducibilidad.descargas import record_download
from utils_http import session_with_retries

RAW_DIR = Path("data/raw/ine_municipios")
RAW_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = Path("data/processed/municipios_ine.csv")
OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

URL_INE = "https://www.ine.es/daco/daco42/codmun/diccionario25.xlsx"
RAW_FILE = RAW_DIR / "municipios_ine.xlsx"

PROVINCIAS_INE = {
    '01': 'Araba/Álava', '02': 'Albacete', '03': 'Alicante/Alacant', '04': 'Almería',
    '05': 'Ávila', '06': 'Badajoz', '07': 'Balears, Illes', '08': 'Barcelona', '09': 'Burgos',
    '10': 'Cáceres', '11': 'Cádiz', '12': 'Castellón/Castelló', '13': 'Ciudad Real',
    '14': 'Córdoba', '15': 'Coruña, A', '16': 'Cuenca', '17': 'Girona', '18': 'Granada',
    '19': 'Guadalajara', '20': 'Gipuzkoa', '21': 'Huelva', '22': 'Huesca', '23': 'Jaén',
    '24': 'León', '25': 'Lleida', '26': 'Rioja, La', '27': 'Lugo', '28': 'Madrid',
    '29': 'Málaga', '30': 'Murcia', '31': 'Navarra', '32': 'Ourense', '33': 'Asturias',
    '34': 'Palencia', '35': 'Palmas, Las', '36': 'Pontevedra', '37': 'Salamanca',
    '38': 'Santa Cruz de Tenerife', '39': 'Cantabria', '40': 'Segovia', '41': 'Sevilla',
    '42': 'Soria', '43': 'Tarragona', '44': 'Teruel', '45': 'Toledo', '46': 'Valencia/València',
    '47': 'Valladolid', '48': 'Bizkaia', '49': 'Zamora', '50': 'Zaragoza',
    '51': 'Ceuta', '52': 'Melilla',
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

def descarga_ine():
    resp = session_with_retries().get(URL_INE, timeout=30)
    resp.raise_for_status()
    RAW_FILE.write_bytes(resp.content)
    record_download(
        RAW_FILE, URL_INE, payload=resp.content,
        organism="Instituto Nacional de Estadística",
        resource="Relación de municipios y códigos, diccionario 2025",
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
    )
    print(f"Descargado: {RAW_FILE} ({len(resp.content)} bytes)")

def procesa():
    df = pd.read_excel(RAW_FILE, sheet_name="dic25", header=None, skiprows=2)
    df.columns = ['codauto', 'cpro', 'cmun', 'dc', 'nombre']

    df['cpro'] = df['cpro'].astype(str).str.zfill(2)
    df['cmun'] = df['cmun'].astype(str).str.zfill(3)
    df['id_municipio'] = df['cpro'] + df['cmun']

    df['provincia'] = df['cpro'].map(PROVINCIAS_INE)
    df['provincia_norm'] = df['provincia'].apply(normaliza_texto)
    df['municipio_norm'] = df['nombre'].apply(normaliza_texto)

    sin_provincia = df[df['provincia'].isna()]
    if len(sin_provincia) > 0:
        print("AVISO: códigos de provincia sin mapear:", sin_provincia['cpro'].unique())

    df_final = df[['id_municipio', 'cpro', 'cmun', 'nombre', 'provincia',
                    'provincia_norm', 'municipio_norm']]
    df_final.to_csv(OUT_FILE, index=False)

    print(f"Total municipios en España: {len(df_final)}")
    print(f"Provincias únicas: {df_final['provincia'].nunique()}")
    print(f"Guardado: {OUT_FILE}")
    return df_final

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true",
                        help="Vuelve a descargar aunque el fichero ya esté")
    args = parser.parse_args()
    if args.force_download or not RAW_FILE.exists():
        descarga_ine()
    procesa()