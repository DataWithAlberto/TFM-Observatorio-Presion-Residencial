#!/usr/bin/env python3
"""Audita las cuatro capas históricas y el corte prospectivo IPR-5 de 2023."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

UNIVERSO = 306
DEFAULT_DB_URL = (
    "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
)
MUNICIPIOS_FILE = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_DIR = Path("data/processed")
OUT_TEMPORAL = OUT_DIR / "cobertura_temporal_capas.csv"
OUT_PANEL = OUT_DIR / "cobertura_municipio_anio.csv"
OUT_VALIDACIONES = OUT_DIR / "validaciones_integracion.csv"
OUT_ESCENARIOS = OUT_DIR / "cobertura_escenarios_panel.csv"
OUT_PANEL_ESTABLE = OUT_DIR / "panel_estable_2020_2023.csv"
OUT_CORTE_IPR5 = OUT_DIR / "cobertura_corte_ipr5_2023.csv"
SQL_FILE = Path("sql/14_cobertura_integracion.sql")
ESPECULACION_INPUT_FILE = OUT_DIR / "indicadores_especulativos.csv"
RIESGO_FUTURO_FILE = OUT_DIR / "riesgo_futuro_residencial_score.csv"
RIESGO_FUTURO_IND_FILE = OUT_DIR / "indicadores_riesgo_futuro.csv"

CAPAS = {
    "asequibilidad": {
        "file": OUT_DIR / "indicadores_asequibilidad.csv",
        "periodo": "anio",
        "score": "puntuacion_asequibilidad",
        "tabla": "indicadores_asequibilidad",
    },
    "turismo": {
        "file": OUT_DIR / "presion_turistica_score.csv",
        "periodo": "fecha",
        "score": "score_presion_turistica",
        "tabla": "presion_turistica_score",
    },
    "especulacion": {
        "file": OUT_DIR / "presion_especulativa_score.csv",
        "periodo": "anio",
        "score": "score_presion_especulativa",
        "tabla": "presion_especulativa_score",
    },
    "gentrificacion": {
        "file": OUT_DIR / "riesgo_gentrificacion_score.csv",
        "periodo": "anio",
        "score": "score_riesgo_gentrificacion",
        "tabla": "riesgo_gentrificacion_score",
    },
}


def leer_universo() -> pd.DataFrame:
    import geopandas as gpd

    municipios = gpd.read_file(MUNICIPIOS_FILE, ignore_geometry=True)
    municipios["cod_ine"] = municipios["cod_ine"].astype(str).str.zfill(5)
    columnas = ["cod_ine", "nombre"]
    if "provincia" in municipios.columns:
        columnas.append("provincia")
    municipios = municipios[columnas].drop_duplicates("cod_ine")
    if len(municipios) != UNIVERSO:
        raise ValueError(
            f"El universo geográfico contiene {len(municipios)} municipios, no {UNIVERSO}"
        )
    return municipios.sort_values("cod_ine").reset_index(drop=True)


def leer_capas() -> dict[str, pd.DataFrame]:
    capas = {}
    for nombre, cfg in CAPAS.items():
        df = pd.read_csv(cfg["file"], dtype={"cod_ine": str})
        df["cod_ine"] = df["cod_ine"].str.zfill(5)
        if cfg["periodo"] == "fecha":
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df["anio"] = df["fecha"].dt.year.astype("Int64")
        else:
            df["anio"] = pd.to_numeric(
                df[cfg["periodo"]], errors="coerce"
            ).astype("Int64")
        df[cfg["score"]] = pd.to_numeric(df[cfg["score"]], errors="coerce")
        capas[nombre] = df
    return capas


def leer_elegibilidad_especulacion() -> pd.DataFrame:
    """Lee inputs elegibles aunque el score nacional no se haya publicado."""
    df = pd.read_csv(ESPECULACION_INPUT_FILE, dtype={"cod_ine": str})
    df["cod_ine"] = df["cod_ine"].str.zfill(5)
    df["anio"] = pd.to_numeric(df["anio"], errors="coerce").astype("Int64")
    if df["elegible_score_principal"].dtype != bool:
        df["elegible_score_principal"] = (
            df["elegible_score_principal"].astype(str).str.lower().eq("true")
        )
    return df


def leer_riesgo_futuro() -> tuple[pd.DataFrame, pd.DataFrame]:
    score = pd.read_csv(RIESGO_FUTURO_FILE, dtype={"cod_ine": str})
    score["cod_ine"] = score["cod_ine"].str.zfill(5)
    score["anio_base"] = pd.to_numeric(
        score["anio_base"], errors="coerce"
    ).astype("Int64")
    score["score_riesgo_futuro"] = pd.to_numeric(
        score["score_riesgo_futuro"], errors="coerce"
    )
    if score["elegible_score"].dtype != bool:
        score["elegible_score"] = (
            score["elegible_score"].astype(str).str.lower().eq("true")
        )
    score["version_metodologia"] = score["version_metodologia"].astype(str)
    indicadores = pd.read_csv(RIESGO_FUTURO_IND_FILE, dtype={"cod_ine": str})
    indicadores["cod_ine"] = indicadores["cod_ine"].str.zfill(5)
    return score, indicadores


def construir_corte_ipr5_2023(
    municipios: pd.DataFrame,
    capas: dict[str, pd.DataFrame],
    riesgo: pd.DataFrame,
) -> pd.DataFrame:
    base = municipios[["cod_ine", "nombre"]].copy()
    cortes = {
        "asequibilidad": capas["asequibilidad"][
            capas["asequibilidad"]["anio"].eq(2023)
        ],
        "turismo": capas["turismo"][
            pd.to_datetime(capas["turismo"]["fecha"]).eq(pd.Timestamp("2023-08-01"))
        ],
        "especulacion": capas["especulacion"][
            capas["especulacion"]["anio"].eq(2023)
        ],
        "gentrificacion": capas["gentrificacion"][
            capas["gentrificacion"]["anio"].eq(2023)
        ],
    }
    for capa, df in cortes.items():
        score = CAPAS[capa]["score"]
        parte = df[["cod_ine", score]].rename(
            columns={score: f"score_{capa}"}
        )
        base = base.merge(parte, on="cod_ine", how="left", validate="one_to_one")
        base[f"{capa}_disponible"] = base[f"score_{capa}"].notna() & base[
            f"score_{capa}"
        ].between(0, 100)

    riesgo_cols = [
        "cod_ine",
        "anio_base",
        "horizonte_climatico",
        "escenario_climatico",
        "tipo_valor_climatico",
        "score_riesgo_futuro",
        "elegible_score",
        "version_metodologia",
    ]
    base = base.merge(
        riesgo[riesgo_cols].rename(
            columns={
                "elegible_score": "riesgo_futuro_elegible_origen",
                "version_metodologia": "version_riesgo_futuro",
            }
        ),
        on="cod_ine",
        how="left",
        validate="one_to_one",
    )
    base["riesgo_futuro_disponible"] = (
        base["riesgo_futuro_elegible_origen"].fillna(False)
        & base["score_riesgo_futuro"].notna()
        & base["score_riesgo_futuro"].between(0, 100)
    )
    actuales = [f"{c}_disponible" for c in CAPAS]
    todas = actuales + ["riesgo_futuro_disponible"]
    base["capas_actuales_disponibles"] = base[actuales].sum(axis=1).astype(int)
    base["capas_ipr5_disponibles"] = base[todas].sum(axis=1).astype(int)
    base["elegible_ipr4_observado"] = base["capas_actuales_disponibles"].eq(4)
    base["elegible_ipr5_prospectivo"] = base["capas_ipr5_disponibles"].eq(5)
    base["motivo_no_elegible_ipr5"] = np.where(
        base["elegible_ipr5_prospectivo"],
        "",
        "sin_score_riesgo_futuro",
    )
    base["anio_corte"] = 2023
    base["fecha_turismo"] = pd.Timestamp("2023-08-01")
    base["tipo_producto"] = "corte_ipr5_prospectivo"
    return base.sort_values("cod_ine").reset_index(drop=True)


def validar_corte_ipr5(
    municipios: pd.DataFrame,
    riesgo: pd.DataFrame,
    indicadores_riesgo: pd.DataFrame,
    corte: pd.DataFrame,
) -> pd.DataFrame:
    pruebas = []

    def registrar(prueba: str, ok: bool, detalle: str) -> None:
        pruebas.append(
            {"prueba": prueba, "estado": "OK" if ok else "ERROR", "detalle": detalle}
        )

    score_valido = riesgo["score_riesgo_futuro"].notna() & riesgo[
        "score_riesgo_futuro"
    ].between(0, 100)
    registrar(
        "riesgo_futuro_306_claves",
        len(riesgo) == UNIVERSO
        and riesgo["cod_ine"].nunique() == UNIVERSO
        and not riesgo["cod_ine"].duplicated().any(),
        f"{len(riesgo)} filas; {riesgo['cod_ine'].nunique()} códigos",
    )
    registrar(
        "riesgo_futuro_elegibilidad_coherente",
        riesgo["elegible_score"].equals(score_valido),
        f"{int(riesgo['elegible_score'].sum())} elegibles",
    )
    registrar(
        "riesgo_futuro_version_corregida",
        riesgo["version_metodologia"].astype(str).eq("2.0").all(),
        ",".join(sorted(riesgo["version_metodologia"].astype(str).unique())),
    )
    registrar(
        "riesgo_futuro_metadatos",
        riesgo["anio_base"].eq(2023).all()
        and riesgo["horizonte_climatico"].eq("2041-2060").all()
        and riesgo["escenario_climatico"].eq("SSP2-4.5").all()
        and riesgo["tipo_valor_climatico"].eq("ANOMALY").all(),
        "base=2023; horizonte=2041-2060; escenario=SSP2-4.5; valor=ANOMALY",
    )
    faltantes = sorted(set(municipios["cod_ine"]) - set(riesgo.loc[score_valido, "cod_ine"]))
    registrar(
        "riesgo_futuro_faltantes_documentados",
        faltantes == ["11012", "11031", "48044"],
        ",".join(faltantes) or "ninguno",
    )
    fines = [c for c in indicadores_riesgo if c.startswith("fin_")]
    sin_fuga = all(
        pd.to_numeric(indicadores_riesgo[c], errors="coerce")
        .dropna()
        .le(2023)
        .all()
        for c in fines
    )
    registrar(
        "riesgo_futuro_sin_fuga_temporal",
        sin_fuga,
        "todos los fin_* <= 2023",
    )
    registrar(
        "riesgo_futuro_turismo_agosto_2020_2023",
        indicadores_riesgo["n_anios_turismo"].eq(4).all()
        and indicadores_riesgo["inicio_turismo"].eq(2020).all()
        and indicadores_riesgo["fin_turismo"].eq(2023).all(),
        "306 municipios con cuatro snapshots",
    )
    registrar(
        "riesgo_futuro_especulacion_no_forzada",
        indicadores_riesgo["tendencia_especulacion"].isna().all()
        and riesgo["percentil_tendencia_especulacion"].isna().all(),
        "tendencia y percentil completamente nulos",
    )
    registrar(
        "corte_ipr4_306",
        int(corte["elegible_ipr4_observado"].sum()) == UNIVERSO,
        f"{int(corte['elegible_ipr4_observado'].sum())}/306",
    )
    registrar(
        "corte_ipr5_303",
        int(corte["elegible_ipr5_prospectivo"].sum()) == 303,
        f"{int(corte['elegible_ipr5_prospectivo'].sum())}/306",
    )
    registrar(
        "corte_tres_municipios_cuatro_capas",
        int(corte["capas_ipr5_disponibles"].eq(4).sum()) == 3,
        str(int(corte["capas_ipr5_disponibles"].eq(4).sum())),
    )
    return pd.DataFrame(pruebas)


def construir_cobertura_temporal(
    capas: dict[str, pd.DataFrame], anios: list[int]
) -> pd.DataFrame:
    filas = []
    for capa, df in capas.items():
        score = CAPAS[capa]["score"]
        for anio in anios:
            periodo = df[df["anio"].eq(anio)]
            validos = periodo[periodo[score].notna() & periodo[score].between(0, 100)]
            # Los CSV de score solo contienen observaciones que superaron la
            # elegibilidad propia de cada capa. No se reconstruye ni imputa.
            elegibles = validos
            filas.append(
                {
                    "capa": capa,
                    "anio": anio,
                    "filas_fuente": len(periodo),
                    "municipios_con_fila": periodo["cod_ine"].nunique(),
                    "pct_municipios_con_fila": round(
                        100 * periodo["cod_ine"].nunique() / UNIVERSO, 6
                    ),
                    "municipios_valor_valido": validos["cod_ine"].nunique(),
                    "pct_municipios_valor_valido": round(
                        100 * validos["cod_ine"].nunique() / UNIVERSO, 6
                    ),
                    "municipios_elegibles_score": elegibles["cod_ine"].nunique(),
                    "pct_municipios_elegibles_score": round(
                        100 * elegibles["cod_ine"].nunique() / UNIVERSO, 6
                    ),
                    "observaciones_temporales": (
                        periodo["fecha"].nunique() if capa == "turismo" else int(bool(len(periodo)))
                    ),
                    "cobertura_completa_306": elegibles["cod_ine"].nunique() == UNIVERSO,
                }
            )
    return pd.DataFrame(filas).sort_values(["anio", "capa"]).reset_index(drop=True)


def construir_panel(
    municipios: pd.DataFrame, capas: dict[str, pd.DataFrame], anios: list[int]
) -> pd.DataFrame:
    base = municipios.assign(_k=1).merge(
        pd.DataFrame({"anio": anios, "_k": 1}), on="_k"
    ).drop(columns="_k")
    for capa, df in capas.items():
        score = CAPAS[capa]["score"]
        validos = df[df[score].notna() & df[score].between(0, 100)]
        anual = (
            validos.groupby(["cod_ine", "anio"], as_index=False)
            .agg(
                **{
                    f"{capa}_disponible": (score, "size"),
                    f"{capa}_observaciones": (score, "size"),
                }
            )
        )
        anual[f"{capa}_disponible"] = True
        base = base.merge(anual, on=["cod_ine", "anio"], how="left")
        base[f"{capa}_disponible"] = base[f"{capa}_disponible"].fillna(False)
        base[f"{capa}_observaciones"] = (
            base[f"{capa}_observaciones"].fillna(0).astype(int)
        )
    banderas = [f"{capa}_disponible" for capa in CAPAS]
    base["capas_disponibles"] = base[banderas].sum(axis=1).astype(int)
    base["elegible_indice_completo"] = base["capas_disponibles"].eq(len(CAPAS))
    base["estado_integracion"] = "sin_cobertura"
    base.loc[base["capas_disponibles"].between(1, 3), "estado_integracion"] = (
        "historico_parcial_observado"
    )
    base.loc[base["elegible_indice_completo"], "estado_integracion"] = (
        "observado_completo"
    )
    return base.sort_values(["anio", "cod_ine"]).reset_index(drop=True)


def construir_escenarios_panel(
    municipios: pd.DataFrame,
    capas: dict[str, pd.DataFrame],
    especulacion_input: pd.DataFrame,
    anios: list[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Distingue score publicado de un panel parcial que exigiría recalcular."""
    conjuntos: dict[str, dict[int, set[str]]] = {}
    for capa, df in capas.items():
        score = CAPAS[capa]["score"]
        validos = df[df[score].notna() & df[score].between(0, 100)]
        conjuntos[capa] = {
            anio: set(validos.loc[validos["anio"].eq(anio), "cod_ine"])
            for anio in anios
        }
    espec_elegible = especulacion_input[
        especulacion_input["elegible_score_principal"]
    ]
    conjuntos_espec_input = {
        anio: set(espec_elegible.loc[espec_elegible["anio"].eq(anio), "cod_ine"])
        for anio in anios
    }

    filas = []
    intersecciones_recalculables: dict[int, set[str]] = {}
    for anio in anios:
        publicado = set.intersection(
            *(conjuntos[capa][anio] for capa in CAPAS)
        )
        recalculable = (
            conjuntos["asequibilidad"][anio]
            & conjuntos["turismo"][anio]
            & conjuntos_espec_input[anio]
            & conjuntos["gentrificacion"][anio]
        )
        tres_capas = (
            conjuntos["asequibilidad"][anio]
            & conjuntos_espec_input[anio]
            & conjuntos["gentrificacion"][anio]
        )
        intersecciones_recalculables[anio] = recalculable
        for escenario, codigos, nota in [
            (
                "cuatro_capas_score_publicado",
                publicado,
                "Intersección de los cuatro CSV de score existentes",
            ),
            (
                "cuatro_capas_input_elegible",
                recalculable,
                "Requiere recalcular todos los percentiles sobre un universo fijo",
            ),
            (
                "tres_capas_sin_turismo",
                tres_capas,
                "Diagnóstico histórico; no es el índice completo",
            ),
        ]:
            filas.append(
                {
                    "escenario": escenario,
                    "anio": anio,
                    "municipios": len(codigos),
                    "pct_universo_306": round(100 * len(codigos) / UNIVERSO, 6),
                    "nota": nota,
                }
            )

    periodo_panel = list(range(2020, 2024))
    panel_estable = set.intersection(
        *(intersecciones_recalculables[anio] for anio in periodo_panel)
    )
    estable = municipios[municipios["cod_ine"].isin(panel_estable)].copy()
    estable["desde"] = min(periodo_panel)
    estable["hasta"] = max(periodo_panel)
    estable["requiere_recalculo_scores"] = True
    estable = estable.sort_values("cod_ine").reset_index(drop=True)
    return pd.DataFrame(filas), estable


def validar(
    municipios: pd.DataFrame,
    capas: dict[str, pd.DataFrame],
    especulacion_input: pd.DataFrame,
    temporal: pd.DataFrame,
    panel: pd.DataFrame,
    escenarios: pd.DataFrame,
    panel_estable: pd.DataFrame,
) -> pd.DataFrame:
    pruebas = []

    def registrar(prueba: str, ok: bool, detalle: str) -> None:
        pruebas.append(
            {"prueba": prueba, "estado": "OK" if ok else "ERROR", "detalle": detalle}
        )

    registrar("universo_306", len(municipios) == UNIVERSO, f"{len(municipios)} municipios")
    universo = set(municipios["cod_ine"])
    for capa, df in capas.items():
        cfg = CAPAS[capa]
        clave = ["cod_ine", cfg["periodo"]]
        duplicados = int(df.duplicated(clave).sum())
        desconocidos = sorted(set(df["cod_ine"]) - universo)
        nulos_periodo = int(df["anio"].isna().sum())
        score_valido = df[cfg["score"]].notna()
        fuera_rango = int(
            (score_valido & ~df[cfg["score"]].between(0, 100)).sum()
        )
        nulos_score = int((~score_valido).sum())
        registrar(f"{capa}_duplicados_clave", duplicados == 0, str(duplicados))
        registrar(
            f"{capa}_municipios_fuera_universo",
            not desconocidos,
            ",".join(desconocidos) if desconocidos else "0",
        )
        registrar(f"{capa}_periodos_nulos", nulos_periodo == 0, str(nulos_periodo))
        registrar(f"{capa}_scores_fuera_rango", fuera_rango == 0, str(fuera_rango))
        registrar(
            f"{capa}_scores_sin_nulos",
            nulos_score == 0,
            f"{nulos_score} nulos (las 4 capas observadas cubren los 306 municipios)",
        )
        anios_por_municipio = (
            df[df[cfg["score"]].notna()]
            .groupby("cod_ine")["anio"]
            .apply(lambda s: sorted(set(int(x) for x in s.dropna())))
        )
        huecos = sum(
            len(a) > 1 and a != list(range(min(a), max(a) + 1))
            for a in anios_por_municipio
        )
        registrar(f"{capa}_continuidad_anual", huecos == 0, f"{huecos} municipios con huecos")

    completos = (
        temporal[temporal["cobertura_completa_306"]]
        .groupby("anio")["capa"]
        .nunique()
    )
    anios_comunes_cuatro = sorted(
        completos[completos.eq(len(CAPAS))].index.tolist()
    )
    registrar(
        "anio_comun_306_cuatro_capas",
        anios_comunes_cuatro == [2023],
        ",".join(map(str, anios_comunes_cuatro)) or "ninguno",
    )
    elegibles_2023 = int(
        panel.loc[panel["anio"].eq(2023), "elegible_indice_completo"].sum()
    )
    registrar(
        "cobertura_2023_306",
        elegibles_2023 == UNIVERSO,
        str(elegibles_2023),
    )
    turismo = capas["turismo"]
    snapshots_incompletos = int(
        (~turismo.groupby("fecha")["cod_ine"].nunique().eq(UNIVERSO)).sum()
    )
    registrar(
        "turismo_snapshots_306",
        snapshots_incompletos == 0,
        f"{snapshots_incompletos} snapshots incompletos",
    )
    gentrificacion = capas["gentrificacion"]
    cobertura_g = gentrificacion.groupby("anio")["cod_ine"].nunique()
    metadatos_g = gentrificacion.groupby("anio")["municipios_cobertura_anio"].first()
    coherencia_g = cobertura_g.equals(metadatos_g.astype(int))
    registrar(
        "gentrificacion_metadatos_cobertura",
        coherencia_g,
        "recuento observado coincide con municipios_cobertura_anio",
    )
    orden_cobertura = (
        temporal["municipios_elegibles_score"]
        .le(temporal["municipios_valor_valido"])
        & temporal["municipios_valor_valido"].le(temporal["municipios_con_fila"])
    ).all()
    registrar(
        "coherencia_fila_valido_elegible",
        bool(orden_cobertura),
        "elegible <= válido <= fila",
    )
    espec_elegible = especulacion_input[
        especulacion_input["elegible_score_principal"]
    ]
    cobertura_espec_input = espec_elegible.groupby("anio")["cod_ine"].nunique()
    esperado_espec = {
        2016: 280,
        2017: 284,
        2018: 284,
        2019: 284,
        2020: 284,
        2021: 284,
        2022: 306,
        2023: 306,
    }
    observado_espec = {
        int(anio): int(cobertura_espec_input.get(anio, 0))
        for anio in esperado_espec
    }
    registrar(
        "especulacion_input_elegible_por_anio",
        observado_espec == esperado_espec,
        str(observado_espec),
    )
    recalculable = escenarios[
        escenarios["escenario"].eq("cuatro_capas_input_elegible")
    ].set_index("anio")["municipios"]
    esperado_recalculable = {2020: 284, 2021: 284, 2022: 284, 2023: 306}
    observado_recalculable = {
        anio: int(recalculable.get(anio, 0)) for anio in esperado_recalculable
    }
    registrar(
        "interseccion_recalculable_2020_2023",
        observado_recalculable == esperado_recalculable,
        str(observado_recalculable),
    )
    registrar(
        "panel_estable_recalculable_2020_2023",
        len(panel_estable) == 284,
        f"{len(panel_estable)} municipios",
    )
    anteriores_2020 = recalculable[recalculable.index < 2020]
    registrar(
        "sin_indice_completo_antes_2020",
        anteriores_2020.eq(0).all(),
        "0 municipios por ausencia de turismo",
    )
    turismo_fechas = set(
        pd.to_datetime(capas["turismo"]["fecha"]).dt.strftime("%Y-%m-%d")
    )
    agostos = {f"{anio}-08-01" for anio in range(2020, 2024)}
    registrar(
        "turismo_agosto_comparable_2020_2023",
        agostos.issubset(turismo_fechas),
        ",".join(sorted(agostos & turismo_fechas)),
    )
    return pd.DataFrame(pruebas)


def comparar_postgis(
    capas: dict[str, pd.DataFrame],
    especulacion_input: pd.DataFrame,
    riesgo_futuro: pd.DataFrame,
    db_url: str,
) -> pd.DataFrame:
    resultados = []
    engine = create_engine(db_url, connect_args={"connect_timeout": 5})
    with engine.connect() as conn:
        for capa, cfg in CAPAS.items():
            periodo_sql = (
                "EXTRACT(YEAR FROM fecha)::int"
                if cfg["periodo"] == "fecha"
                else cfg["periodo"]
            )
            consulta = text(
                f"SELECT {periodo_sql} AS anio, COUNT(*) AS filas, "
                f"COUNT(DISTINCT cod_ine) AS municipios FROM {cfg['tabla']} "
                f"GROUP BY 1 ORDER BY 1"
            )
            db = pd.read_sql(consulta, conn)
            csv = (
                capas[capa].groupby("anio")["cod_ine"]
                .agg(filas="size", municipios="nunique")
                .reset_index()
            )
            igual = db.astype({"anio": int}).equals(csv.astype({"anio": int}))
            resultados.append(
                {
                    "prueba": f"{capa}_csv_vs_postgis",
                    "estado": "OK" if igual else "ERROR",
                    "detalle": "recuentos idénticos" if igual else "recuentos distintos",
                }
            )
            clave_periodo = cfg["periodo"]
            db_detalle = pd.read_sql(
                text(
                    f"SELECT TRIM(cod_ine) AS cod_ine, {clave_periodo}, "
                    f"{cfg['score']}::double precision AS score "
                    f"FROM {cfg['tabla']}"
                ),
                conn,
            )
            csv_detalle = capas[capa][
                ["cod_ine", clave_periodo, cfg["score"]]
            ].rename(columns={cfg["score"]: "score"})
            if clave_periodo == "fecha":
                db_detalle[clave_periodo] = pd.to_datetime(
                    db_detalle[clave_periodo]
                )
                csv_detalle[clave_periodo] = pd.to_datetime(
                    csv_detalle[clave_periodo]
                )
            claves = ["cod_ine", clave_periodo]
            combinado = csv_detalle.merge(
                db_detalle,
                on=claves,
                how="outer",
                suffixes=("_csv", "_db"),
                indicator=True,
            )
            claves_iguales = combinado["_merge"].eq("both").all()
            resultados.append(
                {
                    "prueba": f"{capa}_claves_csv_vs_postgis",
                    "estado": "OK" if claves_iguales else "ERROR",
                    "detalle": (
                        "claves idénticas"
                        if claves_iguales
                        else combinado["_merge"].value_counts().to_dict()
                    ),
                }
            )
            ambos = combinado[combinado["_merge"].eq("both")]
            diferencias = (
                ambos["score_csv"].astype(float) - ambos["score_db"].astype(float)
            ).abs()
            valores_iguales = bool(
                np.isclose(
                    ambos["score_csv"].astype(float),
                    ambos["score_db"].astype(float),
                    rtol=0,
                    atol=5.1e-5,
                    equal_nan=True,
                ).all()
            )
            resultados.append(
                {
                    "prueba": f"{capa}_scores_csv_vs_postgis",
                    "estado": "OK" if valores_iguales else "ERROR",
                    "detalle": f"diferencia máxima {diferencias.max():.10f}",
                }
            )

        db_riesgo = pd.read_sql(
            text(
                "SELECT TRIM(cod_ine) AS cod_ine, anio_base, "
                "horizonte_climatico, escenario_climatico, elegible_score, "
                "tipo_valor_climatico, "
                "score_riesgo_futuro::double precision AS score_riesgo_futuro, "
                "version_metodologia FROM riesgo_futuro_residencial_score"
            ),
            conn,
        )
        columnas_riesgo = [
            "cod_ine",
            "anio_base",
            "horizonte_climatico",
            "escenario_climatico",
            "tipo_valor_climatico",
            "elegible_score",
            "score_riesgo_futuro",
            "version_metodologia",
        ]
        csv_riesgo = riesgo_futuro[columnas_riesgo].copy()
        combinado_riesgo = csv_riesgo.merge(
            db_riesgo,
            on=[
                "cod_ine",
                "anio_base",
                "horizonte_climatico",
                "escenario_climatico",
                "tipo_valor_climatico",
                "version_metodologia",
            ],
            how="outer",
            suffixes=("_csv", "_db"),
            indicator=True,
        )
        claves_riesgo = combinado_riesgo["_merge"].eq("both").all()
        elegibilidad_riesgo = (
            combinado_riesgo.loc[
                combinado_riesgo["_merge"].eq("both"), "elegible_score_csv"
            ].reset_index(drop=True)
            .equals(
                combinado_riesgo.loc[
                    combinado_riesgo["_merge"].eq("both"), "elegible_score_db"
                ].reset_index(drop=True)
            )
        )
        scores_riesgo = np.isclose(
            combinado_riesgo.loc[
                combinado_riesgo["_merge"].eq("both"), "score_riesgo_futuro_csv"
            ],
            combinado_riesgo.loc[
                combinado_riesgo["_merge"].eq("both"), "score_riesgo_futuro_db"
            ],
            rtol=0,
            atol=5.1e-5,
            equal_nan=True,
        ).all()
        resultados.append(
            {
                "prueba": "riesgo_futuro_csv_vs_postgis",
                "estado": (
                    "OK"
                    if claves_riesgo and elegibilidad_riesgo and scores_riesgo
                    else "ERROR"
                ),
                "detalle": "claves, metadatos, elegibilidad y scores idénticos",
            }
        )

        db_espec = pd.read_sql(
            text(
                "SELECT TRIM(cod_ine) AS cod_ine, anio, "
                "elegible_score_principal FROM indicadores_especulativos"
            ),
            conn,
        ).sort_values(["anio", "cod_ine"]).reset_index(drop=True)
        csv_espec = especulacion_input[
            ["cod_ine", "anio", "elegible_score_principal"]
        ].copy()
        csv_espec["anio"] = csv_espec["anio"].astype(int)
        csv_espec = csv_espec.sort_values(["anio", "cod_ine"]).reset_index(drop=True)
        espec_igual = db_espec.equals(csv_espec)
        resultados.append(
            {
                "prueba": "especulacion_input_elegibilidad_csv_vs_postgis",
                "estado": "OK" if espec_igual else "ERROR",
                "detalle": (
                    "claves y elegibilidad idénticas"
                    if espec_igual
                    else "diferencias en claves o elegibilidad"
                ),
            }
        )
        columnas_legacy = [
            "salida_interior_por_1000_3a",
            "winsor_salida_interior_por_1000_3a",
            "percentil_salida_interior_por_1000_3a",
        ]
        columnas_db = {
            fila[0]
            for fila in conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' "
                    "AND table_name='riesgo_gentrificacion_score'"
                )
            )
        }
        presentes = [c for c in columnas_legacy if c in columnas_db]
        if presentes:
            no_nulos = conn.execute(
                text(
                    "SELECT "
                    + " + ".join(f"COUNT({c})" for c in presentes)
                    + " FROM riesgo_gentrificacion_score"
                )
            ).scalar_one()
            resultados.append(
                {
                    "prueba": "gentrificacion_columnas_legacy_postgis",
                    "estado": "AVISO" if no_nulos == 0 else "ERROR",
                    "detalle": (
                        f"{len(presentes)} columnas v1 presentes; "
                        f"{no_nulos} valores no nulos"
                    ),
                }
            )
    return pd.DataFrame(resultados)


def cargar_postgis(
    temporal: pd.DataFrame,
    panel: pd.DataFrame,
    corte_ipr5: pd.DataFrame,
    db_url: str,
) -> None:
    engine = create_engine(db_url, connect_args={"connect_timeout": 5})
    ddl = SQL_FILE.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text(ddl))
        temporal.to_sql(
            "_cobertura_temporal_integracion_carga",
            conn,
            if_exists="replace",
            index=False,
            method="multi",
        )
        panel.to_sql(
            "_cobertura_municipio_anio_carga",
            conn,
            if_exists="replace",
            index=False,
            method="multi",
        )
        corte_ipr5.to_sql(
            "_cobertura_corte_ipr5_carga",
            conn,
            if_exists="replace",
            index=False,
            method="multi",
        )
        conn.execute(text("TRUNCATE cobertura_temporal_integracion"))
        conn.execute(text("TRUNCATE cobertura_municipio_anio_integracion"))
        conn.execute(text("TRUNCATE cobertura_corte_ipr5_integracion"))
        conn.execute(text(
            "INSERT INTO cobertura_temporal_integracion ("
            + ",".join(temporal.columns)
            + ") SELECT "
            + ",".join(temporal.columns)
            + " FROM _cobertura_temporal_integracion_carga"
        ))
        conn.execute(text(
            "INSERT INTO cobertura_municipio_anio_integracion ("
            + ",".join(panel.columns)
            + ") SELECT "
            + ",".join(panel.columns)
            + " FROM _cobertura_municipio_anio_carga"
        ))
        conn.execute(text(
            "INSERT INTO cobertura_corte_ipr5_integracion ("
            + ",".join(corte_ipr5.columns)
            + ") SELECT "
            + ",".join(corte_ipr5.columns)
            + " FROM _cobertura_corte_ipr5_carga"
        ))
        conn.execute(text("DROP TABLE _cobertura_temporal_integracion_carga"))
        conn.execute(text("DROP TABLE _cobertura_municipio_anio_carga"))
        conn.execute(text("DROP TABLE _cobertura_corte_ipr5_carga"))


def validar_carga_postgis(
    temporal: pd.DataFrame,
    panel: pd.DataFrame,
    corte_ipr5: pd.DataFrame,
    db_url: str,
) -> pd.DataFrame:
    engine = create_engine(db_url, connect_args={"connect_timeout": 5})
    pruebas = []
    with engine.connect() as conn:
        db_temporal = pd.read_sql(
            text(
                "SELECT capa, anio FROM cobertura_temporal_integracion "
                "ORDER BY capa, anio"
            ),
            conn,
        )
        csv_temporal = (
            temporal[["capa", "anio"]]
            .sort_values(["capa", "anio"])
            .reset_index(drop=True)
        )
        pruebas.append(
            {
                "prueba": "carga_cobertura_temporal_postgis",
                "estado": "OK" if db_temporal.equals(csv_temporal) else "ERROR",
                "detalle": f"{len(db_temporal)} claves",
            }
        )
        db_corte = pd.read_sql(
            text(
                "SELECT TRIM(cod_ine) AS cod_ine, anio_corte "
                "FROM cobertura_corte_ipr5_integracion "
                "ORDER BY cod_ine"
            ),
            conn,
        )
        csv_corte = (
            corte_ipr5[["cod_ine", "anio_corte"]]
            .sort_values("cod_ine")
            .reset_index(drop=True)
        )
        pruebas.append(
            {
                "prueba": "carga_corte_ipr5_postgis",
                "estado": "OK" if db_corte.equals(csv_corte) else "ERROR",
                "detalle": f"{len(db_corte)} claves",
            }
        )
        db_panel = pd.read_sql(
            text(
                "SELECT TRIM(cod_ine) AS cod_ine, anio "
                "FROM cobertura_municipio_anio_integracion "
                "ORDER BY anio, cod_ine"
            ),
            conn,
        )
        csv_panel = (
            panel[["cod_ine", "anio"]]
            .sort_values(["anio", "cod_ine"])
            .reset_index(drop=True)
        )
        pruebas.append(
            {
                "prueba": "carga_cobertura_municipio_anio_postgis",
                "estado": "OK" if db_panel.equals(csv_panel) else "ERROR",
                "detalle": f"{len(db_panel)} claves",
            }
        )
    return pd.DataFrame(pruebas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    parser.add_argument(
        "--check-db", action="store_true", help="Comparar recuentos con PostGIS"
    )
    parser.add_argument(
        "--load-db", action="store_true", help="Crear y cargar tablas de cobertura"
    )
    args = parser.parse_args()
    if args.load_db and not args.check_db:
        parser.error("--load-db exige --check-db")

    municipios = leer_universo()
    capas = leer_capas()
    especulacion_input = leer_elegibilidad_especulacion()
    riesgo_futuro, indicadores_riesgo = leer_riesgo_futuro()
    anios = list(
        range(
            min(int(df["anio"].min()) for df in capas.values()),
            max(int(df["anio"].max()) for df in capas.values()) + 1,
        )
    )
    temporal = construir_cobertura_temporal(capas, anios)
    panel = construir_panel(municipios, capas, anios)
    escenarios, panel_estable = construir_escenarios_panel(
        municipios, capas, especulacion_input, anios
    )
    corte_ipr5 = construir_corte_ipr5_2023(
        municipios, capas, riesgo_futuro
    )
    validaciones = validar(
        municipios,
        capas,
        especulacion_input,
        temporal,
        panel,
        escenarios,
        panel_estable,
    )
    validaciones = pd.concat(
        [
            validaciones,
            validar_corte_ipr5(
                municipios,
                riesgo_futuro,
                indicadores_riesgo,
                corte_ipr5,
            ),
        ],
        ignore_index=True,
    )
    if args.check_db:
        validaciones = pd.concat(
            [
                validaciones,
                comparar_postgis(
                    capas, especulacion_input, riesgo_futuro, args.db_url
                ),
            ],
            ignore_index=True,
        )
    else:
        validaciones = pd.concat(
            [
                validaciones,
                pd.DataFrame(
                    [
                        {
                            "prueba": "comparacion_csv_postgis",
                            "estado": "NO_EJECUTADA",
                            "detalle": "Ejecutar con --check-db y PostGIS activo",
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    temporal.to_csv(OUT_TEMPORAL, index=False)
    panel.to_csv(OUT_PANEL, index=False)
    escenarios.to_csv(OUT_ESCENARIOS, index=False)
    panel_estable.to_csv(OUT_PANEL_ESTABLE, index=False)
    corte_ipr5.to_csv(OUT_CORTE_IPR5, index=False)
    if args.load_db:
        cargar_postgis(temporal, panel, corte_ipr5, args.db_url)
        validaciones = pd.concat(
            [
                validaciones,
                validar_carga_postgis(
                    temporal, panel, corte_ipr5, args.db_url
                ),
            ],
            ignore_index=True,
        )
    validaciones.to_csv(OUT_VALIDACIONES, index=False)

    comunes = panel.groupby("anio")["elegible_indice_completo"].sum()
    print(f"Años completos 306/306: {comunes[comunes.eq(UNIVERSO)].index.tolist()}")
    print(
        "Corte IPR-5 prospectivo 2023: "
        f"{int(corte_ipr5['elegible_ipr5_prospectivo'].sum())}/306"
    )
    print(f"Validaciones: {validaciones['estado'].value_counts().to_dict()}")
    if validaciones["estado"].eq("ERROR").any():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
