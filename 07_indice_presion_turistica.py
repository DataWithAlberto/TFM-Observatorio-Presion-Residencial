#!/usr/bin/env python3
"""Calcula el score nacional de presión turística en escala 0–100."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

INDICADORES_FILE = Path("data/processed/indicadores_turisticos.csv")
MUNICIPIOS_GPKG = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_FILE = Path("data/processed/presion_turistica_score.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
SQL_FILE = Path("database/bootstrap/01_serving_tables.sql")
VARIABLES_SCORE = ["vut_por_1000_hab", "vut_por_km2"]
MAX_CORRELACION = 0.90


def _percentil(grupo: pd.Series) -> pd.Series:
    if grupo.nunique(dropna=True) <= 1:
        return pd.Series(50.0, index=grupo.index)
    return 100 * (grupo.rank(method="average") - 1) / (grupo.notna().sum() - 1)


def calcular() -> pd.DataFrame:
    df = pd.read_csv(INDICADORES_FILE, dtype={"cod_ine": str}, parse_dates=["fecha"])
    if df[VARIABLES_SCORE].isna().any().any():
        raise ValueError("Hay nulos en variables del score principal")
    if not df.groupby("fecha")["cod_ine"].nunique().eq(306).all():
        raise ValueError("El score no puede calcularse sin cobertura 306/306")

    correlaciones = []
    for fecha, grupo in df.groupby("fecha"):
        corr = grupo[VARIABLES_SCORE].corr(method="spearman").iloc[0, 1]
        correlaciones.append((fecha, corr))
    peor = max(abs(corr) for _, corr in correlaciones)
    if peor >= MAX_CORRELACION:
        raise ValueError(
            f"Variables redundantes: correlación Spearman máxima {peor:.3f} "
            f"(umbral {MAX_CORRELACION})"
        )

    salida = df[["cod_ine", "fecha"] + VARIABLES_SCORE].copy()
    for variable in VARIABLES_SCORE:
        salida[f"percentil_{variable}"] = salida.groupby("fecha")[variable].transform(
            _percentil
        )
    salida["score_presion_turistica"] = salida[
        [f"percentil_{v}" for v in VARIABLES_SCORE]
    ].mean(axis=1)
    salida["metodo"] = "media_percentiles_50_50"
    salida["version_metodologia"] = "1.0"
    salida = salida.sort_values(["fecha", "cod_ine"]).reset_index(drop=True)
    if not salida["score_presion_turistica"].between(0, 100).all():
        raise ValueError("Score fuera de rango 0–100")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT_FILE, index=False)
    print(f"Score: {len(salida):,} filas; correlación máxima={peor:.3f}")
    validar_referencias(salida)
    return salida


def validar_referencias(score: pd.DataFrame) -> None:
    import geopandas as gpd
    nombres = gpd.read_file(MUNICIPIOS_GPKG, ignore_geometry=True)[["cod_ine", "nombre"]]
    nombres["cod_ine"] = nombres["cod_ine"].astype(str).str.zfill(5)
    referencias = {
        "Barcelona": "08019", "Palma": "07040", "Málaga": "29067",
        "Donostia/San Sebastián": "20069", "Gijón": "33024",
        "Oviedo": "33044", "Santander": "39075",
    }
    ultima = score["fecha"].max()
    muestra = score[
        (score["fecha"] == ultima) & score["cod_ine"].isin(referencias.values())
    ].merge(nombres, on="cod_ine", how="left")
    if len(muestra) != len(referencias):
        raise ValueError("Faltan municipios de referencia")
    print(f"\nCasos de referencia ({ultima.date()}):")
    print(
        muestra[[
            "nombre", "vut_por_1000_hab", "vut_por_km2",
            "score_presion_turistica",
        ]].sort_values("score_presion_turistica", ascending=False).to_string(
            index=False, float_format=lambda x: f"{x:.2f}"
        )
    )


def cargar_postgresql(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    temporal = "_presion_turistica_score_carga"
    columnas = list(df.columns)
    updates = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in columnas if c not in ("cod_ine", "fecha")
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text(encoding="utf-8"))
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(text(
            f"INSERT INTO presion_turistica_score ({','.join(columnas)}) "
            f"SELECT {','.join(columnas)} FROM {temporal} "
            f"ON CONFLICT (cod_ine,fecha) DO UPDATE SET {updates}"
        ))
        conn.execute(text(f"DROP TABLE {temporal}"))
    print("Carga presion_turistica_score completada")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    score = calcular()
    if not args.no_db:
        cargar_postgresql(score, args.db_url)


if __name__ == "__main__":
    main()
