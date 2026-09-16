#!/usr/bin/env python3
"""Ingesta reproducible de renta neta media por hogar del Atlas del INE.

La tabla 30824 contiene todos los municipios, distritos y secciones de España.
Este pipeline conserva únicamente el nivel municipal, valida los códigos contra
el callejero INE y hace una carga idempotente en ``renta_hogares``.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path

import pandas as pd
import requests

from reproducibilidad.descargas import record_download
from sqlalchemy import create_engine, text

INE_TABLE_ID = "30824"
INE_URL = f"https://www.ine.es/jaxiT3/files/t/csv_bdsc/{INE_TABLE_ID}.csv"
FUENTE = f"INE, Atlas de distribución de renta de los hogares, tabla {INE_TABLE_ID}"
RAW_FILE = Path("data/raw/ine_renta/atlas_renta_30824.csv")
MUNICIPIOS_FILE = Path("data/processed/municipios_ine.csv")
OUT_FILE = Path("data/processed/renta_hogares.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
# Cerdedo y Cotobade se fusionaron en 2016 para formar Cerdedo-Cotobade
# (36902). Sus observaciones de 2015 son históricamente válidas y no deben
# reasignarse al nuevo municipio porque cambiaría la unidad territorial.
CODIGOS_HISTORICOS_VALIDOS = {"36011", "36012"}


def descargar(destino: Path = RAW_FILE, force: bool = False) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not force:
        print(f"Se reutiliza la descarga existente: {destino}")
        return destino

    temporal = destino.with_suffix(destino.suffix + ".part")
    with requests.get(INE_URL, timeout=180, stream=True) as respuesta:
        respuesta.raise_for_status()
        with temporal.open("wb") as fichero:
            for bloque in respuesta.iter_content(chunk_size=1024 * 1024):
                if bloque:
                    fichero.write(bloque)
    temporal.replace(destino)
    record_download(
        destino, INE_URL,
        organism="Instituto Nacional de Estadística",
        resource="Atlas de distribución de renta de los hogares",
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
    )
    print(f"Descargado: {destino} ({destino.stat().st_size:,} bytes)")
    return destino


def _detectar_encoding(ruta: Path) -> str:
    # El INE ha servido esta tabla tanto como UTF-8 con BOM como ISO-8859-15.
    for encoding in ("utf-8-sig", "iso-8859-15"):
        try:
            pd.read_csv(ruta, sep=";", dtype=str, encoding=encoding, nrows=5)
            return encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo determinar la codificación de {ruta}")


def _parsear_euros(valor: pd.Series) -> pd.Series:
    limpio = (
        valor.astype("string")
        .str.strip()
        .replace({"": pd.NA, "..": pd.NA, "...": pd.NA, ":": pd.NA, "nan": pd.NA})
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(limpio, errors="coerce")


def procesar(
    raw_file: Path = RAW_FILE,
    municipios_file: Path = MUNICIPIOS_FILE,
    out_file: Path = OUT_FILE,
) -> pd.DataFrame:
    encoding = _detectar_encoding(raw_file)
    cabecera = pd.read_csv(raw_file, sep=";", dtype=str, encoding=encoding, nrows=0)
    indicador_cols = [col for col in cabecera.columns if col.startswith("Indicadores de renta")]
    requeridas = {"Municipios", "Distritos", "Secciones", "Periodo", "Total"}
    faltantes = requeridas.difference(cabecera.columns)
    if faltantes:
        raise ValueError(f"Columnas INE ausentes: {sorted(faltantes)}")
    if len(indicador_cols) != 1:
        raise ValueError(f"No se pudo identificar la columna de indicador: {indicador_cols}")
    indicador_col = indicador_cols[0]

    # Una fila municipal no tiene distrito ni sección. No basta con buscar un
    # código de cinco dígitos porque las filas de nivel inferior también lo contienen.
    trozos = []
    for df in pd.read_csv(
        raw_file, sep=";", dtype=str, encoding=encoding, chunksize=250_000
    ):
        sin_distrito = df["Distritos"].fillna("").str.strip().eq("")
        sin_seccion = df["Secciones"].fillna("").str.strip().eq("")
        renta_hogar = df[indicador_col].str.strip().eq("Renta neta media por hogar")
        trozos.append(df.loc[sin_distrito & sin_seccion & renta_hogar].copy())
    municipal = pd.concat(trozos, ignore_index=True)

    municipal["cod_ine"] = municipal["Municipios"].str.extract(r"^\s*(\d{5})\b")[0]
    municipal["anio"] = pd.to_numeric(municipal["Periodo"], errors="coerce")
    municipal["renta_media"] = _parsear_euros(municipal["Total"])
    municipal["fuente"] = FUENTE
    municipal = municipal[["cod_ine", "anio", "renta_media", "fuente"]].dropna(
        subset=["cod_ine", "anio", "renta_media"]
    )
    municipal["anio"] = municipal["anio"].astype(int)
    municipal["cod_ine"] = municipal["cod_ine"].str.zfill(5)

    if (municipal["renta_media"] <= 0).any():
        raise ValueError("Se encontraron rentas nulas o negativas")
    duplicados = municipal.duplicated(["cod_ine", "anio"], keep=False)
    if duplicados.any():
        muestra = municipal.loc[duplicados, ["cod_ine", "anio"]].head().to_dict("records")
        raise ValueError(f"Duplicados municipio-año en el INE: {muestra}")

    municipios = pd.read_csv(municipios_file, dtype={"id_municipio": str})
    codigos_validos = set(municipios["id_municipio"].str.zfill(5))
    no_validos = sorted(
        set(municipal["cod_ine"]).difference(codigos_validos | CODIGOS_HISTORICOS_VALIDOS)
    )
    if no_validos:
        # Cambios de código municipal entre ediciones se deben resolver de forma
        # explícita; descartarlos silenciosamente falsearía la cobertura.
        raise ValueError(
            f"{len(no_validos)} códigos del Atlas no existen en el callejero INE: "
            f"{no_validos[:20]}"
        )

    municipal = municipal.sort_values(["cod_ine", "anio"]).reset_index(drop=True)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    municipal.to_csv(out_file, index=False)
    print(
        f"Renta procesada: {len(municipal):,} filas, "
        f"{municipal['cod_ine'].nunique():,} municipios, "
        f"{municipal['anio'].min()}–{municipal['anio'].max()}"
    )
    print(f"Guardado: {out_file}")
    return municipal


def cargar_postgresql(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    ddl = """
    CREATE TABLE IF NOT EXISTS renta_hogares (
        cod_ine CHAR(5) NOT NULL,
        anio SMALLINT NOT NULL,
        renta_media NUMERIC(12,2) NOT NULL CHECK (renta_media > 0),
        fuente TEXT NOT NULL,
        PRIMARY KEY (cod_ine, anio)
    )
    """
    temporal = "_renta_hogares_carga"
    with engine.begin() as conn:
        conn.execute(text(ddl))
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(
            text(
                f"""
                INSERT INTO renta_hogares (cod_ine, anio, renta_media, fuente)
                SELECT cod_ine, anio, renta_media, fuente FROM {temporal}
                ON CONFLICT (cod_ine, anio) DO UPDATE SET
                    renta_media = EXCLUDED.renta_media,
                    fuente = EXCLUDED.fuente
                """
            )
        )
        conn.execute(text(f"DROP TABLE {temporal}"))
    print(f"Cargadas/actualizadas {len(df):,} filas en renta_hogares")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--no-db", action="store_true", help="No cargar PostgreSQL")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()

    if not args.skip_download:
        descargar(force=args.force_download)
    if not RAW_FILE.exists():
        raise FileNotFoundError(f"Falta {RAW_FILE}; ejecute sin --skip-download")
    datos = procesar()
    if not args.no_db:
        cargar_postgresql(datos, args.db_url)


if __name__ == "__main__":
    main()
