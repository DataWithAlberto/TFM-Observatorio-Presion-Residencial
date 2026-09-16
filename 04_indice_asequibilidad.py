#!/usr/bin/env python3
"""Cálculo y carga del indicador municipal de asequibilidad residencial.

Ratio = (precio anual ponderado por m² × superficie de referencia) /
        renta neta media anual por hogar

La puntuación es el percentil invertido del ratio dentro de cada año:
100 representa mayor asequibilidad relativa y 0 menor asequibilidad.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

PRECIOS_FILE = Path("data/processed/precios_vivienda_ministerio_final.csv")
RENTA_FILE = Path("data/processed/renta_hogares.csv")
MUNICIPIOS_FILE = Path("data/processed/municipios_ine.csv")
OUT_FILE = Path("data/processed/indicadores_asequibilidad.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
SQL_FILE = Path("database/bootstrap/01_serving_tables.sql")
SUPERFICIE_REFERENCIA_M2 = 90.0
METODO_NORMALIZACION = "percentil_invertido_anual"


def _media_ponderada(grupo: pd.DataFrame) -> float:
    valores = grupo["precio_m2"].to_numpy(dtype=float)
    pesos = grupo["num_tasaciones"].fillna(0).to_numpy(dtype=float)
    validos = np.isfinite(valores)
    if not validos.any():
        return float("nan")
    if pesos[validos].sum() > 0:
        return float(np.average(valores[validos], weights=pesos[validos]))
    return float(np.mean(valores[validos]))


def preparar_precios(ruta: Path = PRECIOS_FILE) -> pd.DataFrame:
    precios = pd.read_csv(ruta, dtype={"id_municipio": str})
    precios["cod_ine"] = precios["id_municipio"].str.zfill(5)
    precios["anio"] = pd.to_datetime(precios["fecha"], errors="coerce").dt.year
    precios["precio_m2"] = pd.to_numeric(precios["valor_total"], errors="coerce")
    precios["num_tasaciones"] = pd.to_numeric(precios["num_tasaciones"], errors="coerce")
    precios = precios.dropna(subset=["cod_ine", "anio", "precio_m2"])
    precios = precios[precios["precio_m2"] > 0].copy()

    anual = (
        precios.groupby(["cod_ine", "anio"], as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "precio_m2": _media_ponderada(g),
                    "num_tasaciones": g["num_tasaciones"].sum(min_count=1),
                    "trimestres_disponibles": g["fecha"].nunique(),
                }
            ),
            include_groups=False,
        )
        .reset_index(drop=True)
    )
    anual["anio"] = anual["anio"].astype(int)
    anual["num_tasaciones"] = anual["num_tasaciones"].round().astype("Int64")
    anual["trimestres_disponibles"] = anual["trimestres_disponibles"].astype(int)
    return anual


def calcular_indicador(
    precios_anuales: pd.DataFrame,
    renta: pd.DataFrame,
    superficie_m2: float = SUPERFICIE_REFERENCIA_M2,
) -> pd.DataFrame:
    if superficie_m2 <= 0:
        raise ValueError("La superficie de referencia debe ser positiva")
    renta = renta.copy()
    renta["cod_ine"] = renta["cod_ine"].astype(str).str.zfill(5)
    renta["anio"] = pd.to_numeric(renta["anio"], errors="raise").astype(int)
    renta["renta_media"] = pd.to_numeric(renta["renta_media"], errors="coerce")

    resultado = precios_anuales.merge(
        renta[["cod_ine", "anio", "renta_media"]],
        on=["cod_ine", "anio"],
        how="inner",
        validate="one_to_one",
    )
    resultado["superficie_ref_m2"] = float(superficie_m2)
    resultado["precio_vivienda"] = resultado["precio_m2"] * superficie_m2
    resultado["ratio_asequibilidad"] = (
        resultado["precio_vivienda"] / resultado["renta_media"]
    )

    # Percentil empírico invertido: el menor ratio recibe 100 y el mayor 0.
    # ``average`` trata los empates de forma simétrica.
    grupos = resultado.groupby("anio")["ratio_asequibilidad"]
    rango = grupos.rank(method="average", ascending=True)
    n = grupos.transform("size")
    resultado["puntuacion_asequibilidad"] = np.where(
        n > 1, 100 * (n - rango) / (n - 1), 100.0
    )
    resultado["metodo_normalizacion"] = METODO_NORMALIZACION
    resultado["fuente_precio"] = "Ministerio de Vivienda, valor tasado"
    resultado["fuente_renta"] = "INE, Atlas de distribución de renta de los hogares"

    columnas = [
        "cod_ine",
        "anio",
        "precio_m2",
        "num_tasaciones",
        "trimestres_disponibles",
        "renta_media",
        "superficie_ref_m2",
        "precio_vivienda",
        "ratio_asequibilidad",
        "puntuacion_asequibilidad",
        "metodo_normalizacion",
        "fuente_precio",
        "fuente_renta",
    ]
    resultado = resultado[columnas].sort_values(["anio", "cod_ine"]).reset_index(drop=True)
    if resultado.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("El indicador contiene duplicados municipio-año")
    return resultado


def validar_municipios(
    indicador: pd.DataFrame, municipios_file: Path = MUNICIPIOS_FILE
) -> pd.DataFrame:
    municipios = pd.read_csv(municipios_file, dtype={"id_municipio": str})
    nombres = municipios[["id_municipio", "nombre"]].rename(
        columns={"id_municipio": "cod_ine"}
    )
    nombres["cod_ine"] = nombres["cod_ine"].str.zfill(5)
    conocidos = {
        "Madrid": "28079",
        "Barcelona": "08019",
        "Gijón": "33024",
        "Valencia": "46250",
    }
    ultimo = indicador["anio"].max()
    validacion = indicador[
        (indicador["anio"] == ultimo) & indicador["cod_ine"].isin(conocidos.values())
    ].merge(nombres, on="cod_ine", how="left")
    validacion["municipio_validacion"] = validacion["cod_ine"].map(
        {codigo: nombre for nombre, codigo in conocidos.items()}
    )
    validacion = validacion[
        [
            "municipio_validacion",
            "cod_ine",
            "anio",
            "precio_m2",
            "renta_media",
            "ratio_asequibilidad",
            "puntuacion_asequibilidad",
        ]
    ].sort_values("ratio_asequibilidad", ascending=False)
    faltan = set(conocidos).difference(validacion["municipio_validacion"])
    if faltan:
        raise ValueError(f"Sin indicador para municipios de validación: {sorted(faltan)}")
    print(f"\nValidación de municipios (último año común: {ultimo}):")
    print(validacion.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    return validacion


def cargar_postgresql(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    temporal = "_indicadores_asequibilidad_carga"
    columnas = list(df.columns)
    actualizaciones = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in columnas if col not in ("cod_ine", "anio")
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text(encoding="utf-8"))
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(
            text(
                f"""
                INSERT INTO indicadores_asequibilidad ({", ".join(columnas)})
                SELECT {", ".join(columnas)} FROM {temporal}
                ON CONFLICT (cod_ine, anio) DO UPDATE SET {actualizaciones}
                """
            )
        )
        conn.execute(text(f"DROP TABLE {temporal}"))
    print(f"Cargadas/actualizadas {len(df):,} filas en indicadores_asequibilidad")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--superficie-m2", type=float, default=SUPERFICIE_REFERENCIA_M2)
    parser.add_argument("--no-db", action="store_true", help="No cargar PostgreSQL")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()

    precios = preparar_precios()
    renta = pd.read_csv(RENTA_FILE, dtype={"cod_ine": str})
    indicador = calcular_indicador(precios, renta, args.superficie_m2)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    indicador.to_csv(OUT_FILE, index=False)
    print(
        f"Indicador generado: {len(indicador):,} filas, "
        f"{indicador['cod_ine'].nunique():,} municipios"
    )
    print(f"Guardado: {OUT_FILE}")
    validar_municipios(indicador)
    if not args.no_db:
        cargar_postgresql(indicador, args.db_url)


if __name__ == "__main__":
    main()
