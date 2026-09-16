#!/usr/bin/env python3
"""Construye indicadores climáticos y tendencias de presión residencial."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CLIMA_FILE = Path("data/raw/riesgo_futuro/adaptecca_proyecciones_municipales.csv")
OUT_FILE = Path("data/processed/indicadores_riesgo_futuro.csv")
ANIO_BASE = 2023
MES_TURISMO = 8
CAPAS = {
    "asequibilidad": (
        Path("data/processed/indicadores_asequibilidad.csv"),
        "anio",
        "puntuacion_asequibilidad",
    ),
    "turismo": (
        Path("data/processed/presion_turistica_score.csv"),
        "fecha",
        "score_presion_turistica",
    ),
    "especulacion": (
        Path("data/processed/presion_especulativa_score.csv"),
        "anio",
        "score_presion_especulativa",
    ),
    "gentrificacion": (
        Path("data/processed/riesgo_gentrificacion_score.csv"),
        "anio",
        "score_riesgo_gentrificacion",
    ),
}


def pendiente_robusta(grupo: pd.DataFrame, valor: str) -> tuple[float, int, int, int]:
    g = grupo.dropna(subset=["anio", valor]).sort_values("anio")
    g = g.groupby("anio", as_index=False)[valor].mean()
    if len(g) < 3 or g["anio"].nunique() < 3:
        return np.nan, len(g), g["anio"].min() if len(g) else np.nan, g["anio"].max() if len(g) else np.nan
    pendientes = []
    x, y = g["anio"].to_numpy(), g[valor].to_numpy()
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            if x[j] != x[i]:
                pendientes.append((y[j] - y[i]) / (x[j] - x[i]))
    return float(np.median(pendientes)), len(g), int(x.min()), int(x.max())


def preparar_serie_tendencia(
    df: pd.DataFrame, nombre: str, periodo: str, score: str
) -> tuple[pd.DataFrame, str]:
    df = df.copy()
    if periodo == "fecha":
        fechas = pd.to_datetime(df["fecha"], errors="coerce")
        df["anio"] = fechas.dt.year
        # La serie turística comparable fijada por la auditoría es el
        # snapshot de agosto. No se usa información posterior al corte.
        df = df[fechas.dt.month.eq(MES_TURISMO)]
    df = df[pd.to_numeric(df["anio"], errors="coerce").le(ANIO_BASE)].copy()
    if nombre == "asequibilidad":
        # La capa original aumenta con la asequibilidad. Para estimar una
        # tendencia de presión se invierte solo en este cálculo derivado.
        df["_score_presion"] = 100 - pd.to_numeric(df[score], errors="coerce")
        return df, "_score_presion"
    return df, score


def tendencias() -> pd.DataFrame:
    salida = None
    for nombre, (ruta, periodo, score) in CAPAS.items():
        df = pd.read_csv(ruta, dtype={"cod_ine": str})
        df, score_tendencia = preparar_serie_tendencia(
            df, nombre, periodo, score
        )
        registros = []
        for cod_ine, grupo in df.groupby("cod_ine"):
            pendiente, n, inicio, fin = pendiente_robusta(grupo, score_tendencia)
            registros.append(
                {
                    "cod_ine": cod_ine,
                    f"tendencia_{nombre}": pendiente,
                    f"n_anios_{nombre}": n,
                    f"inicio_{nombre}": inicio,
                    f"fin_{nombre}": fin,
                }
            )
        parte = pd.DataFrame(registros)
        salida = parte if salida is None else salida.merge(parte, on="cod_ine", how="outer")
    return salida


def validar_tendencias(df: pd.DataFrame) -> None:
    fines = [c for c in df if c.startswith("fin_")]
    if any(pd.to_numeric(df[c], errors="coerce").dropna().gt(ANIO_BASE).any() for c in fines):
        raise ValueError("Fuga temporal: existe una tendencia posterior al año base")
    if not df["n_anios_turismo"].eq(4).all():
        raise ValueError("Turismo debe usar cuatro snapshots de agosto (2020–2023)")
    if df["tendencia_especulacion"].notna().any():
        raise ValueError("Especulación no permite tendencia con solo 2022–2023")
    if not df["fin_asequibilidad"].eq(ANIO_BASE).all():
        raise ValueError("La tendencia de asequibilidad no termina en 2023")


def clima_futuro() -> pd.DataFrame:
    clima = pd.read_csv(CLIMA_FILE, dtype={"cod_ine": str})
    ventana = clima[clima["anio"].between(2041, 2060)].copy()
    if ventana.empty:
        raise ValueError("AdapteCCa no contiene la ventana 2041–2060")
    resumen = (
        ventana.groupby(["cod_ine", "variable"], as_index=False)
        .agg(
            valor_futuro=("valor_mediana_ensemble", "mean"),
            valor_p25=("valor_p25_ensemble", "mean"),
            valor_p75=("valor_p75_ensemble", "mean"),
            n_anios=("anio", "nunique"),
            n_modelos_mediana=("n_modelos", "median"),
        )
    )
    resumen["incertidumbre_iqr"] = resumen["valor_p75"] - resumen["valor_p25"]
    ancho = resumen.pivot(index="cod_ine", columns="variable", values="valor_futuro")
    ancho.columns = [f"proyeccion_{c}" for c in ancho.columns]
    return ancho.reset_index()


def construir() -> pd.DataFrame:
    tendencias_df = tendencias()
    validar_tendencias(tendencias_df)
    salida = clima_futuro().merge(tendencias_df, on="cod_ine", how="outer")
    salida["anio_base"] = ANIO_BASE
    salida["horizonte_climatico"] = "2041-2060"
    salida["escenario_climatico"] = "SSP2-4.5"
    salida["tipo_valor_climatico"] = "ANOMALY"
    if salida["cod_ine"].nunique() != 306:
        raise ValueError(f"Cobertura final inesperada: {salida.cod_ine.nunique()}/306")
    if salida.duplicated("cod_ine").any():
        raise ValueError("Duplicados por municipio")
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    salida.sort_values("cod_ine").to_csv(OUT_FILE, index=False)
    return salida


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    salida = construir()
    print(f"Indicadores: {len(salida)} municipios; {len(salida.columns)} columnas")
    print(salida.isna().mean().sort_values(ascending=False).head(12).to_string())


if __name__ == "__main__":
    main()
