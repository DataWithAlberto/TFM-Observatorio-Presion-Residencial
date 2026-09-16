#!/usr/bin/env python3
"""Construye indicadores de transformación socioeconómica municipal."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from analytics.normalization import ajustar_hogares

SOCIO_FILE = Path("data/processed/variables_socioeconomicas_municipales.csv")
MIGRACION_FILE = Path("data/processed/saldos_migratorios_municipales.csv")
POBLACION_FILE = Path("data/processed/poblacion_municipal.csv")
PRECIOS_FILE = Path("data/processed/precios_vivienda_ministerio_final.csv")
ASEQUIBILIDAD_FILE = Path("data/processed/indicadores_asequibilidad.csv")
TURISMO_FILE = Path("data/processed/presion_turistica_score.csv")
ESPECULACION_FILE = Path("data/processed/presion_especulativa_score.csv")
OUT_FILE = Path("data/processed/indicadores_gentrificacion.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
SQL_FILE = Path("sql/11_gentrificacion.sql")
VENTANA = 3
COBERTURA_MINIMA = 0.90


def _log_cambio(serie: pd.Series, periodos: int = VENTANA) -> pd.Series:
    anterior = serie.groupby(level=0).shift(periodos)
    return np.log(serie / anterior)


def _precios_anuales() -> pd.DataFrame:
    df = pd.read_csv(PRECIOS_FILE, dtype={"id_municipio": str})
    df["cod_ine"] = df["id_municipio"].str.zfill(5)
    df["anio"] = pd.to_datetime(df["fecha"], errors="coerce").dt.year
    df["precio_m2"] = pd.to_numeric(df["valor_total"], errors="coerce")
    df["num_tasaciones"] = pd.to_numeric(df["num_tasaciones"], errors="coerce").fillna(0)
    df = df.dropna(subset=["cod_ine", "anio", "precio_m2"])
    df = df[df["precio_m2"] > 0].copy()

    def ponderada(g: pd.DataFrame) -> float:
        if g["num_tasaciones"].sum() > 0:
            return float(np.average(g["precio_m2"], weights=g["num_tasaciones"]))
        return float(g["precio_m2"].mean())

    return (
        df.groupby(["cod_ine", "anio"])
        .apply(ponderada, include_groups=False)
        .rename("precio_m2")
        .reset_index()
    )


def construir() -> pd.DataFrame:
    socio = pd.read_csv(SOCIO_FILE, dtype={"cod_ine": str})
    migracion = pd.read_csv(MIGRACION_FILE, dtype={"cod_ine": str})
    poblacion = pd.read_csv(POBLACION_FILE, dtype={"cod_ine": str})
    asequibilidad = pd.read_csv(ASEQUIBILIDAD_FILE, dtype={"cod_ine": str})
    precios = _precios_anuales()

    base = (
        poblacion[["cod_ine", "anio", "poblacion"]]
        .merge(precios, on=["cod_ine", "anio"], how="left", validate="one_to_one")
        .merge(
            socio[
                [
                    "cod_ine",
                    "anio",
                    "renta_neta_media_persona",
                    "renta_neta_media_hogar",
                    "mediana_renta_unidad_consumo",
                    "pct_renta_alta_200",
                    "pct_renta_baja_60",
                    "indice_gini",
                    "ratio_p80_p20",
                    "edad_media",
                    "pct_hogares_unipersonales",
                    "pct_mayor_65",
                    "pct_menor_18",
                    "pct_poblacion_espanola",
                    "tamano_medio_hogar",
                ]
            ],
            on=["cod_ine", "anio"],
            how="left",
            validate="one_to_one",
        )
        .sort_values(["cod_ine", "anio"])
    )
    idx = base.set_index(["cod_ine", "anio"])
    for variable in (
        "poblacion",
        "precio_m2",
        "renta_neta_media_persona",
        "renta_neta_media_hogar",
        "mediana_renta_unidad_consumo",
    ):
        idx[f"log_cambio_{variable}_3a"] = _log_cambio(idx[variable])
    for variable in (
        "pct_renta_alta_200",
        "pct_renta_baja_60",
        "indice_gini",
        "ratio_p80_p20",
        "edad_media",
        "pct_hogares_unipersonales",
        "pct_mayor_65",
        "pct_menor_18",
        "pct_poblacion_espanola",
        "tamano_medio_hogar",
    ):
        idx[f"cambio_{variable}_3a"] = idx.groupby(level=0)[variable].diff(VENTANA)
    base = idx.reset_index()
    base["brecha_precio_renta_3a"] = (
        base["log_cambio_precio_m2_3a"]
        - base["log_cambio_renta_neta_media_persona_3a"]
    )
    base["sustitucion_composicion_renta_3a"] = (
        base["cambio_pct_renta_alta_200_3a"]
        - base["cambio_pct_renta_baja_60_3a"]
    )

    # Residuo de aumento de hogares unipersonales tras descontar los cambios
    # en población mayor de 65 y menor de 18 años. Evita atribuir a
    # transformación urbana lo que puede explicarse únicamente por envejecimiento.
    base["transformacion_hogares_ajustada_3a"] = np.nan
    for anio, grupo in base.groupby("anio"):
        base.loc[grupo.index, "transformacion_hogares_ajustada_3a"] = ajustar_hogares(grupo)

    migracion = migracion.sort_values(["cod_ine", "anio"])
    for variable in ("saldo_total", "saldo_exterior", "saldo_interior"):
        migracion[f"{variable}_acum_3a"] = (
            migracion.groupby("cod_ine")[variable]
            .rolling(VENTANA, min_periods=VENTANA)
            .sum()
            .reset_index(level=0, drop=True)
        )
    base = base.merge(
        migracion[
            [
                "cod_ine",
                "anio",
                "saldo_total_acum_3a",
                "saldo_exterior_acum_3a",
                "saldo_interior_acum_3a",
            ]
        ],
        on=["cod_ine", "anio"],
        how="left",
        validate="one_to_one",
    )
    base["salida_interior_por_1000_3a"] = (
        -1000 * base["saldo_interior_acum_3a"] / base["poblacion"]
    )
    base["saldo_exterior_por_1000_3a"] = (
        1000 * base["saldo_exterior_acum_3a"] / base["poblacion"]
    )

    asequibilidad = asequibilidad[
        ["cod_ine", "anio", "ratio_asequibilidad", "puntuacion_asequibilidad"]
    ]
    base = base.merge(
        asequibilidad, on=["cod_ine", "anio"], how="left", validate="one_to_one"
    )

    # Capas previas: contexto, no componentes del score para evitar doble conteo.
    esp = pd.read_csv(ESPECULACION_FILE, dtype={"cod_ine": str})[
        ["cod_ine", "anio", "score_presion_especulativa"]
    ]
    base = base.merge(esp, on=["cod_ine", "anio"], how="left", validate="one_to_one")
    tur = pd.read_csv(TURISMO_FILE, dtype={"cod_ine": str}, parse_dates=["fecha"])
    tur["anio"] = tur["fecha"].dt.year
    tur = (
        tur.sort_values("fecha")
        .groupby(["cod_ine", "anio"], as_index=False)
        .tail(1)[["cod_ine", "anio", "score_presion_turistica"]]
    )
    base = base.merge(tur, on=["cod_ine", "anio"], how="left", validate="one_to_one")

    principales = [
        "log_cambio_renta_neta_media_persona_3a",
        "brecha_precio_renta_3a",
        "transformacion_hogares_ajustada_3a",
    ]
    base["elegible_score"] = base[principales].notna().all(axis=1)
    columnas = [
        "cod_ine",
        "anio",
        "poblacion",
        "log_cambio_poblacion_3a",
        "precio_m2",
        "log_cambio_precio_m2_3a",
        "renta_neta_media_persona",
        "renta_neta_media_hogar",
        "mediana_renta_unidad_consumo",
        "log_cambio_renta_neta_media_persona_3a",
        "log_cambio_mediana_renta_unidad_consumo_3a",
        "brecha_precio_renta_3a",
        "pct_renta_alta_200",
        "pct_renta_baja_60",
        "cambio_pct_renta_alta_200_3a",
        "cambio_pct_renta_baja_60_3a",
        "sustitucion_composicion_renta_3a",
        "indice_gini",
        "ratio_p80_p20",
        "cambio_indice_gini_3a",
        "cambio_ratio_p80_p20_3a",
        "edad_media",
        "pct_hogares_unipersonales",
        "pct_mayor_65",
        "pct_menor_18",
        "pct_poblacion_espanola",
        "tamano_medio_hogar",
        "cambio_edad_media_3a",
        "cambio_pct_hogares_unipersonales_3a",
        "cambio_pct_mayor_65_3a",
        "cambio_pct_menor_18_3a",
        "cambio_pct_poblacion_espanola_3a",
        "cambio_tamano_medio_hogar_3a",
        "transformacion_hogares_ajustada_3a",
        "saldo_total_acum_3a",
        "saldo_exterior_acum_3a",
        "saldo_interior_acum_3a",
        "salida_interior_por_1000_3a",
        "saldo_exterior_por_1000_3a",
        "ratio_asequibilidad",
        "puntuacion_asequibilidad",
        "score_presion_turistica",
        "score_presion_especulativa",
        "elegible_score",
    ]
    salida = base[columnas].sort_values(["anio", "cod_ine"]).reset_index(drop=True)
    validar(salida, principales)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT_FILE, index=False)
    return salida


def validar(df: pd.DataFrame, principales: list[str]) -> None:
    if df.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("Duplicados municipio-año")
    if (df["poblacion"] <= 0).any():
        raise ValueError("Población no positiva")
    cobertura = df[df["elegible_score"]].groupby("anio")["cod_ine"].nunique()
    utilizables = cobertura[cobertura >= int(np.ceil(306 * COBERTURA_MINIMA))]
    if utilizables.empty:
        detalle = cobertura[cobertura > 0].to_dict()
        raise ValueError(f"No existe año con cobertura mínima: {detalle}")
    if not np.isfinite(df.loc[df["elegible_score"], principales]).all().all():
        raise ValueError("Valores no finitos en variables principales")
    print(f"Cobertura elegible por año: {utilizables.to_dict()}")


def cargar(df: pd.DataFrame, db_url: str) -> None:
    engine = create_engine(db_url)
    tabla = "indicadores_gentrificacion"
    temporal = f"_{tabla}_carga"
    columnas = list(df.columns)
    actualizaciones = ", ".join(
        f"{c}=EXCLUDED.{c}" for c in columnas if c not in ("cod_ine", "anio")
    )
    with engine.begin() as conn:
        conn.exec_driver_sql(SQL_FILE.read_text())
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
    datos = construir()
    print(f"Indicadores: {len(datos):,} filas, {datos.cod_ine.nunique()}/306 municipios")
    if not args.no_db:
        cargar(datos, args.db_url)


if __name__ == "__main__":
    main()
