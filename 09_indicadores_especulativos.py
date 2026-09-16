#!/usr/bin/env python3
"""Construye indicadores municipales de presión especulativa residencial."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

TRANSACCIONES_FILE = Path("data/processed/transacciones_vivienda_municipal.csv")
PARQUE_FILE = Path("data/processed/parque_viviendas_2021.csv")
CATASTRO_FILE = Path("data/processed/titularidad_corporativa_catastro.csv")
PRECIOS_FILE = Path("data/processed/precios_vivienda_ministerio_final.csv")
RENTA_FILE = Path("data/processed/renta_hogares.csv")
OUT_FILE = Path("data/processed/indicadores_especulativos.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"


def _media_ponderada(grupo: pd.DataFrame) -> float:
    valores = grupo["precio_m2"].to_numpy(float)
    pesos = grupo["num_tasaciones"].fillna(0).to_numpy(float)
    validos = np.isfinite(valores)
    if not validos.any():
        return float("nan")
    return float(
        np.average(valores[validos], weights=pesos[validos])
        if pesos[validos].sum() > 0
        else np.mean(valores[validos])
    )


def precios_anuales() -> pd.DataFrame:
    df = pd.read_csv(PRECIOS_FILE, dtype={"id_municipio": str})
    df["cod_ine"] = df["id_municipio"].str.zfill(5)
    df["anio"] = pd.to_datetime(df["fecha"], errors="coerce").dt.year
    df["precio_m2"] = pd.to_numeric(df["valor_total"], errors="coerce")
    df["num_tasaciones"] = pd.to_numeric(df["num_tasaciones"], errors="coerce")
    df = df.dropna(subset=["cod_ine", "anio", "precio_m2"])
    df = df[df["precio_m2"] > 0]
    anual = (
        df.groupby(["cod_ine", "anio"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "precio_m2": _media_ponderada(g),
                    "trimestres_precio": g["fecha"].nunique(),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
        .sort_values(["cod_ine", "anio"])
    )
    anual["anio"] = anual["anio"].astype(int)
    anual["crecimiento_precio"] = anual.groupby("cod_ine")["precio_m2"].pct_change(
        fill_method=None
    )
    anual["aceleracion_precio"] = anual.groupby("cod_ine")[
        "crecimiento_precio"
    ].diff()
    return anual


def construir() -> pd.DataFrame:
    transacciones = pd.read_csv(TRANSACCIONES_FILE, dtype={"cod_ine": str})
    parque = pd.read_csv(PARQUE_FILE, dtype={"cod_ine": str})
    renta = pd.read_csv(RENTA_FILE, dtype={"cod_ine": str})
    catastro = pd.read_csv(CATASTRO_FILE, dtype={"cod_ine": str})

    anual_tx = (
        transacciones.groupby(["cod_ine", "anio"], as_index=False)
        .agg(compraventas=("compraventas", "sum"), trimestres_tx=("trimestre", "nunique"))
    )
    # El año en curso no entra mientras no estén publicados sus cuatro trimestres.
    anual_tx = anual_tx[anual_tx["trimestres_tx"] == 4].copy()
    anual_tx = anual_tx.merge(
        parque[["cod_ine", "anio_referencia", "viviendas"]],
        on="cod_ine",
        how="inner",
        validate="many_to_one",
    )
    anual_tx["tasa_rotacion"] = 100 * anual_tx["compraventas"] / anual_tx["viviendas"]

    renta["anio"] = pd.to_numeric(renta["anio"], errors="raise").astype(int)
    renta["renta_media"] = pd.to_numeric(renta["renta_media"], errors="coerce")
    renta = renta.sort_values(["cod_ine", "anio"])
    renta["crecimiento_renta"] = renta.groupby("cod_ine")["renta_media"].pct_change(
        fill_method=None
    )

    resultado = (
        anual_tx.merge(precios_anuales(), on=["cod_ine", "anio"], how="inner")
        .merge(
            renta[["cod_ine", "anio", "renta_media", "crecimiento_renta"]],
            on=["cod_ine", "anio"],
            how="left",
            validate="one_to_one",
        )
    )
    resultado["desacoplamiento_precio_renta"] = (
        resultado["crecimiento_precio"] - resultado["crecimiento_renta"]
    )

    catastro["pct_propiedad_sociedades"] = (
        100 * catastro["inmuebles_sociedades"] / catastro["inmuebles_total"]
    )
    catastro = catastro.sort_values(["cod_ine", "anio"])
    catastro["variacion_propiedad_sociedades"] = catastro.groupby("cod_ine")[
        "pct_propiedad_sociedades"
    ].diff()
    resultado = resultado.merge(
        catastro[
            [
                "cod_ine",
                "anio",
                "pct_propiedad_sociedades",
                "variacion_propiedad_sociedades",
            ]
        ],
        on=["cod_ine", "anio"],
        how="left",
        validate="one_to_one",
    )
    resultado["elegible_score_principal"] = resultado[
        ["tasa_rotacion", "aceleracion_precio", "desacoplamiento_precio_renta"]
    ].notna().all(axis=1)
    columnas = [
        "cod_ine",
        "anio",
        "compraventas",
        "trimestres_tx",
        "viviendas",
        "anio_referencia",
        "tasa_rotacion",
        "precio_m2",
        "trimestres_precio",
        "crecimiento_precio",
        "aceleracion_precio",
        "renta_media",
        "crecimiento_renta",
        "desacoplamiento_precio_renta",
        "pct_propiedad_sociedades",
        "variacion_propiedad_sociedades",
        "elegible_score_principal",
    ]
    resultado = resultado[columnas].sort_values(["anio", "cod_ine"]).reset_index(drop=True)
    validar(resultado)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    resultado.to_csv(OUT_FILE, index=False)
    print(
        f"Indicadores: {len(resultado):,} filas; "
        f"{resultado.cod_ine.nunique()}/306 municipios"
    )
    return resultado


def validar(df: pd.DataFrame) -> None:
    if df.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("Duplicados municipio-año en indicadores")
    if not df["tasa_rotacion"].ge(0).all():
        raise ValueError("Tasas de rotación negativas")
    if not df["pct_propiedad_sociedades"].dropna().between(0, 100).all():
        raise ValueError("Porcentaje de propiedad societaria fuera de rango")
    cobertura_score = (
        df[df["elegible_score_principal"]]
        .groupby("anio")["cod_ine"]
        .nunique()
    )
    completos = cobertura_score[cobertura_score == 306].index.tolist()
    if not completos:
        raise ValueError("Ningún año permite un score comparable 306/306")
    cobertura_catastro = df.groupby("anio")["pct_propiedad_sociedades"].count()
    if not cobertura_catastro.reindex([2024, 2025]).fillna(0).eq(289).all():
        raise ValueError(
            "La titularidad complementaria no conserva la cobertura esperada 289/306"
        )
    print(f"Años elegibles con cobertura nacional: {completos}")


def cargar_postgresql(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    temporal = "_indicadores_especulativos_carga"
    columnas = list(df.columns)
    updates = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in columnas if c not in ("cod_ine", "anio")
    )
    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(
            text(
                f"INSERT INTO indicadores_especulativos ({','.join(columnas)}) "
                f"SELECT {','.join(columnas)} FROM {temporal} "
                f"ON CONFLICT (cod_ine,anio) DO UPDATE SET {updates}"
            )
        )
        conn.execute(text(f"DROP TABLE {temporal}"))
    print("Carga indicadores_especulativos completada")


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
