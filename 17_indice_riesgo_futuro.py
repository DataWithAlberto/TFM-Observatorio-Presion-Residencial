#!/usr/bin/env python3
"""Calcula el índice de Riesgo Futuro Residencial mediante la fórmula oficial."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

IND_FILE = Path("data/processed/indicadores_riesgo_futuro.csv")
OUT_SCORE = Path("data/processed/riesgo_futuro_residencial_score.csv")
SQL_FILE = Path("sql/15_riesgo_futuro.sql")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
CLIMA = [
    "proyeccion_duracion_max_ola_calor_dias",
    "proyeccion_grados_dia_refrigeracion",
    "proyeccion_racha_seca_max_dias",
]
TENDENCIAS = [
    "tendencia_asequibilidad",
    "tendencia_turismo",
    "tendencia_especulacion",
    "tendencia_gentrificacion",
]
TENDENCIAS_SCORE = [
    "tendencia_asequibilidad",
    "tendencia_turismo",
    "tendencia_gentrificacion",
]


def percentil(serie: pd.Series) -> pd.Series:
    n_validos = serie.notna().sum()
    if n_validos == 0:
        return pd.Series(np.nan, index=serie.index, dtype=float)
    if serie.nunique(dropna=True) <= 1:
        return pd.Series(
            np.where(serie.notna(), 50.0, np.nan), index=serie.index, dtype=float
        )
    inferior, superior = serie.quantile([0.01, 0.99])
    s = serie.clip(inferior, superior)
    return 100 * (s.rank(method="average") - 1) / (s.notna().sum() - 1)


def calcular() -> pd.DataFrame:
    df = pd.read_csv(IND_FILE, dtype={"cod_ine": str})
    if df[CLIMA].notna().all(axis=1).sum() < 291:
        raise ValueError("Cobertura climática inferior al 95%")
    salida = df[
        [
            "cod_ine",
            "anio_base",
            "horizonte_climatico",
            "escenario_climatico",
            "tipo_valor_climatico",
        ]
        + CLIMA
        + TENDENCIAS
    ].copy()
    for variable in CLIMA + TENDENCIAS:
        salida[f"percentil_{variable}"] = percentil(salida[variable])

    p_clima = [f"percentil_{v}" for v in CLIMA]
    p_tend = [f"percentil_{v}" for v in TENDENCIAS_SCORE]
    salida["score_riesgo_climatico"] = salida[p_clima].mean(axis=1)
    salida["n_tendencias_validas"] = salida[TENDENCIAS_SCORE].notna().sum(axis=1)
    salida["score_tendencia_presion"] = salida[p_tend].mean(axis=1, skipna=True)
    salida["elegible_score"] = (
        salida[CLIMA].notna().all(axis=1)
        & salida["n_tendencias_validas"].ge(2)
    )
    salida["score_riesgo_futuro"] = np.where(
        salida["elegible_score"],
        0.60 * salida["score_riesgo_climatico"]
        + 0.40 * salida["score_tendencia_presion"],
        np.nan,
    )
    salida["metodo"] = (
        "anomalias_climaticas_60_tendencias_activas_40_percentiles_v2"
    )
    salida["version_metodologia"] = "2.0"
    validar(salida)
    OUT_SCORE.parent.mkdir(parents=True, exist_ok=True)
    salida.sort_values("cod_ine").to_csv(OUT_SCORE, index=False)
    return salida


def validar(df: pd.DataFrame) -> None:
    if df.duplicated("cod_ine").any() or len(df) != 306:
        raise ValueError("El score debe contener exactamente 306 municipios únicos")
    validos = df.loc[df["elegible_score"], "score_riesgo_futuro"]
    if validos.empty or not validos.between(0, 100).all():
        raise ValueError("Score vacío o fuera de rango")
    if df["elegible_score"].sum() < 276:
        raise ValueError("Cobertura elegible inferior al 90%")
    percentiles_tendencia = [f"percentil_{v}" for v in TENDENCIAS_SCORE]
    if not (
        df[percentiles_tendencia].notna().sum(axis=1)
        == df["n_tendencias_validas"]
    ).all():
        raise ValueError(
            "El número de percentiles de tendencia no coincide con los datos válidos"
        )
    if df["tendencia_especulacion"].notna().any():
        raise ValueError(
            "La especulación no debe producir tendencia con solo dos años"
        )


def cargar(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    tabla = "riesgo_futuro_residencial_score"
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text())
        conn.execute(text(f"DELETE FROM {tabla}"))
        df.to_sql(f"_{tabla}_carga", conn, if_exists="replace", index=False)
        columnas = list(df.columns)
        conn.execute(text(f"INSERT INTO {tabla} ({','.join(columnas)}) SELECT {','.join(columnas)} FROM _{tabla}_carga"))
        conn.execute(text(f"DROP TABLE _{tabla}_carga"))
        conn.execute(
            text(
                f"ALTER TABLE {tabla} "
                "ALTER COLUMN tipo_valor_climatico SET NOT NULL"
            )
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    salida = calcular()
    print(
        f"Score: {salida.elegible_score.sum()}/306 elegibles; "
        f"rango {salida.score_riesgo_futuro.min():.2f}–{salida.score_riesgo_futuro.max():.2f}"
    )
    if not args.no_db:
        cargar(salida, args.db_url)


if __name__ == "__main__":
    main()
