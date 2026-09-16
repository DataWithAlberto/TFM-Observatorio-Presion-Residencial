#!/usr/bin/env python3
"""Construye el IPR observado y prospectivo 2023 sin modificar las capas."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine, text

from analytics.normalization import percentil

UNIVERSO = 306
ANIO = 2023
MES_TURISMO = 8
VERSION = "2.0"
OUT = Path("data/processed")
SQL_FILE = Path("sql/18_indice_presion_residencial.sql")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"

CAPAS = ["asequibilidad", "turismo", "especulacion", "gentrificacion", "riesgo_futuro"]
PESOS_BASE = {
    "asequibilidad": 0.30,
    "turismo": 0.20,
    "especulacion": 0.20,
    "gentrificacion": 0.15,
    "riesgo_futuro": 0.15,
}
ESCENARIOS = {
    "base_30_20_20_15_15": PESOS_BASE,
    "pesos_iguales": dict.fromkeys(CAPAS, 0.20),
    "enfasis_asequibilidad": {
        "asequibilidad": 0.40, "turismo": 0.15, "especulacion": 0.15,
        "gentrificacion": 0.15, "riesgo_futuro": 0.15,
    },
    "enfasis_turismo": {
        "asequibilidad": 0.20, "turismo": 0.35, "especulacion": 0.15,
        "gentrificacion": 0.15, "riesgo_futuro": 0.15,
    },
    "enfasis_especulacion": {
        "asequibilidad": 0.20, "turismo": 0.15, "especulacion": 0.35,
        "gentrificacion": 0.15, "riesgo_futuro": 0.15,
    },
    "sin_riesgo_futuro": {
        "asequibilidad": 0.35, "turismo": 0.25, "especulacion": 0.20,
        "gentrificacion": 0.20, "riesgo_futuro": 0.00,
    },
}


def cargar_matriz() -> pd.DataFrame:
    municipios = gpd.read_file(
        "data/raw/municipios_306_con_geometria.gpkg", ignore_geometry=True
    )
    municipios["cod_ine"] = municipios["cod_ine"].astype(str).str.zfill(5)
    columnas = ["cod_ine", "nombre"]
    if "provincia" in municipios:
        columnas.append("provincia")
    base = municipios[columnas].drop_duplicates("cod_ine")
    if len(base) != UNIVERSO:
        raise ValueError(f"Universo geográfico inesperado: {len(base)}")

    configuracion = {
        "asequibilidad": (
            "data/processed/indicadores_asequibilidad.csv",
            "puntuacion_asequibilidad", "anio",
        ),
        "turismo": (
            "data/processed/presion_turistica_score.csv",
            "score_presion_turistica", "fecha",
        ),
        "especulacion": (
            "data/processed/presion_especulativa_score.csv",
            "score_presion_especulativa", "anio",
        ),
        "gentrificacion": (
            "data/processed/riesgo_gentrificacion_score.csv",
            "score_riesgo_gentrificacion", "anio",
        ),
        "riesgo_futuro": (
            "data/processed/riesgo_futuro_residencial_score.csv",
            "score_riesgo_futuro", "anio_base",
        ),
    }
    for capa, (ruta, score, periodo) in configuracion.items():
        df = pd.read_csv(ruta, dtype={"cod_ine": str})
        df["cod_ine"] = df["cod_ine"].str.zfill(5)
        if periodo == "fecha":
            fecha = pd.to_datetime(df["fecha"], errors="coerce")
            df = df[fecha.dt.year.eq(ANIO) & fecha.dt.month.eq(MES_TURISMO)]
        else:
            df = df[pd.to_numeric(df[periodo], errors="coerce").eq(ANIO)]
        if capa == "riesgo_futuro":
            version = df.get("version_metodologia", pd.Series(dtype=str)).astype(str)
            tipo = df.get("tipo_valor_climatico", pd.Series(dtype=str))
            if not version.eq("2.0").all() or not tipo.eq("ANOMALY").all():
                raise ValueError(
                    "El IPR exige riesgo futuro versión 2.0 y valor ANOMALY"
                )
        if df["cod_ine"].duplicated().any():
            raise ValueError(f"{capa}: claves duplicadas en el corte seleccionado")
        df[score] = pd.to_numeric(df[score], errors="coerce")
        base = base.merge(
            df[["cod_ine", score]].rename(columns={score: f"score_origen_{capa}"}),
            on="cod_ine", how="left", validate="one_to_one",
        )

    # La capa original expresa asequibilidad, no presión: 100 significa más
    # asequible. La inversión se realiza solo en esta tabla derivada.
    base["score_orientado_asequibilidad"] = 100 - base["score_origen_asequibilidad"]
    for capa in CAPAS[1:]:
        base[f"score_orientado_{capa}"] = base[f"score_origen_{capa}"]
    for capa in CAPAS:
        base[f"score_normalizado_{capa}"] = percentil(
            base[f"score_orientado_{capa}"]
        )
    return base.sort_values("cod_ine").reset_index(drop=True)


def suma_ponderada(df: pd.DataFrame, pesos: dict[str, float]) -> pd.Series:
    if not np.isclose(sum(pesos.values()), 1):
        raise ValueError("Los pesos deben sumar 1")
    return sum(df[f"score_normalizado_{c}"] * pesos[c] for c in CAPAS)


def categoria_relativa(percentiles: pd.Series) -> pd.Categorical:
    return pd.cut(
        percentiles,
        bins=[-np.inf, 20, 40, 60, 80, np.inf],
        labels=["muy_baja", "baja", "media", "alta", "muy_alta"],
        include_lowest=True,
    )


def construir_resultados(matriz: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    completos = matriz[[f"score_normalizado_{c}" for c in CAPAS]].notna().all(axis=1)
    principal = matriz.copy()
    principal["anio"] = ANIO
    principal["mes_turismo"] = MES_TURISMO
    principal["capas_validas"] = matriz[
        [f"score_normalizado_{c}" for c in CAPAS]
    ].notna().sum(axis=1)
    principal["elegible_ipr5_prospectivo"] = completos
    principal["ipr5_prospectivo"] = np.where(
        completos, suma_ponderada(matriz, PESOS_BASE), np.nan
    )
    principal["percentil_ipr5_prospectivo"] = percentil(
        principal["ipr5_prospectivo"]
    )
    principal["categoria_ipr5_prospectivo"] = categoria_relativa(
        principal["percentil_ipr5_prospectivo"]
    )
    principal["ranking_ipr5_prospectivo"] = principal["ipr5_prospectivo"].rank(
        ascending=False, method="min"
    ).astype("Int64")
    for capa, peso in PESOS_BASE.items():
        principal[f"peso_{capa}"] = peso
        principal[f"contribucion_{capa}"] = (
            principal[f"score_normalizado_{capa}"] * peso
        )

    # Producto nacional distinto: cuatro capas observadas y pesos fijos
    # renormalizados una sola vez para todos los 306 municipios.
    pesos4 = {c: PESOS_BASE[c] for c in CAPAS[:-1]}
    total4 = sum(pesos4.values())
    pesos4 = {c: p / total4 for c, p in pesos4.items()}
    principal["ipr4_nacional_observado"] = sum(
        principal[f"score_normalizado_{c}"] * pesos4[c] for c in CAPAS[:-1]
    )
    principal["percentil_ipr4"] = percentil(principal["ipr4_nacional_observado"])
    principal["categoria_ipr4"] = categoria_relativa(principal["percentil_ipr4"])
    principal["ranking_ipr4"] = principal["ipr4_nacional_observado"].rank(
        ascending=False, method="min"
    ).astype("Int64")
    principal["ipr5_cota_inferior"] = sum(
        principal[f"score_normalizado_{c}"] * PESOS_BASE[c] for c in CAPAS[:-1]
    )
    principal["ipr5_cota_superior"] = principal["ipr5_cota_inferior"] + 100 * PESOS_BASE["riesgo_futuro"]
    principal["metodo"] = (
        "ipr4_observado_e_ipr5_prospectivo_percentiles_2023_30_20_20_15_15"
    )
    principal["version_metodologia"] = VERSION

    sensibilidad = []
    completos_df = principal[completos].copy()
    base = completos_df["ipr5_prospectivo"]
    ranking_base = base.rank(ascending=False, method="average")
    top_base = set(completos_df.loc[ranking_base.le(np.ceil(len(completos_df) * 0.10)), "cod_ine"])
    for escenario, pesos in ESCENARIOS.items():
        score = suma_ponderada(completos_df, pesos)
        ranking = score.rank(ascending=False, method="average")
        top = set(completos_df.loc[ranking.le(np.ceil(len(completos_df) * 0.10)), "cod_ine"])
        sensibilidad.append(
            {
                "escenario": escenario,
                **{f"peso_{c}": pesos[c] for c in CAPAS},
                "municipios": len(score),
                "spearman_score_base": score.corr(base, method="spearman"),
                "cambio_rango_medio": (ranking - ranking_base).abs().mean(),
                "cambio_rango_maximo": (ranking - ranking_base).abs().max(),
                "solapamiento_top_10_pct": len(top & top_base) / len(top_base),
            }
        )
    return principal, pd.DataFrame(sensibilidad)


def diagnosticos(matriz: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    columnas = [f"score_normalizado_{c}" for c in CAPAS]
    x = matriz[columnas].dropna()
    correlaciones = []
    for metodo in ("pearson", "spearman"):
        corr = x.corr(method=metodo)
        for fila in CAPAS:
            for columna in CAPAS:
                correlaciones.append(
                    {"metodo": metodo, "capa_fila": fila, "capa_columna": columna,
                     "correlacion": corr.loc[f"score_normalizado_{fila}", f"score_normalizado_{columna}"]}
                )

    vif = []
    for i, capa in enumerate(CAPAS):
        y = x.iloc[:, i]
        predictores = x.drop(columns=x.columns[i])
        r2 = LinearRegression().fit(predictores, y).score(predictores, y)
        vif.append({"capa": capa, "r2_auxiliar": r2, "vif": 1 / (1 - r2)})

    z = StandardScaler().fit_transform(x)
    pca = PCA().fit(z)
    pca_rows = []
    for i, varianza in enumerate(pca.explained_variance_ratio_):
        fila = {"componente": i + 1, "varianza_explicada": varianza,
                "varianza_acumulada": pca.explained_variance_ratio_[: i + 1].sum()}
        fila.update({f"carga_{c}": pca.components_[i, j] for j, c in enumerate(CAPAS)})
        pca_rows.append(fila)
    return pd.DataFrame(correlaciones), pd.DataFrame(vif), pd.DataFrame(pca_rows)


def resumen_estadistico(resultados: pd.DataFrame) -> pd.DataFrame:
    variables = (
        [f"score_origen_{c}" for c in CAPAS]
        + [f"score_normalizado_{c}" for c in CAPAS]
        + ["ipr5_prospectivo", "ipr4_nacional_observado"]
    )
    filas = []
    for variable in variables:
        s = resultados[variable]
        filas.append({
            "variable": variable, "n": s.notna().sum(), "n_nulos": s.isna().sum(),
            "media": s.mean(), "desviacion": s.std(), "min": s.min(),
            "p25": s.quantile(.25), "mediana": s.median(),
            "p75": s.quantile(.75), "max": s.max(),
        })
    return pd.DataFrame(filas)


def guardar_y_cargar(
    resultados: pd.DataFrame,
    sensibilidad: pd.DataFrame,
    correlaciones: pd.DataFrame,
    vif: pd.DataFrame,
    pca: pd.DataFrame,
    no_db: bool,
    db_url: str,
) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    resultados.to_csv(OUT / "indice_presion_residencial_2023.csv", index=False)
    resultados.sort_values(
        ["elegible_ipr5_prospectivo", "ipr5_prospectivo"],
        ascending=[False, False],
    ).to_csv(OUT / "ranking_ipr5_prospectivo_2023.csv", index=False)
    sensibilidad.to_csv(OUT / "ipr_sensibilidad_pesos.csv", index=False)
    correlaciones.to_csv(OUT / "ipr_correlaciones.csv", index=False)
    vif.to_csv(OUT / "ipr_vif.csv", index=False)
    pca.to_csv(OUT / "ipr_pca_contraste.csv", index=False)
    resumen_estadistico(resultados).to_csv(
        OUT / "ipr_resumen_estadistico.csv", index=False
    )
    if no_db:
        return
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text())
        conn.execute(text("DELETE FROM indice_presion_residencial WHERE anio = :anio"), {"anio": ANIO})
        resultados.to_sql("_ipr_carga", conn, if_exists="replace", index=False)
        columnas = list(resultados.columns)
        conn.execute(text(
            f"INSERT INTO indice_presion_residencial ({','.join(columnas)}) "
            f"SELECT {','.join(columnas)} FROM _ipr_carga"
        ))
        conn.execute(text("DROP TABLE _ipr_carga"))
        conn.execute(text("DELETE FROM ipr_sensibilidad_pesos WHERE anio = :anio"), {"anio": ANIO})
        sensibilidad.assign(anio=ANIO).to_sql(
            "ipr_sensibilidad_pesos", conn, if_exists="append", index=False
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    matriz = cargar_matriz()
    resultados, sensibilidad = construir_resultados(matriz)
    correlaciones, vif, pca = diagnosticos(matriz)
    guardar_y_cargar(
        resultados, sensibilidad, correlaciones, vif, pca, args.no_db, args.db_url
    )
    print(json.dumps({
        "filas": len(resultados),
        "ipr5_prospectivo_elegibles": int(
            resultados["elegible_ipr5_prospectivo"].sum()
        ),
        "ipr4_nacional": int(resultados["ipr4_nacional_observado"].notna().sum()),
        "vif_max": round(float(vif["vif"].max()), 3),
        "sensibilidad_spearman_min": round(float(sensibilidad["spearman_score_base"].min()), 3),
    }, indent=2))


if __name__ == "__main__":
    main()
