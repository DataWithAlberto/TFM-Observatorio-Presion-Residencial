#!/usr/bin/env python3
"""Ingesta de fuentes municipales para la capa de transformación socioeconómica."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from reproducibilidad.descargas import record_download
from sqlalchemy import create_engine, text

MIGRACION_ID = "69767"
MIGRACION_URL = f"https://www.ine.es/jaxiT3/files/t/csv_bdsc/{MIGRACION_ID}.csv"
RAW_MIGRACION = Path(f"data/raw/ine_gentrificacion/saldos_migratorios_{MIGRACION_ID}.csv")
ATLAS_IDS = {
    "renta": "30824",
    "distribucion_relativa": "30829",
    "desigualdad": "37677",
    "demografia": "30832",
}
ATLAS_FILES = {
    "renta": Path("data/raw/ine_renta/atlas_renta_30824.csv"),
    "distribucion_relativa": Path(
        "data/raw/ine_gentrificacion/distribucion_relativa_30829_selectivo.csv"
    ),
    "desigualdad": Path(
        "data/raw/ine_gentrificacion/desigualdad_37677_selectivo.csv"
    ),
    "demografia": Path(
        "data/raw/ine_gentrificacion/demografia_hogares_30832_selectivo.csv"
    ),
}
MUNICIPIOS_API_FILE = Path("data/raw/ine_gentrificacion/municipios_api_ine.csv")
API_BASE = "https://servicios.ine.es/wstempus/js/ES"
ATLAS_API_CONFIG = {
    "distribucion_relativa": {
        "tabla": "30829",
        "filtros": [(18, 451)],
        "indicadores": [
            (848, 322972, "pct_renta_baja_60"),
            (848, 366828, "pct_renta_alta_200"),
        ],
    },
    "desigualdad": {
        "tabla": "37677",
        "filtros": [],
        "indicadores": [
            (482, 382445, "indice_gini"),
            (482, 382446, "ratio_p80_p20"),
        ],
    },
    "demografia": {
        "tabla": "30832",
        "filtros": [],
        "indicadores": [
            (260, 274520, "edad_media"),
            (260, 366830, "pct_menor_18"),
            (260, 366831, "pct_mayor_65"),
            (260, 366832, "tamano_medio_hogar"),
            (260, 366833, "pct_hogares_unipersonales"),
            (260, 391401, "pct_poblacion_espanola"),
        ],
    },
}
MUNICIPIOS_GPKG = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_SOCIO = Path("data/processed/variables_socioeconomicas_municipales.csv")
OUT_MIGRACION = Path("data/processed/saldos_migratorios_municipales.csv")
DEFAULT_DB_URL = "postgresql://postgres:tfm_pass@localhost:5433/tfm_presion_residencial"
SQL_FILE = Path("sql/11_gentrificacion.sql")


def descargar(url: str, destino: Path, force: bool = False,
              recurso: str | None = None) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists() and not force:
        print(f"Se reutiliza: {destino}")
        return
    temporal = destino.with_suffix(destino.suffix + ".part")
    with requests.get(url, timeout=180, stream=True) as respuesta:
        respuesta.raise_for_status()
        with temporal.open("wb") as fichero:
            for bloque in respuesta.iter_content(1024 * 1024):
                if bloque:
                    fichero.write(bloque)
    temporal.replace(destino)
    record_download(destino, url, organism="Instituto Nacional de Estadística", resource=recurso,
                    license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125")
    print(f"Descargado: {destino}")


def _leer_ine(ruta: Path, **kwargs) -> pd.DataFrame:
    for encoding in ("utf-8-sig", "iso-8859-15"):
        try:
            return pd.read_csv(ruta, sep=";", encoding=encoding, **kwargs)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Codificación no reconocida: {ruta}")


def _encoding_ine(ruta: Path) -> str:
    for encoding in ("utf-8-sig", "iso-8859-15"):
        try:
            pd.read_csv(ruta, sep=";", encoding=encoding, dtype=str, nrows=5)
            return encoding
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Codificación no reconocida: {ruta}")


def _numero_ine(serie: pd.Series) -> pd.Series:
    limpio = (
        serie.astype("string")
        .str.strip()
        .replace({"": pd.NA, "..": pd.NA, "...": pd.NA, ":": pd.NA})
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(limpio, errors="coerce")


def _codigos_objetivo() -> set[str]:
    municipios = gpd.read_file(MUNICIPIOS_GPKG, ignore_geometry=True)
    return set(municipios["cod_ine"].astype(str).str.zfill(5))


def _obtener_mapeo_municipios(force: bool = False) -> pd.DataFrame:
    if MUNICIPIOS_API_FILE.exists() and not force:
        return pd.read_csv(MUNICIPIOS_API_FILE, dtype={"cod_ine": str})
    respuesta = requests.get(
        f"{API_BASE}/VALORES_GRUPOSTABLA/30829/90507?det=1", timeout=300
    )
    respuesta.raise_for_status()
    codigos = _codigos_objetivo()
    filas = [
        {
            "cod_ine": str(valor.get("Codigo", "")).zfill(5),
            "id_valor_ine": valor["Id"],
            "nombre_ine": valor["Nombre"],
        }
        for valor in respuesta.json()
        if valor.get("Variable", {}).get("Codigo") == "MUN"
        and str(valor.get("Codigo", "")).zfill(5) in codigos
    ]
    salida = pd.DataFrame(filas).sort_values("cod_ine")
    if len(salida) != 306 or salida["cod_ine"].duplicated().any():
        raise ValueError("El catálogo API no resolvió exactamente los 306 municipios")
    MUNICIPIOS_API_FILE.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(MUNICIPIOS_API_FILE, index=False)
    record_download(
        MUNICIPIOS_API_FILE,
        f"{API_BASE}/VALORES_GRUPOSTABLA/30829/90507?det=1",
        organism="Instituto Nacional de Estadística",
        resource="Catálogo de municipios del Atlas de renta, API Tempus",
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
    )
    return salida


def descargar_atlas_selectivo(nombre: str, force: bool = False) -> None:
    destino = ATLAS_FILES[nombre]
    if destino.exists() and not force:
        print(f"Se reutiliza: {destino}")
        return
    config = ATLAS_API_CONFIG[nombre]
    municipios = _obtener_mapeo_municipios(force=force)
    nombre_por_id = {
        indicador_id: variable
        for _, indicador_id, variable in config["indicadores"]
    }
    filas = []
    tamano_lote = 40
    for inicio in range(0, len(municipios), tamano_lote):
        lote = municipios.iloc[inicio : inicio + tamano_lote]
        parametros: list[tuple[str, str]] = [("tip", "AM")]
        parametros.extend(
            ("tv", f"19:{int(valor)}") for valor in lote["id_valor_ine"]
        )
        parametros.extend(
            ("tv", f"{variable}:{valor}")
            for variable, valor in config["filtros"]
        )
        parametros.extend(
            ("tv", f"{variable}:{valor}")
            for variable, valor, _ in config["indicadores"]
        )
        respuesta = requests.get(
            f"{API_BASE}/DATOS_TABLA/{config['tabla']}",
            params=parametros,
            timeout=180,
        )
        respuesta.raise_for_status()
        for serie in respuesta.json():
            metadatos = serie.get("MetaData", [])
            territorio = next(
                (m for m in metadatos if m.get("T3_Variable") == "Municipios"),
                None,
            )
            indicador = next(
                (m for m in metadatos if m.get("Id") in nombre_por_id), None
            )
            if territorio is None or indicador is None:
                continue
            for dato in serie.get("Data", []):
                filas.append(
                    {
                        "cod_ine": str(territorio["Codigo"]).zfill(5),
                        "anio": int(dato["Anyo"]),
                        "variable": nombre_por_id[indicador["Id"]],
                        "valor": dato.get("Valor"),
                    }
                )
    largo = pd.DataFrame(filas)
    if largo.duplicated(["cod_ine", "anio", "variable"]).any():
        raise ValueError(f"Duplicados en descarga API {nombre}")
    salida = largo.pivot(
        index=["cod_ine", "anio"], columns="variable", values="valor"
    ).reset_index()
    salida.columns.name = None
    cobertura = salida.groupby("anio")["cod_ine"].nunique()
    if cobertura.max() > 306 or cobertura.empty:
        raise ValueError(f"Cobertura API inválida en {nombre}: {cobertura.to_dict()}")
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida.sort_values(["cod_ine", "anio"]).to_csv(destino, index=False)
    # La consulta va por lotes de municipios: se anota la tabla consultada,
    # que es lo que identifica la fuente, no cada una de las peticiones.
    record_download(
        destino,
        f"{API_BASE}/DATOS_TABLA/{config['tabla']}",
        organism="Instituto Nacional de Estadística",
        resource=f"Atlas de distribución de renta de los hogares, tabla {config['tabla']} ({nombre})",
        license_url="https://www.ine.es/dyngs/AYU/index.htm?cid=125",
    )
    print(
        f"Descarga selectiva: {destino} ({len(salida):,} filas); "
        f"cobertura {cobertura.to_dict()}"
    )


def _procesar_atlas_municipal(
    ruta: Path,
    columna_indicador: str,
    nombres: dict[str, str],
    filtros: dict[str, str] | None = None,
) -> pd.DataFrame:
    partes = []
    encoding = _encoding_ine(ruta)
    codigos = _codigos_objetivo()
    for df in pd.read_csv(
        ruta, sep=";", encoding=encoding, dtype=str, chunksize=250_000
    ):
        mascara = (
            df["Distritos"].fillna("").str.strip().eq("")
            & df["Secciones"].fillna("").str.strip().eq("")
            & df[columna_indicador].isin(nombres)
        )
        for columna, valor in (filtros or {}).items():
            mascara &= df[columna].eq(valor)
        municipal = df.loc[
            mascara, ["Municipios", "Periodo", "Total", columna_indicador]
        ].copy()
        municipal["cod_ine"] = municipal["Municipios"].str.extract(
            r"^\s*(\d{5})\b"
        )[0]
        municipal = municipal[municipal["cod_ine"].isin(codigos)]
        municipal["anio"] = pd.to_numeric(municipal["Periodo"], errors="coerce")
        municipal["valor"] = _numero_ine(municipal["Total"])
        municipal["variable"] = municipal[columna_indicador].map(nombres)
        partes.append(municipal[["cod_ine", "anio", "variable", "valor"]])
    largo = pd.concat(partes, ignore_index=True)
    if largo.duplicated(["cod_ine", "anio", "variable"]).any():
        raise ValueError(f"Duplicados en tabla Atlas {ruta}")
    salida = largo.pivot(
        index=["cod_ine", "anio"], columns="variable", values="valor"
    ).reset_index()
    salida.columns.name = None
    salida["anio"] = salida["anio"].astype(int)
    return salida


def procesar_atlas() -> pd.DataFrame:
    renta = _procesar_atlas_municipal(
        ATLAS_FILES["renta"],
        "Indicadores de renta media",
        {
        "Renta neta media por persona": "renta_neta_media_persona",
        "Renta neta media por hogar": "renta_neta_media_hogar",
        "Mediana de la renta por unidad de consumo": "mediana_renta_unidad_consumo",
        },
    )
    distribucion = pd.read_csv(
        ATLAS_FILES["distribucion_relativa"], dtype={"cod_ine": str}
    )
    desigualdad = pd.read_csv(
        ATLAS_FILES["desigualdad"], dtype={"cod_ine": str}
    )
    demografia = pd.read_csv(
        ATLAS_FILES["demografia"], dtype={"cod_ine": str}
    )
    salida = renta
    for adicional in (distribucion, desigualdad, demografia):
        salida = salida.merge(
            adicional, on=["cod_ine", "anio"], how="outer", validate="one_to_one"
        )
    salida["fuente"] = (
        "INE, Atlas de distribución de renta de los hogares, "
        "tablas 30824, 30829, 37677 y 30832"
    )
    return salida.sort_values(["cod_ine", "anio"]).reset_index(drop=True)


def procesar_migracion() -> pd.DataFrame:
    df = _leer_ine(RAW_MIGRACION, dtype=str)
    municipal = df[
        df["Municipios"].notna() & df["Sexo"].eq("Ambos sexos")
    ].copy()
    municipal["cod_ine"] = municipal["Municipios"].str.extract(r"^\s*(\d{5})\b")[0]
    municipal["anio"] = pd.to_numeric(municipal["Periodo"], errors="coerce")
    municipal["valor"] = _numero_ine(municipal["Total"])
    tipos = {
        "Saldo total": "saldo_total",
        "Saldo exterior": "saldo_exterior",
        "Saldo interior": "saldo_interior",
    }
    municipal["variable"] = municipal["Tipo de saldo"].map(tipos)
    salida = municipal.pivot(
        index=["cod_ine", "anio"], columns="variable", values="valor"
    ).reset_index()
    salida.columns.name = None
    salida["anio"] = salida["anio"].astype(int)
    salida["fuente"] = f"INE, Estadística de Migraciones y Cambios de Residencia, tabla {MIGRACION_ID}"
    return salida.sort_values(["cod_ine", "anio"]).reset_index(drop=True)


def validar_y_filtrar(df: pd.DataFrame, nombre: str) -> pd.DataFrame:
    codigos = _codigos_objetivo()
    df = df[df["cod_ine"].isin(codigos)].copy()
    if df.duplicated(["cod_ine", "anio"]).any():
        raise ValueError(f"Duplicados municipio-año en {nombre}")
    cobertura = df.groupby("anio")["cod_ine"].nunique()
    if not cobertura.eq(306).all():
        raise ValueError(f"Cobertura distinta de 306/306 en {nombre}: {cobertura.to_dict()}")
    print(f"{nombre}: {len(df):,} filas; cobertura anual {cobertura.to_dict()}")
    return df


def cargar(df: pd.DataFrame, tabla: str, db_url: str) -> None:
    engine = create_engine(db_url)
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
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--no-db", action="store_true")
    parser.add_argument("--db-url", default=os.getenv("DATABASE_URL", DEFAULT_DB_URL))
    args = parser.parse_args()
    if not args.skip_download:
        descargar(MIGRACION_URL, RAW_MIGRACION, args.force_download,
                  recurso=f"Estadística de migraciones, saldos municipales, tabla {MIGRACION_ID}")
        for nombre in ATLAS_IDS:
            if nombre == "renta":
                continue
            descargar_atlas_selectivo(nombre, args.force_download)
    if not RAW_MIGRACION.exists():
        raise FileNotFoundError(RAW_MIGRACION)
    for ruta in ATLAS_FILES.values():
        if not ruta.exists():
            raise FileNotFoundError(ruta)
    socio = validar_y_filtrar(procesar_atlas(), "variables socioeconómicas")
    migracion = validar_y_filtrar(procesar_migracion(), "saldos migratorios")
    OUT_SOCIO.parent.mkdir(parents=True, exist_ok=True)
    socio.to_csv(OUT_SOCIO, index=False)
    migracion.to_csv(OUT_MIGRACION, index=False)
    if not args.no_db:
        cargar(socio, "variables_socioeconomicas_municipales", args.db_url)
        cargar(migracion, "saldos_migratorios_municipales", args.db_url)


if __name__ == "__main__":
    main()
