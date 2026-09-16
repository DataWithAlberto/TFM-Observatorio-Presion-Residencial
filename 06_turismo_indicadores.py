#!/usr/bin/env python3
"""Construye indicadores turísticos comparables para los 306 municipios."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

VUT_FILE = Path("data/processed/turismo_fuentes.csv")
POBLACION_FILE = Path("data/processed/poblacion_municipal.csv")
MUNICIPIOS_GPKG = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_FILE = Path("data/processed/indicadores_turisticos.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"


def construir() -> pd.DataFrame:
    vut = pd.read_csv(VUT_FILE, dtype={"cod_ine": str}, parse_dates=["fecha"])
    poblacion = pd.read_csv(POBLACION_FILE, dtype={"cod_ine": str})
    geo = gpd.read_file(MUNICIPIOS_GPKG)[["cod_ine", "geometry"]]
    geo["cod_ine"] = geo["cod_ine"].astype(str).str.zfill(5)
    geo["superficie_km2"] = geo.to_crs(3035).geometry.area / 1_000_000

    # As-of municipal: último padrón disponible no posterior al año del dato.
    base = vut.sort_values(["cod_ine", "fecha"]).copy()
    base["anio_ref"] = base["fecha"].dt.year.astype("int64")
    poblacion = poblacion.sort_values(["cod_ine", "anio"]).copy()
    poblacion["anio"] = poblacion["anio"].astype("int64")
    partes = []
    for codigo, grupo in base.groupby("cod_ine", sort=False):
        pob = poblacion[poblacion["cod_ine"] == codigo]
        combinado = pd.merge_asof(
            grupo.sort_values("anio_ref"),
            pob[["anio", "poblacion"]].sort_values("anio"),
            left_on="anio_ref",
            right_on="anio",
            direction="backward",
        )
        if combinado["poblacion"].isna().any():
            raise ValueError(f"Sin población previa para {codigo}")
        combinado["cod_ine"] = codigo
        partes.append(combinado)
    resultado = pd.concat(partes, ignore_index=True).merge(
        geo[["cod_ine", "superficie_km2"]], on="cod_ine", validate="many_to_one"
    )
    resultado = resultado.rename(columns={"anio": "anio_poblacion"})
    resultado["vut_por_1000_hab"] = (
        1000 * resultado["viviendas_turisticas"] / resultado["poblacion"]
    )
    resultado["plazas_por_1000_hab"] = (
        1000 * resultado["plazas"] / resultado["poblacion"]
    )
    resultado["vut_por_km2"] = (
        resultado["viviendas_turisticas"] / resultado["superficie_km2"]
    )

    resultado["anio_snapshot"] = resultado["fecha"].dt.year
    stats = (
        resultado.groupby(["cod_ine", "anio_snapshot"])["viviendas_turisticas"]
        .agg(min_vut="min", max_vut="max", media_vut="mean", snapshots="size")
        .reset_index()
    )
    stats["estacionalidad_vut"] = np.where(
        (stats["snapshots"] >= 2) & (stats["media_vut"] > 0),
        (stats["max_vut"] - stats["min_vut"]) / stats["media_vut"],
        np.nan,
    )
    resultado = resultado.merge(
        stats[["cod_ine", "anio_snapshot", "estacionalidad_vut", "snapshots"]],
        on=["cod_ine", "anio_snapshot"],
        validate="many_to_one",
    )
    resultado["poblacion_desfasada"] = (
        resultado["anio_ref"] - resultado["anio_poblacion"] > 1
    )
    columnas = [
        "cod_ine", "fecha", "viviendas_turisticas", "plazas",
        "plazas_por_vivienda", "poblacion", "anio_poblacion",
        "poblacion_desfasada", "superficie_km2", "vut_por_1000_hab",
        "plazas_por_1000_hab", "vut_por_km2", "estacionalidad_vut", "snapshots",
    ]
    resultado = resultado[columnas].sort_values(["fecha", "cod_ine"])
    if resultado.duplicated(["cod_ine", "fecha"]).any():
        raise ValueError("Duplicados en indicadores turísticos")
    cobertura = resultado.groupby("fecha")["cod_ine"].nunique()
    if not cobertura.eq(306).all():
        raise ValueError(f"Cobertura incompleta: {cobertura.to_dict()}")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(OUT_FILE, index=False)
    print(f"Indicadores: {len(resultado):,} filas y cobertura 306/306 por fecha")
    print("Correlaciones (última fecha):")
    ultima = resultado[resultado["fecha"] == resultado["fecha"].max()]
    print(ultima[["vut_por_1000_hab", "plazas_por_1000_hab", "vut_por_km2"]].corr())
    return resultado


def cargar_postgresql(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    ddl = """
    CREATE TABLE IF NOT EXISTS indicadores_turisticos (
        cod_ine CHAR(5) NOT NULL REFERENCES municipios(cod_ine),
        fecha DATE NOT NULL,
        viviendas_turisticas INTEGER NOT NULL CHECK (viviendas_turisticas >= 0),
        plazas INTEGER NOT NULL CHECK (plazas >= 0),
        plazas_por_vivienda NUMERIC(8,3),
        poblacion INTEGER NOT NULL CHECK (poblacion > 0),
        anio_poblacion SMALLINT NOT NULL,
        poblacion_desfasada BOOLEAN NOT NULL,
        superficie_km2 NUMERIC(14,5) NOT NULL CHECK (superficie_km2 > 0),
        vut_por_1000_hab NUMERIC(14,6) NOT NULL CHECK (vut_por_1000_hab >= 0),
        plazas_por_1000_hab NUMERIC(14,6) NOT NULL CHECK (plazas_por_1000_hab >= 0),
        vut_por_km2 NUMERIC(14,6) NOT NULL CHECK (vut_por_km2 >= 0),
        estacionalidad_vut NUMERIC(14,6),
        snapshots SMALLINT NOT NULL,
        PRIMARY KEY (cod_ine, fecha)
    )
    """
    temporal = "_indicadores_turisticos_carga"
    columnas = list(df.columns)
    updates = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in columnas if c not in ("cod_ine", "fecha")
    )
    with engine.begin() as conn:
        conn.execute(text(ddl))
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(text(
            f"INSERT INTO indicadores_turisticos ({','.join(columnas)}) "
            f"SELECT {','.join(columnas)} FROM {temporal} "
            f"ON CONFLICT (cod_ine,fecha) DO UPDATE SET {updates}"
        ))
        conn.execute(text(f"DROP TABLE {temporal}"))
    print("Carga indicadores_turisticos completada")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    datos = construir()
    if not args.no_db:
        cargar_postgresql(datos, args.db_url)


if __name__ == "__main__":
    main()
