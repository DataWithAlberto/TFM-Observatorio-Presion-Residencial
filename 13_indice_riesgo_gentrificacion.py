#!/usr/bin/env python3
"""Calcula y audita el índice municipal de riesgo de gentrificación (0–100)."""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

INDICADORES_FILE = Path("data/processed/indicadores_gentrificacion.csv")
MUNICIPIOS_FILE = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_SCORE = Path("data/processed/riesgo_gentrificacion_score.csv")
OUT_CORR = Path("data/processed/gentrificacion_correlaciones.csv")
OUT_SENS = Path("data/processed/gentrificacion_sensibilidad.csv")
OUT_VALIDACION = Path("data/processed/gentrificacion_validacion_externa.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
SQL_FILE = Path("sql/11_gentrificacion.sql")
COBERTURA_MINIMA = 0.90
VARIABLES = {
    "cambio_socioeconomico": "log_cambio_renta_neta_media_persona_3a",
    "presion_residencial": "brecha_precio_renta_3a",
    "transformacion_hogares": "transformacion_hogares_ajustada_3a",
}
ESCENARIOS = {
    "iguales": (1 / 3, 1 / 3, 1 / 3),
    "residencial_50": (0.25, 0.50, 0.25),
    "hogares_50": (0.25, 0.25, 0.50),
    "socioeconomico_50": (0.50, 0.25, 0.25),
}


def _winsorizar_percentil(serie: pd.Series) -> tuple[pd.Series, pd.Series]:
    inferior, superior = serie.quantile([0.01, 0.99])
    winsor = serie.clip(inferior, superior)
    if winsor.nunique() <= 1:
        percentil = pd.Series(50.0, index=serie.index)
    else:
        percentil = (
            100 * (winsor.rank(method="average") - 1) / (winsor.notna().sum() - 1)
        )
    return winsor, percentil


def calcular() -> pd.DataFrame:
    df = pd.read_csv(INDICADORES_FILE, dtype={"cod_ine": str})
    cobertura = df[df["elegible_score"]].groupby("anio")["cod_ine"].nunique()
    minimo = math.ceil(306 * COBERTURA_MINIMA)
    anios = cobertura[cobertura >= minimo].index
    base = df[df["anio"].isin(anios) & df["elegible_score"]].copy()
    if base.empty:
        raise ValueError("No hay años completos para calcular el índice")

    salida = base[["cod_ine", "anio"] + list(VARIABLES.values())].copy()
    for _, variable in VARIABLES.items():
        partes = []
        for _, grupo in salida.groupby("anio"):
            winsor, percentil = _winsorizar_percentil(grupo[variable])
            partes.append(
                pd.DataFrame(
                    {
                        "indice": grupo.index,
                        f"winsor_{variable}": winsor,
                        f"percentil_{variable}": percentil,
                    }
                )
            )
        transformado = pd.concat(partes).set_index("indice")
        salida.loc[transformado.index, f"winsor_{variable}"] = transformado[
            f"winsor_{variable}"
        ]
        salida.loc[transformado.index, f"percentil_{variable}"] = transformado[
            f"percentil_{variable}"
        ]

    percentiles = [f"percentil_{v}" for v in VARIABLES.values()]
    salida["score_riesgo_gentrificacion"] = salida[percentiles].mean(axis=1)
    salida["municipios_cobertura_anio"] = salida["anio"].map(
        salida.groupby("anio")["cod_ine"].nunique()
    )
    salida["pct_cobertura_anio"] = (
        100 * salida["municipios_cobertura_anio"] / 306
    )
    salida["panel_completo_306"] = salida["municipios_cobertura_anio"].eq(306)
    salida["universo_normalizacion"] = "municipios_observados_anio"
    salida["metodo"] = "media_percentiles_winsorizados_p01_p99"
    salida["version_metodologia"] = "2.0"
    salida = salida.sort_values(["anio", "cod_ine"]).reset_index(drop=True)
    validar(salida)
    auditar(salida)
    validar_referencias(salida)
    OUT_SCORE.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT_SCORE, index=False)
    return salida


def auditar(score: pd.DataFrame) -> None:
    corr_partes = []
    sens_partes = []
    originales = list(VARIABLES.values())
    percentiles = [f"percentil_{v}" for v in originales]
    for anio, grupo in score.groupby("anio"):
        corr = grupo[originales].corr(method="spearman")
        largo = corr.stack().rename("correlacion_spearman").reset_index()
        largo.columns = ["variable_1", "variable_2", "correlacion_spearman"]
        largo["anio"] = anio
        corr_partes.append(largo)

        estandar = StandardScaler().fit_transform(grupo[originales])
        pca = PCA().fit(estandar)
        referencia = grupo["score_riesgo_gentrificacion"]
        n_top = max(1, int(np.ceil(len(grupo) * 0.10)))
        top_ref = set(grupo.nlargest(n_top, "score_riesgo_gentrificacion").cod_ine)
        for nombre, pesos in ESCENARIOS.items():
            alternativo = grupo[percentiles].mul(pesos).sum(axis=1)
            top_alt = set(grupo.loc[alternativo.nlargest(n_top).index, "cod_ine"])
            sens_partes.append(
                {
                    "anio": anio,
                    "escenario": nombre,
                    "rho_spearman_score_base": referencia.corr(
                        alternativo, method="spearman"
                    ),
                    "solapamiento_top_10_pct": len(top_ref & top_alt) / n_top,
                    "varianza_pca_componente_1": pca.explained_variance_ratio_[0],
                    "varianza_pca_acumulada_2": pca.explained_variance_ratio_[:2].sum(),
                }
            )
    pd.concat(corr_partes, ignore_index=True).to_csv(OUT_CORR, index=False)
    pd.DataFrame(sens_partes).to_csv(OUT_SENS, index=False)
    indicadores = pd.read_csv(INDICADORES_FILE, dtype={"cod_ine": str})
    contraste = score.merge(
        indicadores[
            [
                "cod_ine",
                "anio",
                "sustitucion_composicion_renta_3a",
                "salida_interior_por_1000_3a",
            ]
        ],
        on=["cod_ine", "anio"],
        how="left",
        validate="one_to_one",
    )
    filas_validacion = []
    for anio, grupo in contraste.groupby("anio"):
        for variable in (
            "sustitucion_composicion_renta_3a",
            "salida_interior_por_1000_3a",
        ):
            disponibles = grupo[
                ["score_riesgo_gentrificacion", variable]
            ].dropna()
            if len(disponibles) >= 20:
                filas_validacion.append(
                    {
                        "anio": anio,
                        "variable_contraste": variable,
                        "n": len(disponibles),
                        "rho_spearman": disponibles[
                            "score_riesgo_gentrificacion"
                        ].corr(disponibles[variable], method="spearman"),
                    }
                )
    pd.DataFrame(filas_validacion).to_csv(OUT_VALIDACION, index=False)
    print(f"Auditorías: {OUT_CORR}, {OUT_SENS} y {OUT_VALIDACION}")


def validar(df: pd.DataFrame) -> None:
    if df.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("Duplicados en score")
    cobertura = df.groupby("anio")["cod_ine"].nunique()
    minimo = math.ceil(306 * COBERTURA_MINIMA)
    if not cobertura.ge(minimo).all():
        raise ValueError(f"Cobertura inferior al 90%: {cobertura.to_dict()}")
    if not df.groupby("anio")["municipios_cobertura_anio"].nunique().eq(1).all():
        raise ValueError("Metadato de cobertura inconsistente")
    if not df["score_riesgo_gentrificacion"].between(0, 100).all():
        raise ValueError("Score fuera de rango")
    correlaciones = []
    for _, g in df.groupby("anio"):
        c = g[list(VARIABLES.values())].corr(method="spearman")
        correlaciones.extend(
            abs(c.iloc[i, j])
            for i in range(len(c))
            for j in range(i + 1, len(c))
        )
    if max(correlaciones) >= 0.90:
        raise ValueError(f"Redundancia excesiva entre variables: {max(correlaciones):.3f}")


def validar_referencias(score: pd.DataFrame) -> None:
    import geopandas as gpd

    municipios = gpd.read_file(MUNICIPIOS_FILE, ignore_geometry=True)[
        ["cod_ine", "nombre"]
    ]
    municipios["cod_ine"] = municipios["cod_ine"].astype(str).str.zfill(5)
    codigos = [
        "28079",  # Madrid
        "08019",  # Barcelona
        "29067",  # Málaga
        "33024",  # Gijón
        "48020",  # Bilbao
        "13034",  # Ciudad Real
        "48084",  # Sestao
    ]
    ultimo = score["anio"].max()
    muestra = score[
        (score["anio"] == ultimo) & score["cod_ine"].isin(codigos)
    ].merge(municipios, on="cod_ine", how="left", validate="one_to_one")
    if len(muestra) != len(codigos):
        raise ValueError("Faltan municipios de referencia")
    print(f"\nCasos de referencia ({ultimo}):")
    print(
        muestra[
            ["nombre", *VARIABLES.values(), "score_riesgo_gentrificacion"]
        ]
        .sort_values("score_riesgo_gentrificacion", ascending=False)
        .to_string(index=False, float_format=lambda x: f"{x:.3f}")
    )


def cargar(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    tabla = "riesgo_gentrificacion_score"
    temporal = f"_{tabla}_carga"
    columnas = list(df.columns)
    actualizaciones = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in columnas if c not in ("cod_ine", "anio")
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text())
        conn.execute(text(f"DELETE FROM {tabla}"))
        conn.execute(text(f"DROP TABLE IF EXISTS {temporal}"))
        df.to_sql(temporal, conn, if_exists="replace", index=False, method="multi")
        conn.execute(
            text(
                f"INSERT INTO {tabla} ({','.join(columnas)}) "
                f"SELECT {','.join(columnas)} FROM {temporal} "
                f"ON CONFLICT (cod_ine,anio) DO UPDATE SET {actualizaciones}"
            )
        )
        conn.execute(text(f"DROP TABLE {temporal}"))
    print(f"Cargada tabla {tabla}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    score = calcular()
    print(
        f"Score: {len(score):,} filas; años {score.anio.min()}–{score.anio.max()}; "
        f"cobertura {score.groupby('anio').cod_ine.nunique().to_dict()}"
    )
    if not args.no_db:
        cargar(score, args.db_url)


if __name__ == "__main__":
    main()
