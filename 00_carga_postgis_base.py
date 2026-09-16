#!/usr/bin/env python3
"""Carga idempotente de municipios y precios en PostGIS."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text

MUNICIPIOS_FILE = Path("data/raw/municipios_306_con_geometria.gpkg")
PRECIOS_FILE = Path("data/processed/precios_vivienda_ministerio_final.csv")
SQL_FILE = Path("sql/00_base.sql")
DEFAULT_DB_URL = (
    "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
)


def preparar_municipios() -> gpd.GeoDataFrame:
    df = gpd.read_file(MUNICIPIOS_FILE).to_crs(4326)
    df["cod_ine"] = df["cod_ine"].astype(str).str.zfill(5)
    df = df[
        ["cod_ine", "nombre", "provincia_norm", "comunidad_autonoma", "geometry"]
    ].rename(columns={"provincia_norm": "provincia"})
    if len(df) != 306 or df["cod_ine"].nunique() != 306:
        raise ValueError("El universo espacial debe contener 306 municipios únicos")
    if df.geometry.isna().any() or not df.geometry.is_valid.all():
        raise ValueError("Existen geometrías nulas o inválidas")
    return df.sort_values("cod_ine").reset_index(drop=True)


def preparar_precios(ruta: Path) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype={"id_municipio": str})
    df["cod_ine"] = df["id_municipio"].str.zfill(5)
    fecha = pd.to_datetime(df["fecha"], errors="raise")
    df["anio"] = fecha.dt.year
    df["trimestre"] = fecha.dt.quarter
    df = df.rename(columns={"valor_total": "precio_m2"})
    columnas = [
        "cod_ine",
        "anio",
        "trimestre",
        "precio_m2",
        "valor_5menos",
        "valor_5mas",
        "num_tasaciones",
    ]
    df = df[columnas].sort_values(["cod_ine", "anio", "trimestre"])
    if df.duplicated(["cod_ine", "anio", "trimestre"]).any():
        raise ValueError("Duplicados municipio-año-trimestre en precios")
    if df[["cod_ine", "anio", "trimestre"]].isna().any().any():
        raise ValueError("Nulos en la clave de precios")
    return df.reset_index(drop=True)


def cargar(
    municipios: gpd.GeoDataFrame,
    precios: pd.DataFrame,
    db_url: str,
) -> None:
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text(encoding="utf-8"))
        conn.execute(text("DROP TABLE IF EXISTS _municipios_base_carga"))
        municipios.to_postgis(
            "_municipios_base_carga", conn, if_exists="replace", index=False
        )
        conn.execute(
            text(
                """
                INSERT INTO municipios
                    (cod_ine,nombre,provincia,comunidad_autonoma,geometry)
                SELECT cod_ine,nombre,provincia,comunidad_autonoma,geometry
                FROM _municipios_base_carga
                ON CONFLICT (cod_ine) DO UPDATE SET
                    nombre=EXCLUDED.nombre,
                    provincia=EXCLUDED.provincia,
                    comunidad_autonoma=EXCLUDED.comunidad_autonoma,
                    geometry=EXCLUDED.geometry
                """
            )
        )
        conn.execute(text("DROP TABLE _municipios_base_carga"))

        conn.execute(text("DROP TABLE IF EXISTS _precios_base_carga"))
        precios.to_sql(
            "_precios_base_carga",
            conn,
            if_exists="replace",
            index=False,
            method="multi",
        )
        columnas = ",".join(precios.columns)
        actualizaciones = ",".join(
            f"{c}=EXCLUDED.{c}"
            for c in precios.columns
            if c not in {"cod_ine", "anio", "trimestre"}
        )
        conn.execute(
            text(
                f"""
                INSERT INTO precios_vivienda ({columnas})
                SELECT {columnas} FROM _precios_base_carga
                ON CONFLICT (cod_ine,anio,trimestre)
                DO UPDATE SET {actualizaciones}
                """
            )
        )
        conn.execute(text("DROP TABLE _precios_base_carga"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    parser.add_argument("--prices-file", type=Path)
    args = parser.parse_args()
    ruta_precios = args.prices_file or PRECIOS_FILE
    municipios = preparar_municipios()
    precios = preparar_precios(ruta_precios)
    cargar(municipios, precios, args.db_url)
    print(
        f"Carga base completada: {len(municipios)} municipios y "
        f"{len(precios):,} precios"
    )


if __name__ == "__main__":
    main()
