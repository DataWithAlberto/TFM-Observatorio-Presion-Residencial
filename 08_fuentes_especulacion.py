#!/usr/bin/env python3
"""Ingesta de fuentes públicas para presión especulativa residencial.

Fuentes:
- Ministerio de Vivienda: transacciones municipales trimestrales desde 2004.
- INE, Censo 2021: parque municipal de viviendas familiares convencionales.
- Catastro: propiedad residencial por tipo fiscal (complementaria; sin País
  Vasco ni Navarra).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from reproducibilidad.descargas import record_download
from utils_http import session_with_retries

RAW_DIR = Path("data/raw/especulacion")
PROCESSED_DIR = Path("data/processed")
MUNICIPIOS_FILE = PROCESSED_DIR / "municipios_ine.csv"
MUNICIPIOS_GPKG = Path("data/raw/municipios_306_con_geometria.gpkg")
TRANSACCIONES_RAW = RAW_DIR / "transacciones_municipales_34010210.xls"
PARQUE_RAW = RAW_DIR / "parque_viviendas_ine_59525.json"
TRANSACCIONES_OUT = PROCESSED_DIR / "transacciones_vivienda_municipal.csv"
PARQUE_OUT = PROCESSED_DIR / "parque_viviendas_2021.csv"
CATASTRO_OUT = PROCESSED_DIR / "titularidad_corporativa_catastro.csv"

TRANSACCIONES_URL = (
    "https://apps.fomento.gob.es/BoletinOnline2/sedal/34010210.XLS"
)
PARQUE_URL = "https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/59525?tip=AM"
CATASTRO_URL = (
    "https://www.catastro.hacienda.gob.es/documentos/estadisticas/"
    "propietarios/{anio}/P_SPI_mun_V_TPF.csv"
)
CATASTRO_ANIOS = (2024, 2025)
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"

MAPEO_PROVINCIAS = {
    "ALICANTE": "ALICANTE/ALACANT",
    "VALENCIA": "VALENCIA/VALENCIA",
    "ILLES BALEARS": "BALEARS, ILLES",
    "LA CORUNA": "CORUNA, A",
    "CORUNA (A)": "CORUNA, A",
    "LA RIOJA": "RIOJA, LA",
    "LAS PALMAS": "PALMAS, LAS",
    "PALMAS (LAS)": "PALMAS, LAS",
    "ARABA": "ARABA/ALAVA",
    "ALAVA": "ARABA/ALAVA",
    "GIPUZKOA": "GIPUZKOA",
    "GUIPUZCOA": "GIPUZKOA",
    "BIZKAIA": "BIZKAIA",
    "VIZCAYA": "BIZKAIA",
    "NAVARRA": "NAVARRA",
    "ASTURIAS (PRINCIPADO DE)": "ASTURIAS",
    "BALEARS (ILLES)": "BALEARS, ILLES",
    "CANTABRIA": "CANTABRIA",
    "MADRID (COMUNIDAD DE)": "MADRID",
    "MURCIA (REGION DE)": "MURCIA",
    "NAVARRA (COMUNIDAD FORAL DE)": "NAVARRA",
    "RIOJA (LA)": "RIOJA, LA",
}

MAPEO_MUNICIPIOS = {
    "ALCOY/ALCOI": "ALCOI/ALCOY",
    "ALICANTE/ALACANT": "ALACANT/ALICANTE",
    "CALPE/CALP": "CALP",
    "ELCHE/ELX": "ELX/ELCHE",
    "JAVEA/XABIA": "XABIA/JAVEA",
    "SAN VICENTE DEL RASPEIG": "SANT VICENT DEL RASPEIG/SAN VICENTE DEL RASPEIG",
    "VITORIA": "VITORIA-GASTEIZ",
    "VITORIA/GASTEIZ": "VITORIA-GASTEIZ",
    "HOSPITALET DE LLOBREGAT (L')": "HOSPITALET DE LLOBREGAT, L'",
    "EL PRAT DE LLOBREGAT": "PRAT DE LLOBREGAT, EL",
    "SANTA COLOMA GRAMANET": "SANTA COLOMA DE GRAMENET",
    "PUERTO DE SANTA MARIA": "PUERTO DE SANTA MARIA, EL",
    "BURRIANA": "BORRIANA/BURRIANA",
    "CASTELLON DE LA PLANA": "CASTELLO DE LA PLANA/CASTELLON DE LA PLANA",
    "LA VALL D'UIXO": "VALL D'UIXO, LA",
    "VILLARREAL/VILA-REAL": "VILA-REAL",
    "MAHON": "MAO",
    "SANTA EULALIA DEL RIO": "SANTA EULARIA DES RIU",
    "CORUNA (A)": "CORUNA, A",
    "VELEZ MALAGA": "VELEZ-MALAGA",
    "SAN CRISTOBAL LAGUNA": "SAN CRISTOBAL DE LA LAGUNA",
    "SAGUNTO/SAGUNT": "SAGUNT/SAGUNTO",
    "SAN SEBASTIAN/DONOSTIA": "DONOSTIA/SAN SEBASTIAN",
    "PALMA DE MALLORCA": "PALMA",
    "VILLAJOYOSA/VILA JOIOSA, LA": "VILA JOIOSA, LA/VILLAJOYOSA",
    "ALMAZORA/ALMASSORA": "ALMASSORA",
    "SAN VICENTE DEL RASPEIG/SANT VICENT DEL": (
        "SANT VICENT DEL RASPEIG/SAN VICENTE DEL RASPEIG"
    ),
    "CASTELLON DE LA PLANA/CASTELLO DE LA PLA": (
        "CASTELLO DE LA PLANA/CASTELLON DE LA PLANA"
    ),
    "DONOSTIA-SAN SEBASTIAN": "DONOSTIA/SAN SEBASTIAN",
}


def normalizar(valor: object) -> str | None:
    if pd.isna(valor):
        return None
    limpio = " ".join(str(valor).strip().split())
    if not limpio:
        return None
    limpio = unicodedata.normalize("NFKD", limpio).encode("ascii", "ignore").decode()
    return limpio.upper()


def normalizar_articulo(nombre: str | None) -> str | None:
    if nombre is None:
        return None
    if coincidencia := re.match(r"^(.+?)\s*\((EL|LA|LOS|LAS)\)$", nombre):
        cuerpo, articulo = coincidencia.groups()
        return f"{cuerpo}, {articulo}"
    if coincidencia := re.match(r"^(EL|LA|LOS|LAS)\s+(.+)$", nombre):
        articulo, cuerpo = coincidencia.groups()
        return f"{cuerpo}, {articulo}"
    return nombre


def _municipios() -> pd.DataFrame:
    import geopandas as gpd

    df = pd.read_csv(MUNICIPIOS_FILE, dtype={"id_municipio": str})
    df["cod_ine"] = df["id_municipio"].str.zfill(5)
    codigos_objetivo = set(
        gpd.read_file(MUNICIPIOS_GPKG, ignore_geometry=True)["cod_ine"]
        .astype(str)
        .str.zfill(5)
    )
    salida = df[df["cod_ine"].isin(codigos_objetivo)].copy()
    if salida["cod_ine"].nunique() != 306:
        raise ValueError("El callejero no cubre exactamente los 306 municipios objetivo")
    return salida


def descargar(url: str, destino: Path, force: bool = False, verify: bool = True,
              organismo: str | None = None, recurso: str | None = None,
              licencia: str | None = None) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not force:
        print(f"Se reutiliza: {destino}")
        return destino
    temporal = destino.with_suffix(destino.suffix + ".part")
    with warnings.catch_warnings():
        if not verify:
            warnings.filterwarnings("ignore", message="Unverified HTTPS request")
        with session_with_retries().get(
            url, timeout=240, stream=True, verify=verify
        ) as respuesta:
            respuesta.raise_for_status()
            with temporal.open("wb") as fichero:
                for bloque in respuesta.iter_content(1024 * 1024):
                    if bloque:
                        fichero.write(bloque)
    if temporal.stat().st_size == 0:
        temporal.unlink()
        raise ValueError(f"Descarga vacía: {url}")
    temporal.replace(destino)
    record_download(destino, url, organism=organismo, resource=recurso,
                    license_url=licencia, tls_verified=verify)
    print(f"Descargado: {destino} ({destino.stat().st_size:,} bytes)")
    return destino


def procesar_transacciones() -> pd.DataFrame:
    bruto = pd.read_excel(TRANSACCIONES_RAW, header=None)
    cab_anios = bruto.iloc[10]
    cab_trimestres = bruto.iloc[12]
    periodos: dict[int, tuple[int, int]] = {}
    anio_actual: int | None = None
    for columna in range(3, bruto.shape[1]):
        valor_anio = cab_anios.iloc[columna]
        if pd.notna(valor_anio):
            encontrado = re.search(r"(\d{4})", str(valor_anio))
            if encontrado:
                anio_actual = int(encontrado.group(1))
        trimestre = cab_trimestres.iloc[columna]
        if anio_actual and pd.notna(trimestre):
            encontrado = re.search(r"([1-4])", str(trimestre))
            if encontrado:
                periodos[columna] = (anio_actual, int(encontrado.group(1)))
    if not periodos:
        raise ValueError("No se detectaron periodos en el Excel de transacciones")

    municipios = _municipios()
    municipios["provincia_clave"] = municipios["provincia_norm"].map(normalizar)
    municipios["municipio_clave"] = municipios["municipio_norm"].map(normalizar)
    objetivo = {
        (fila.provincia_clave, fila.municipio_clave): fila.cod_ine
        for fila in municipios.itertuples()
    }
    provincias = set(municipios["provincia_clave"])
    provincia_actual: str | None = None
    registros: list[dict[str, object]] = []

    for _, fila in bruto.iloc[13:].iterrows():
        etiqueta = normalizar(fila.iloc[1])
        if etiqueta is None:
            continue
        provincia_candidata = MAPEO_PROVINCIAS.get(etiqueta, etiqueta)
        es_cabecera = fila.iloc[list(periodos)].isna().all()
        if es_cabecera and provincia_candidata in provincias:
            provincia_actual = provincia_candidata
            continue
        if etiqueta in {"CEUTA", "MELILLA"}:
            provincia_actual = etiqueta
        municipio_clave = normalizar_articulo(etiqueta)
        municipio_clave = MAPEO_MUNICIPIOS.get(municipio_clave, municipio_clave)
        codigo = objetivo.get((provincia_actual, municipio_clave))
        if codigo is None:
            continue
        for columna, (anio, trimestre) in periodos.items():
            valor = pd.to_numeric(fila.iloc[columna], errors="coerce")
            if pd.notna(valor):
                registros.append(
                    {
                        "cod_ine": codigo,
                        "anio": anio,
                        "trimestre": trimestre,
                        "compraventas": int(valor),
                        "fuente": "MIVAU, transacciones inmobiliarias municipales, tabla 2",
                    }
                )
    salida = pd.DataFrame(registros)
    if salida.duplicated(["cod_ine", "anio", "trimestre"]).any():
        raise ValueError("Duplicados municipio-periodo en transacciones")
    cobertura = salida.groupby(["anio", "trimestre"])["cod_ine"].nunique()
    if cobertura.max() != 306:
        ultimo = cobertura.index.max()
        presentes = set(
            salida.loc[
                (salida["anio"] == ultimo[0]) & (salida["trimestre"] == ultimo[1]),
                "cod_ine",
            ]
        )
        faltan = municipios.loc[~municipios["cod_ine"].isin(presentes), ["cod_ine", "nombre"]]
        raise ValueError(
            f"Cobertura máxima {cobertura.max()}/306. Faltan: "
            f"{faltan.to_dict('records')}"
        )
    salida = salida.sort_values(["cod_ine", "anio", "trimestre"]).reset_index(drop=True)
    TRANSACCIONES_OUT.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(TRANSACCIONES_OUT, index=False)
    print(
        f"Transacciones: {len(salida):,} filas; {salida.cod_ine.nunique()}/306; "
        f"{salida.anio.min()}–{salida.anio.max()}"
    )
    return salida


def procesar_parque() -> pd.DataFrame:
    with PARQUE_RAW.open(encoding="utf-8-sig") as fichero:
        bruto = json.load(fichero)
    registros = []
    for serie in bruto:
        metadata = serie.get("MetaData", [])
        meta_municipio = next(
            (m for m in metadata if m.get("T3_Variable") in {"Municipio", "Municipios"}),
            None,
        )
        meta_tipo = next(
            (
                m
                for m in metadata
                if m.get("T3_Variable") == "Tipo de vivienda (principal o no)"
            ),
            None,
        )
        if not meta_municipio or not meta_tipo or meta_tipo.get("Codigo") != "total":
            continue
        datos = serie.get("Data") or []
        if not datos or datos[0].get("Valor") is None:
            continue
        codigo = str(meta_municipio.get("Codigo", "")).zfill(5)
        registros.append(
            {
                "cod_ine": codigo,
                "anio_referencia": 2021,
                "viviendas": int(round(float(datos[0]["Valor"]))),
                "fuente": "INE, Censo de Población y Viviendas 2021, tabla 59525",
            }
        )
    salida = pd.DataFrame(registros)
    objetivo = set(_municipios()["cod_ine"])
    salida = salida[salida["cod_ine"].isin(objetivo)].copy()
    if salida["cod_ine"].nunique() != 306 or salida.duplicated("cod_ine").any():
        raise ValueError(
            f"Parque 2021 sin cobertura íntegra: {salida.cod_ine.nunique()}/306"
        )
    if (salida["viviendas"] <= 0).any():
        raise ValueError("Parque residencial con valores no positivos")
    salida = salida.sort_values("cod_ine").reset_index(drop=True)
    PARQUE_OUT.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(PARQUE_OUT, index=False)
    print("Parque de viviendas: 306/306 municipios")
    return salida


def _suma_columnas(df: pd.DataFrame, prefijo: str, categorias: tuple[str, ...]) -> pd.Series:
    columnas = [
        col
        for col in df.columns
        if col.startswith(prefijo) and any(col.endswith(cat) for cat in categorias)
    ]
    if not columnas:
        raise ValueError(f"No se hallaron columnas {prefijo} para {categorias}")
    return df[columnas].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)


def procesar_catastro() -> pd.DataFrame:
    objetivo = set(_municipios()["cod_ine"])
    partes = []
    for anio in CATASTRO_ANIOS:
        ruta = RAW_DIR / f"catastro_titularidad_residencial_{anio}.csv"
        df = pd.read_csv(ruta, sep=";", encoding="iso-8859-15", dtype=str)
        df["cod_ine"] = df["CODINE"].str.zfill(5)
        # Inmuebles residenciales: suma por tramos y clase fiscal. Se separa
        # persona jurídica privada (sociedades) del resto de entidades.
        df["inmuebles_persona_fisica"] = _suma_columnas(
            df, "I_U_", ("FIS_NA", "FIS_EX")
        )
        df["inmuebles_sociedades"] = _suma_columnas(df, "I_U_", ("SOCIEDADES",))
        df["inmuebles_otras_entidades"] = _suma_columnas(
            df,
            "I_U_",
            (
                "ENTIDADES_SINAL",
                "ENTIDADES_SINPJ",
                "ENTIDADES_EXT",
                "AAPP",
                "ENTIDADES_NDEF",
                "OTROS",
            ),
        )
        df["inmuebles_total_calculado"] = (
            df["inmuebles_persona_fisica"]
            + df["inmuebles_sociedades"]
            + df["inmuebles_otras_entidades"]
        )
        df["anio"] = anio
        df["fuente"] = (
            "Dirección General del Catastro, padrón urbano residencial "
            "por tipo de persona fiscal"
        )
        partes.append(
            df[
                [
                    "cod_ine",
                    "anio",
                    "inmuebles_total_calculado",
                    "inmuebles_persona_fisica",
                    "inmuebles_sociedades",
                    "inmuebles_otras_entidades",
                    "fuente",
                ]
            ]
        )
    salida = pd.concat(partes, ignore_index=True)
    salida = salida[salida["cod_ine"].isin(objetivo)].copy()
    salida = salida.rename(columns={"inmuebles_total_calculado": "inmuebles_total"})
    if salida.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("Duplicados municipio-año en Catastro")
    cobertura = salida.groupby("anio")["cod_ine"].nunique()
    if not cobertura.eq(289).all():
        raise ValueError(f"Cobertura Catastro inesperada: {cobertura.to_dict()}")
    if (salida["inmuebles_total"] <= 0).any():
        raise ValueError("Totales catastrales no positivos")
    salida = salida.sort_values(["cod_ine", "anio"]).reset_index(drop=True)
    CATASTRO_OUT.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(CATASTRO_OUT, index=False)
    print(f"Catastro complementario: {cobertura.to_dict()} (17 forales excluidos)")
    return salida


def cargar_postgresql(
    transacciones: pd.DataFrame,
    parque: pd.DataFrame,
    catastro: pd.DataFrame,
    db_url: str,
) -> None:
    engine = create_engine(db_url)
    tablas = {
        "transacciones_vivienda_municipal": (
            transacciones,
            ["cod_ine", "anio", "trimestre"],
        ),
        "parque_viviendas_2021": (parque, ["cod_ine"]),
        "titularidad_corporativa_catastro": (catastro, ["cod_ine", "anio"]),
    }
    with engine.begin() as conn:
        for tabla, (datos, clave) in tablas.items():
            temporal = f"_{tabla}_carga"
            conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
            datos.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
            columnas = list(datos.columns)
            actualizaciones = ", ".join(
                f"{c}=EXCLUDED.{c}" for c in columnas if c not in clave
            )
            conn.execute(
                text(
                    f"INSERT INTO {tabla} ({','.join(columnas)}) "
                    f"SELECT {','.join(columnas)} FROM {temporal} "
                    f"ON CONFLICT ({','.join(clave)}) DO UPDATE SET {actualizaciones}"
                )
            )
            conn.execute(text(f"DROP TABLE {temporal}"))
    print("Carga de fuentes en PostgreSQL completada")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()

    if not args.skip_download:
        descargar(TRANSACCIONES_URL, TRANSACCIONES_RAW, args.force_download,
                  organismo="Ministerio de Transportes y Movilidad Sostenible",
                  recurso="Transacciones inmobiliarias de vivienda, boletín estadístico 34010210",
                  licencia="https://sede.transportes.gob.es/aviso-legal")
        descargar(PARQUE_URL, PARQUE_RAW, args.force_download,
                  organismo="Instituto Nacional de Estadística",
                  recurso="Censo de población y viviendas 2021, tabla 59525",
                  licencia="https://www.ine.es/dyngs/AYU/index.htm?cid=125")
        for anio in CATASTRO_ANIOS:
            # El portal de datos abiertos del Catastro publica estos CSV con
            # un certificado que la cadena de confianza del sistema no
            # valida; se desactiva la verificación TLS solo para esta
            # descarga puntual, no para el resto de fuentes.
            descargar(
                CATASTRO_URL.format(anio=anio),
                RAW_DIR / f"catastro_titularidad_residencial_{anio}.csv",
                args.force_download,
                verify=False,
                organismo="Dirección General del Catastro",
                recurso=f"Estadísticas de titularidad de bienes inmuebles residenciales {anio}",
                licencia="https://www.catastro.hacienda.gob.es/es-ES/estadisticas_3_1.html",
            )
    transacciones = procesar_transacciones()
    parque = procesar_parque()
    catastro = procesar_catastro()
    if not args.no_db:
        cargar_postgresql(transacciones, parque, catastro, args.db_url)


if __name__ == "__main__":
    main()
