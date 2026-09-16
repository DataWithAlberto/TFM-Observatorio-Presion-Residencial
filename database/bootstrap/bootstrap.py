#!/usr/bin/env python3
"""Inicializa la base de la aplicación con los resultados procesados validados."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError

from data_quality import EVIDENCE_FILES, calculate, persist
from spatial import load_spatial

ROOT = Path("/workspace")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:tfm_pass@db:5432/tfm_presion_residencial",
)
FORCE = os.getenv("FORCE_BOOTSTRAP", "0").lower() in {"1", "true", "yes", "si"}

MUNICIPIOS_FILE = ROOT / "data/raw/municipios_306_con_geometria.gpkg"
PROCESSED = ROOT / "data/processed"
SCHEMA_FILES = [
    ROOT / "sql/00_base.sql",
    ROOT / "database/bootstrap/01_serving_tables.sql",
    ROOT / "sql/08_especulacion.sql",
    ROOT / "sql/11_gentrificacion.sql",
    ROOT / "sql/15_riesgo_futuro.sql",
    ROOT / "sql/18_indice_presion_residencial.sql",
    ROOT / "sql/14_cobertura_integracion.sql",
    ROOT / "sql/20_analisis_espacial.sql",
]
VIEW_FILE = ROOT / "database/serving/20_api_views.sql"

SEEDS = {
    "indicadores_asequibilidad": "indicadores_asequibilidad.csv",
    "presion_turistica_score": "presion_turistica_score.csv",
    "indicadores_especulativos": "indicadores_especulativos.csv",
    "presion_especulativa_score": "presion_especulativa_score.csv",
    "riesgo_gentrificacion_score": "riesgo_gentrificacion_score.csv",
    "riesgo_futuro_residencial_score": "riesgo_futuro_residencial_score.csv",
    "indice_presion_residencial": "indice_presion_residencial_2023.csv",
    "ipr_sensibilidad_pesos": "ipr_sensibilidad_pesos.csv",
    "cobertura_corte_ipr5_integracion": "cobertura_corte_ipr5_2023.csv",
}


def require_files() -> list[Path]:
    files = [MUNICIPIOS_FILE, *SCHEMA_FILES, VIEW_FILE]
    files.extend(PROCESSED / name for name in SEEDS.values())
    files.append(PROCESSED / "precios_vivienda_ministerio_final.csv")
    files.extend(PROCESSED / "ipr_historical" / name for name in (
        "manifest.json", "historical_municipality_universe.csv", "scores.csv", "components.csv"
    ))
    files.append(ROOT / "sql/20_ipr_historico.sql")
    files.extend(PROCESSED / name for name in EVIDENCE_FILES)
    files.extend([ROOT / "sql/20_data_quality.sql", Path(__file__).with_name("data_quality.py")])
    files.append(PROCESSED / "spatial/spatial_ipr.json")
    files.extend([Path(__file__), Path(__file__).with_name("spatial.py")])
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Faltan archivos para inicializar la base: " + ", ".join(missing)
        )
    return files


def fingerprint(files: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: str(item)):
        digest.update(str(path.relative_to(ROOT)).encode())
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def connect_with_retry():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    for attempt in range(1, 31):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return engine
        except OperationalError:
            if attempt == 30:
                raise
            time.sleep(1)
    return engine


def database_is_current(engine, source_fingerprint: str) -> bool:
    with engine.connect() as connection:
        metadata = connection.scalar(
            text("SELECT to_regclass('public.bootstrap_metadata')")
        )
        view = connection.scalar(text("SELECT to_regclass('public.api_ipr_municipal')"))
        if metadata is None or view is None:
            return False
        stored = connection.scalar(
            text("SELECT valor FROM bootstrap_metadata WHERE clave='dataset_sha256'")
        )
        return stored == source_fingerprint


def run_sql(connection, path: Path) -> None:
    connection.exec_driver_sql(path.read_text(encoding="utf-8"))


def prepare_municipalities() -> gpd.GeoDataFrame:
    frame = gpd.read_file(MUNICIPIOS_FILE).to_crs(4326)
    frame["cod_ine"] = frame["cod_ine"].astype(str).str.zfill(5)
    frame = frame[
        ["cod_ine", "nombre", "provincia_norm", "comunidad_autonoma", "geometry"]
    ].rename(columns={"provincia_norm": "provincia"})
    if len(frame) != 306 or frame["cod_ine"].nunique() != 306:
        raise ValueError("El universo espacial no contiene 306 municipios únicos")
    if frame.geometry.isna().any() or not frame.geometry.is_valid.all():
        raise ValueError("El universo espacial contiene geometrías nulas o inválidas")
    return frame.sort_values("cod_ine").reset_index(drop=True)


def prepare_prices() -> pd.DataFrame:
    frame = pd.read_csv(
        PROCESSED / "precios_vivienda_ministerio_final.csv",
        dtype={"id_municipio": str},
    )
    frame["cod_ine"] = frame["id_municipio"].str.zfill(5)
    dates = pd.to_datetime(frame["fecha"], errors="raise")
    frame["anio"] = dates.dt.year
    frame["trimestre"] = dates.dt.quarter
    frame = frame.rename(columns={"valor_total": "precio_m2"})
    columns = [
        "cod_ine",
        "anio",
        "trimestre",
        "precio_m2",
        "valor_5menos",
        "valor_5mas",
        "num_tasaciones",
    ]
    frame = frame[columns].sort_values(["cod_ine", "anio", "trimestre"])
    if frame.duplicated(["cod_ine", "anio", "trimestre"]).any():
        raise ValueError("Hay precios duplicados por municipio, año y trimestre")
    return frame.reset_index(drop=True)


def read_seed(filename: str) -> pd.DataFrame:
    frame = pd.read_csv(
        PROCESSED / filename,
        dtype={
            "cod_ine": str,
            "version_metodologia": str,
            "version_riesgo_futuro": str,
        },
    )
    if "cod_ine" in frame:
        frame["cod_ine"] = frame["cod_ine"].str.zfill(5)
    for date_column in ("fecha", "fecha_turismo"):
        if date_column in frame:
            frame[date_column] = pd.to_datetime(
                frame[date_column], errors="raise"
            ).dt.date
    if "motivo_no_elegible_ipr5" in frame:
        frame["motivo_no_elegible_ipr5"] = frame["motivo_no_elegible_ipr5"].fillna("")
    if filename == "ipr_sensibilidad_pesos.csv":
        frame["anio"] = 2023
    return frame


def replace_table(engine, table: str, frame: pd.DataFrame) -> None:
    staging = f"_bootstrap_{table}"
    with engine.begin() as connection:
        target_columns = {
            column["name"] for column in inspect(connection).get_columns(table)
        }
        columns = [column for column in frame.columns if column in target_columns]
        if not columns:
            raise ValueError(f"No hay columnas compatibles para {table}")
        connection.execute(text(f'DROP TABLE IF EXISTS "{staging}"'))
        frame[columns].to_sql(
            staging,
            connection,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )
        quoted = ",".join(f'"{column}"' for column in columns)
        connection.execute(text(f'DELETE FROM "{table}"'))
        connection.execute(
            text(
                f'INSERT INTO "{table}" ({quoted}) '
                f'SELECT {quoted} FROM "{staging}"'
            )
        )
        connection.execute(text(f'DROP TABLE "{staging}"'))
    print(f"  {table}: {len(frame):,} filas")


def load_municipalities(engine, frame: gpd.GeoDataFrame) -> None:
    staging = "_bootstrap_municipios"
    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {staging}"))
        frame.to_postgis(staging, connection, if_exists="replace", index=False)
        connection.execute(
            text(
                f"""
                INSERT INTO municipios
                    (cod_ine,nombre,provincia,comunidad_autonoma,geometry)
                SELECT cod_ine,nombre,provincia,comunidad_autonoma,geometry
                FROM {staging}
                ON CONFLICT (cod_ine) DO UPDATE SET
                    nombre=EXCLUDED.nombre,
                    provincia=EXCLUDED.provincia,
                    comunidad_autonoma=EXCLUDED.comunidad_autonoma,
                    geometry=EXCLUDED.geometry
                """
            )
        )
        connection.execute(text(f"DROP TABLE {staging}"))
    print(f"  municipios: {len(frame):,} filas con geometría")


def validate(engine) -> None:
    expected = {
        "municipios": 306,
        "ipr_spatial_local": 306,
        "indice_presion_residencial": 306,
        "api_ipr_municipal": 306,
        "data_quality_municipal": 306,
        "indicadores_asequibilidad": 306,
        "presion_turistica_score": 306,
        "indicadores_especulativos": 306,
        "presion_especulativa_score": 306,
        "riesgo_gentrificacion_score": 306,
        "riesgo_futuro_residencial_score": 306,
        "cobertura_corte_ipr5_integracion": 306,
    }
    with engine.connect() as connection:
        for table, distinct_municipalities in expected.items():
            count = connection.scalar(
                text(f'SELECT COUNT(DISTINCT cod_ine) FROM "{table}"')
            )
            if count != distinct_municipalities:
                raise ValueError(
                    f"Validación fallida en {table}: {count} municipios; "
                    f"se esperaban {distinct_municipalities}"
                )
        geometry_count = connection.scalar(
            text("SELECT COUNT(*) FROM municipios WHERE geometry IS NOT NULL")
        )
        prospective_count = connection.scalar(
            text(
                "SELECT COUNT(*) FROM api_ipr_municipal "
                "WHERE score_prospectivo IS NOT NULL"
            )
        )
        observed_count = connection.scalar(
            text(
                "SELECT COUNT(*) FROM api_ipr_municipal "
                "WHERE score_observado IS NOT NULL"
            )
        )
    if geometry_count != 306 or observed_count != 306 or prospective_count != 303:
        raise ValueError(
            "Validación final fallida: "
            f"geometrías={geometry_count}, observado={observed_count}, "
            f"prospectivo={prospective_count}"
        )


def main() -> None:
    files = require_files()
    source_fingerprint = fingerprint(files)
    engine = connect_with_retry()

    if not FORCE and database_is_current(engine, source_fingerprint):
        validate(engine)
        print("Base ya inicializada con la versión vigente de los datos.")
        return

    print("Inicializando la base de la aplicación...")
    municipalities = prepare_municipalities()
    prices = prepare_prices()

    with engine.begin() as connection:
        run_sql(connection, SCHEMA_FILES[0])
    load_municipalities(engine, municipalities)
    replace_table(engine, "precios_vivienda", prices)

    with engine.begin() as connection:
        for path in SCHEMA_FILES[1:]:
            run_sql(connection, path)

    for table, filename in SEEDS.items():
        replace_table(engine, table, read_seed(filename))

    sys.path.insert(0, str(ROOT))
    from analytics.historical import persist as persist_history, sha256, validate_results

    history = PROCESSED / "ipr_historical"
    metadata = json.loads((history / "manifest.json").read_text())
    for filename in ("scores.csv", "components.csv", "historical_municipality_universe.csv"):
        if metadata.get("output_sha256", {}).get(filename) != sha256(history / filename):
            raise ValueError(f"Huella del histórico incorrecta: {filename}; regenerar con 20_ipr_historico.py")
    scores = pd.read_csv(history / "scores.csv", dtype={"cod_ine": str})
    components = pd.read_csv(history / "components.csv", dtype={"cod_ine": str})
    universe = pd.read_csv(history / "historical_municipality_universe.csv", dtype={"cod_ine": str}, keep_default_na=False)
    validate_results(scores, components, metadata["years"], set(universe.loc[universe.included, "cod_ine"]))
    persist_history(scores, components, universe, metadata, DATABASE_URL)

    quality, _, _ = calculate(
        PROCESSED, read_seed(SEEDS["indice_presion_residencial"]),
        set(municipalities.cod_ine),
    )
    load_spatial(engine, ROOT)

    with engine.begin() as connection:
        persist(connection, quality, ROOT / "sql/20_data_quality.sql")
        run_sql(connection, VIEW_FILE)
        connection.execute(
            text(
                """
                INSERT INTO bootstrap_metadata (clave,valor,actualizado_en)
                VALUES ('dataset_sha256',:value,NOW())
                ON CONFLICT (clave) DO UPDATE SET
                    valor=EXCLUDED.valor,
                    actualizado_en=EXCLUDED.actualizado_en
                """
            ),
            {"value": source_fingerprint},
        )

    validate(engine)
    print("Base lista: 306 municipios observados y 303 con contraste prospectivo.")


if __name__ == "__main__":
    main()
