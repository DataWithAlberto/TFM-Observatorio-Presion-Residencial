#!/usr/bin/env python3
"""Calcula el score nacional de presión especulativa (0–100)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

INDICADORES_FILE = Path("data/processed/indicadores_especulativos.csv")
MUNICIPIOS_GPKG = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_FILE = Path("data/processed/presion_especulativa_score.csv")
OUT_CORR = Path("data/processed/especulacion_correlaciones.csv")
OUT_SENS = Path("data/processed/especulacion_sensibilidad.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
VARIABLES = [
    "tasa_rotacion",
    "aceleracion_precio",
    "desacoplamiento_precio_renta",
]
ESCENARIOS = {
    "pesos_iguales": [1 / 3, 1 / 3, 1 / 3],
    "enfasis_rotacion": [0.50, 0.25, 0.25],
    "enfasis_aceleracion": [0.25, 0.50, 0.25],
    "enfasis_desacoplamiento": [0.25, 0.25, 0.50],
}


def _percentil(serie: pd.Series) -> pd.Series:
    if serie.nunique(dropna=True) <= 1:
        return pd.Series(50.0, index=serie.index)
    return 100 * (serie.rank(method="average") - 1) / (serie.notna().sum() - 1)


def calcular() -> pd.DataFrame:
    df = pd.read_csv(INDICADORES_FILE, dtype={"cod_ine": str})
    elegible = df[df["elegible_score_principal"]].copy()
    cobertura = elegible.groupby("anio")["cod_ine"].nunique()
    anios_completos = cobertura[cobertura == 306].index
    elegible = elegible[elegible["anio"].isin(anios_completos)].copy()
    if elegible.empty:
        raise ValueError("No hay años completos 306/306 para el score")
    if elegible[VARIABLES].isna().any().any():
        raise ValueError("Nulos en variables del score principal")

    salida = elegible[["cod_ine", "anio"] + VARIABLES].copy()
    for variable in VARIABLES:
        salida[f"percentil_{variable}"] = salida.groupby("anio")[variable].transform(
            _percentil
        )
    percentiles = [f"percentil_{variable}" for variable in VARIABLES]
    salida["score_presion_especulativa"] = salida[percentiles].mean(axis=1)
    salida["metodo"] = "media_percentiles_iguales"
    salida["version_metodologia"] = "1.0"
    salida = salida.sort_values(["anio", "cod_ine"]).reset_index(drop=True)
    if salida.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("Duplicados en score")
    if not salida["score_presion_especulativa"].between(0, 100).all():
        raise ValueError("Score fuera de rango")
    if not salida.groupby("anio")["cod_ine"].nunique().eq(306).all():
        raise ValueError("Cobertura del score distinta de 306/306")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT_FILE, index=False)
    auditar(salida)
    print(
        f"Score: {len(salida):,} filas; años {salida.anio.min()}–"
        f"{salida.anio.max()}; cobertura 306/306"
    )
    validar_referencias(salida)
    return salida


def auditar(score: pd.DataFrame) -> None:
    correlaciones = []
    sensibilidad = []
    percentiles = [f"percentil_{v}" for v in VARIABLES]
    for anio, grupo in score.groupby("anio"):
        corr = grupo[VARIABLES].corr(method="spearman")
        for fila in VARIABLES:
            for columna in VARIABLES:
                correlaciones.append(
                    {
                        "anio": anio,
                        "variable_fila": fila,
                        "variable_columna": columna,
                        "spearman": corr.loc[fila, columna],
                    }
                )
        base = grupo["score_presion_especulativa"]
        ranking_base = base.rank(ascending=False, method="average")
        limite = int(np.ceil(len(grupo) * 0.10))
        top_base = set(grupo.loc[ranking_base.le(limite), "cod_ine"])
        for escenario, pesos in ESCENARIOS.items():
            alternativo = (
                base
                if escenario == "pesos_iguales"
                else sum(
                    grupo[columna] * peso
                    for columna, peso in zip(percentiles, pesos, strict=True)
                )
            )
            ranking = alternativo.rank(ascending=False, method="average")
            top = set(grupo.loc[ranking.le(limite), "cod_ine"])
            sensibilidad.append(
                {
                    "anio": anio,
                    "escenario": escenario,
                    "peso_rotacion": pesos[0],
                    "peso_aceleracion": pesos[1],
                    "peso_desacoplamiento": pesos[2],
                    "spearman_score_base": alternativo.corr(
                        base, method="spearman"
                    ),
                    "cambio_rango_medio": (ranking - ranking_base).abs().mean(),
                    "cambio_rango_maximo": (ranking - ranking_base).abs().max(),
                    "solapamiento_top_10_pct": len(top & top_base) / len(top_base),
                }
            )
    pd.DataFrame(correlaciones).to_csv(OUT_CORR, index=False)
    pd.DataFrame(sensibilidad).to_csv(OUT_SENS, index=False)


def validar_referencias(score: pd.DataFrame) -> None:
    import geopandas as gpd

    nombres = gpd.read_file(MUNICIPIOS_GPKG, ignore_geometry=True)[["cod_ine", "nombre"]]
    nombres["cod_ine"] = nombres["cod_ine"].astype(str).str.zfill(5)
    codigos = ["28079", "08019", "46250", "29067", "33024"]
    ultimo = score["anio"].max()
    muestra = score[
        (score["anio"] == ultimo) & score["cod_ine"].isin(codigos)
    ].merge(nombres, on="cod_ine", how="left", validate="one_to_one")
    if len(muestra) != len(codigos):
        raise ValueError("Faltan municipios de referencia")
    print(f"\nCasos de referencia ({ultimo}):")
    print(
        muestra[
            [
                "nombre",
                "tasa_rotacion",
                "aceleracion_precio",
                "desacoplamiento_precio_renta",
                "score_presion_especulativa",
            ]
        ]
        .sort_values("score_presion_especulativa", ascending=False)
        .to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )


def cargar_postgresql(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    temporal = "_presion_especulativa_score_carga"
    columnas = list(df.columns)
    updates = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in columnas if c not in ("cod_ine", "anio")
    )
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(
            text(
                f"INSERT INTO presion_especulativa_score ({','.join(columnas)}) "
                f"SELECT {','.join(columnas)} FROM {temporal} "
                f"ON CONFLICT (cod_ine,anio) DO UPDATE SET {updates}"
            )
        )
        conn.execute(text(f"DROP TABLE {temporal}"))
    print("Carga presion_especulativa_score completada")


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
