#!/usr/bin/env python3
"""Ingesta oficial de viviendas turísticas y población municipal del INE."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

from reproducibilidad.descargas import record_download
from utils_http import session_with_retries

VUT_URL = "https://www.ine.es/jaxiT3/files/t/csv_bdsc/39363.csv"
RAW_DIR = Path("data/raw/ine_turismo")
VUT_RAW = RAW_DIR / "viviendas_turisticas_39363.csv"
POBLACION_DIR = RAW_DIR / "poblacion_provincias"
POBLACION_TABLE_IDS = range(2854, 2910)
MUNICIPIOS_GPKG = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_VUT = Path("data/processed/turismo_fuentes.csv")
OUT_POBLACION = Path("data/processed/poblacion_municipal.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
SQL_FILE = Path("sql/05_turismo.sql")


def descargar(url: str, destino: Path, force: bool = False, recurso: str | None = None) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not force:
        print(f"Se reutiliza: {destino}")
        return destino
    temporal = destino.with_suffix(destino.suffix + ".part")
    with session_with_retries().get(url, timeout=240, stream=True) as respuesta:
        respuesta.raise_for_status()
        with temporal.open("wb") as fichero:
            for bloque in respuesta.iter_content(1024 * 1024):
                if bloque:
                    fichero.write(bloque)
    temporal.replace(destino)
    record_download(
        destino, url,
        organism="Instituto Nacional de Estadística",
        resource=recurso,
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
    )
    print(f"Descargado: {destino} ({destino.stat().st_size:,} bytes)")
    return destino


def _leer_ine(ruta: Path, **kwargs) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "iso-8859-15"):
        try:
            return pd.read_csv(ruta, sep=";", dtype=str, encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo determinar la codificación de {ruta}")


def _numero_ine(serie: pd.Series) -> pd.Series:
    return pd.to_numeric(
        serie.astype("string")
        .str.strip()
        .replace({"": pd.NA, "..": pd.NA, "...": pd.NA})
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False),
        errors="coerce",
    )


def _codigos_objetivo() -> set[str]:
    import geopandas as gpd

    municipios = gpd.read_file(MUNICIPIOS_GPKG, ignore_geometry=True)
    codigos = set(municipios["cod_ine"].astype(str).str.zfill(5))
    if len(codigos) != 306:
        raise ValueError(f"Se esperaban 306 municipios y se encontraron {len(codigos)}")
    return codigos


def procesar_vut() -> pd.DataFrame:
    df = _leer_ine(VUT_RAW)
    requeridas = {"Municipios", "Viviendas y plazas", "Periodo", "Total"}
    if faltan := requeridas.difference(df.columns):
        raise ValueError(f"Columnas ausentes en tabla 39363: {sorted(faltan)}")
    df["cod_ine"] = df["Municipios"].str.extract(r"^\s*(\d{5})\b")[0]
    df = df[df["cod_ine"].isin(_codigos_objetivo())].copy()
    df["fecha"] = pd.to_datetime(
        df["Periodo"].str.extract(r"^(\d{4})M(\d{2})$").agg("-".join, axis=1) + "-01",
        errors="coerce",
    )
    df["valor"] = _numero_ine(df["Total"])
    mapa = {
        "Viviendas turísticas": "viviendas_turisticas",
        "Plazas": "plazas",
        "Plazas por vivienda turística": "plazas_por_vivienda",
    }
    df["variable"] = df["Viviendas y plazas"].map(mapa)
    df = df.dropna(subset=["cod_ine", "fecha", "variable", "valor"])
    ancho = (
        df.pivot(index=["cod_ine", "fecha"], columns="variable", values="valor")
        .reset_index()
        .rename_axis(columns=None)
    )
    ancho["viviendas_turisticas"] = ancho["viviendas_turisticas"].astype(int)
    ancho["plazas"] = ancho["plazas"].astype(int)
    ancho["fuente"] = "INE, Viviendas turísticas en España, tabla 39363"
    ancho = ancho.sort_values(["fecha", "cod_ine"]).reset_index(drop=True)
    if ancho.duplicated(["cod_ine", "fecha"]).any():
        raise ValueError("Duplicados municipio-fecha en viviendas turísticas")
    cobertura = ancho.groupby("fecha")["cod_ine"].nunique()
    if not cobertura.eq(306).all():
        raise ValueError(f"Cobertura VUT distinta de 306: {cobertura.to_dict()}")
    OUT_VUT.parent.mkdir(parents=True, exist_ok=True)
    ancho.to_csv(OUT_VUT, index=False)
    print(f"VUT: {len(ancho):,} filas; cobertura 306 en {len(cobertura)} fechas")
    return ancho


def procesar_poblacion() -> pd.DataFrame:
    trozos = []
    for table_id in POBLACION_TABLE_IDS:
        ruta = POBLACION_DIR / f"{table_id}.csv"
        # El rango histórico conserva cuatro identificadores retirados que el
        # servidor responde como ficheros vacíos; las provincias afectadas
        # aparecen en otros identificadores del mismo rango.
        if ruta.stat().st_size == 0:
            continue
        df = _leer_ine(ruta)
        requeridas = {"Municipios", "Sexo", "Periodo", "Total"}
        if faltan := requeridas.difference(df.columns):
            raise ValueError(f"Columnas ausentes en tabla {table_id}: {sorted(faltan)}")
        mascara = df["Municipios"].notna() & df["Sexo"].eq("Total")
        trozos.append(df.loc[mascara, ["Municipios", "Periodo", "Total"]])
    poblacion = pd.concat(trozos, ignore_index=True)
    poblacion["cod_ine"] = poblacion["Municipios"].str.extract(r"^\s*(\d{5})\b")[0]
    poblacion.loc[poblacion["Municipios"].str.startswith("51 "), "cod_ine"] = "51001"
    poblacion.loc[poblacion["Municipios"].str.startswith("52 "), "cod_ine"] = "52001"
    poblacion["anio"] = pd.to_numeric(
        poblacion["Periodo"].str.extract(r"(\d{4})")[0], errors="coerce"
    )
    poblacion["poblacion"] = _numero_ine(poblacion["Total"])
    poblacion = poblacion[poblacion["cod_ine"].isin(_codigos_objetivo())]
    poblacion = poblacion[["cod_ine", "anio", "poblacion"]].dropna()
    poblacion["anio"] = poblacion["anio"].astype(int)
    poblacion["poblacion"] = poblacion["poblacion"].astype(int)
    conflictos = (
        poblacion.groupby(["cod_ine", "anio"])["poblacion"].nunique().gt(1)
    )
    if conflictos.any():
        raise ValueError("Valores de población contradictorios para municipio-año")
    # Ceuta y Melilla aparecen con código provincial y municipal en origen.
    poblacion = poblacion.drop_duplicates(["cod_ine", "anio"], keep="last")
    poblacion["fuente"] = "INE, Padrón municipal, tablas provinciales 2854–2909"
    poblacion = poblacion.sort_values(["cod_ine", "anio"]).reset_index(drop=True)
    if poblacion.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("Duplicados municipio-año en población")
    if poblacion["cod_ine"].nunique() != 306:
        raise ValueError("La población no cubre los 306 municipios")
    OUT_POBLACION.parent.mkdir(parents=True, exist_ok=True)
    poblacion.to_csv(OUT_POBLACION, index=False)
    print(
        f"Población: {len(poblacion):,} filas; "
        f"{poblacion['anio'].min()}–{poblacion['anio'].max()}"
    )
    return poblacion


def cargar_postgresql(vut: pd.DataFrame, poblacion: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text(encoding="utf-8"))
        for nombre, datos, clave in (
            ("turismo_fuentes", vut, ["cod_ine", "fecha"]),
            ("poblacion_municipal", poblacion, ["cod_ine", "anio"]),
        ):
            temporal = f"_{nombre}_carga"
            conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
            datos.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
            columnas = list(datos.columns)
            updates = ", ".join(
                f"{c}=EXCLUDED.{c}" for c in columnas if c not in clave
            )
            conn.execute(text(
                f"INSERT INTO {nombre} ({','.join(columnas)}) "
                f"SELECT {','.join(columnas)} FROM {temporal} "
                f"ON CONFLICT ({','.join(clave)}) DO UPDATE SET {updates}"
            ))
            conn.execute(text(f"DROP TABLE {temporal}"))
    print("Carga PostgreSQL completada")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    if not args.skip_download:
        descargar(VUT_URL, VUT_RAW, args.force_download,
                  recurso="Viviendas turísticas y plazas, tabla 39363")
        for table_id in POBLACION_TABLE_IDS:
            descargar(
                f"https://www.ine.es/jaxiT3/files/t/csv_bdsc/{table_id}.csv",
                POBLACION_DIR / f"{table_id}.csv",
                args.force_download,
                recurso=f"Población municipal por provincias, tabla {table_id}",
            )
    rutas = [VUT_RAW] + [
        POBLACION_DIR / f"{table_id}.csv" for table_id in POBLACION_TABLE_IDS
    ]
    for ruta in rutas:
        if not ruta.exists():
            raise FileNotFoundError(ruta)
    vut = procesar_vut()
    poblacion = procesar_poblacion()
    if not args.no_db:
        cargar_postgresql(vut, poblacion, args.db_url)


if __name__ == "__main__":
    main()
