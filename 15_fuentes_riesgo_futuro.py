#!/usr/bin/env python3
"""Descarga proyecciones municipales de AdapteCCa y audita fuentes complementarias."""

from __future__ import annotations

import argparse
import concurrent.futures
import time
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from reproducibilidad.descargas import record_download

BASE_URL = "https://escenarios.adaptecca.es"
MUNICIPIOS_FILE = Path("data/raw/municipios_306_con_geometria.gpkg")
OUT_DIR = Path("data/raw/riesgo_futuro")
OUT_CLIMA = OUT_DIR / "adaptecca_proyecciones_municipales.csv"
OUT_MAPEO = OUT_DIR / "adaptecca_mapeo_municipios.csv"
OUT_AUDITORIA = Path("data/processed/auditoria_fuentes_riesgo_futuro.csv")
VARIABLES = {
    "tasmaxhwdmax": "duracion_max_ola_calor_dias",
    "cdd": "grados_dia_refrigeracion",
    "prspellb1": "racha_seca_max_dias",
}
ALIAS_ADAPTECCA = {
    "03009": "Alcoy/Alcoi",
    "03014": "Alicante/Alacant",
    "03050": "el Campello",
    "03065": "Elche/Elx",
    "07040": "Palma de Mallorca",
    "12126": "la Vall d'Uixó",
    "15030": "A Coruña",
    "28127": "Las Rozas de Madrid",
    "35014": "La Oliva",
    "35016": "Las Palmas de Gran Canaria",
    "41081": "La Rinconada",
}
ESCENARIO = "ssp245"


def normalizar(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor))
    return "".join(c for c in texto if not unicodedata.combining(c)).upper().strip()


def universo() -> pd.DataFrame:
    df = gpd.read_file(MUNICIPIOS_FILE, ignore_geometry=True)
    df["cod_ine"] = df["cod_ine"].astype(str).str.zfill(5)
    df = df[["cod_ine", "nombre", "provincia_norm"]].rename(
        columns={"provincia_norm": "provincia"}
    )
    diccionario = pd.read_csv(
        "data/processed/municipios_ine.csv", dtype={"id_municipio": str}
    )[["id_municipio", "nombre", "provincia"]].rename(
        columns={
            "id_municipio": "cod_ine",
            "nombre": "nombre_oficial",
            "provincia": "provincia_oficial",
        }
    )
    df = df.merge(diccionario, on="cod_ine", how="left", validate="one_to_one")
    df["nombre"] = df["nombre_oficial"].fillna(df["nombre"])
    df["provincia"] = df["provincia_oficial"].fillna(df["provincia"])
    df = df[["cod_ine", "nombre", "provincia"]]
    df = df.drop_duplicates("cod_ine").sort_values("cod_ine")
    if len(df) != 306:
        raise ValueError(f"Universo inesperado: {len(df)} municipios")
    return df


def _get_json(path: str, params: dict, intentos: int = 4) -> object:
    for intento in range(intentos):
        try:
            respuesta = requests.get(
                f"{BASE_URL}/{path}", params=params, timeout=60
            )
            respuesta.raise_for_status()
            return respuesta.json()
        except (requests.RequestException, ValueError):
            if intento == intentos - 1:
                raise
            time.sleep(1.5 * (intento + 1))
    raise RuntimeError("Error de red no recuperable")


def buscar_region(fila: dict) -> dict:
    consultas = [fila["nombre"]]
    if fila["cod_ine"] in ALIAS_ADAPTECCA:
        consultas.insert(0, ALIAS_ADAPTECCA[fila["cod_ine"]])
    consultas.extend(p.strip() for p in fila["nombre"].split("/") if p.strip())
    consultas.append(
        fila["nombre"]
        .replace(", El", "")
        .replace(", La", "")
        .replace(", Los", "")
        .replace(", Las", "")
        .replace(", L'", "")
    )
    candidatos_por_id = {}
    for consulta in dict.fromkeys(consultas):
        for candidato in _get_json(
            "map/regions", {"term": consulta, "regionSet": "MUNICIPALITIES"}
        ):
            candidatos_por_id[candidato["id"]] = candidato
    candidatos = list(candidatos_por_id.values())
    nombre = normalizar(fila["nombre"])
    provincia = normalizar(fila["provincia"])
    exactos = [
        c
        for c in candidatos
        if normalizar(c["name"]) == nombre
        and (
            normalizar(c.get("province", "")) == provincia
            or normalizar(c.get("province", "")) in provincia
            or provincia in normalizar(c.get("province", ""))
        )
    ]
    if len(exactos) != 1:
        variantes = {normalizar(q) for q in consultas}
        exactos = [c for c in candidatos if normalizar(c["name"]) in variantes]
    if len(exactos) != 1 and fila["cod_ine"] in ALIAS_ADAPTECCA:
        alias = normalizar(ALIAS_ADAPTECCA[fila["cod_ine"]])
        exactos = [
            c
            for c in candidatos
            if alias in normalizar(c["name"])
            and (
                normalizar(c.get("province", "")) in provincia
                or provincia in normalizar(c.get("province", ""))
            )
        ]
    if len(exactos) != 1 and len(candidatos) == 1:
        exactos = candidatos
    return {
        **fila,
        "adaptecca_id": exactos[0]["id"] if len(exactos) == 1 else np.nan,
        "estado_mapeo": "ok" if len(exactos) == 1 else f"ambiguo_{len(exactos)}",
    }


def crear_mapeo(municipios: pd.DataFrame, workers: int, force: bool = False) -> pd.DataFrame:
    if OUT_MAPEO.exists() and not force:
        previo = pd.read_csv(OUT_MAPEO, dtype={"cod_ine": str})
        if (
            len(previo) == 306
            and set(previo["cod_ine"]) == set(municipios["cod_ine"])
            and not previo["cod_ine"].duplicated().any()
            and previo["adaptecca_id"].notna().all()
            and not previo["adaptecca_id"].duplicated().any()
        ):
            return previo
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        filas = list(pool.map(buscar_region, municipios.to_dict("records")))
    mapeo = pd.DataFrame(filas).sort_values("cod_ine")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    mapeo.to_csv(OUT_MAPEO, index=False)
    record_download(
        OUT_MAPEO, f"{BASE_URL}/api/map/regions",
        organism="AdapteCCa · AEMET y Oficina Española de Cambio Climático",
        resource="Catálogo de regiones municipales de AdapteCCa",
        license_url="https://adaptecca.es/aviso-legal",
    )
    fallos = mapeo[mapeo["adaptecca_id"].isna()]
    if not fallos.empty:
        raise ValueError(
            "No se resolvieron todos los municipios en AdapteCCa: "
            + ", ".join(fallos["cod_ine"] + " " + fallos["nombre"])
        )
    return mapeo


def descargar_serie(tarea: tuple[str, int, str, str]) -> list[dict]:
    cod_ine, region_id, variable, grupo = tarea
    datos = _get_json(
        "temporal/serie",
        {
            "scenario": ESCENARIO,
            "variable": variable,
            "temporalFilter": "year",
            "valueType": "ANOMALY",
            "group": grupo,
            "region": "MUNICIPALITIES",
            "ids": int(region_id),
        },
    )
    serie = datos.get("model", {}).get("data") or {}
    filas = []
    for fecha, modelos in serie.items():
        valores = [m.get("data") for m in modelos if m.get("data") is not None]
        if valores:
            filas.append(
                {
                    "cod_ine": cod_ine,
                    "anio": int(fecha[:4]),
                    "variable": VARIABLES[variable],
                    "valor_mediana_ensemble": float(np.median(valores)),
                    "valor_p25_ensemble": float(np.percentile(valores, 25)),
                    "valor_p75_ensemble": float(np.percentile(valores, 75)),
                    "n_modelos": len(valores),
                    "escenario": ESCENARIO,
                    "fuente": "AEMET/OECC AdapteCCa CMIP6",
                }
            )
    return filas


def descargar_clima(mapeo: pd.DataFrame, workers: int) -> pd.DataFrame:
    tareas = [
        (
            f.cod_ine,
            int(f.adaptecca_id),
            variable,
            "CMIP6-canarias" if f.cod_ine[:2] in {"35", "38"} else "CMIP6-spain",
        )
        for f in mapeo.itertuples()
        for variable in VARIABLES
    ]
    filas: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for resultado in pool.map(descargar_serie, tareas):
            filas.extend(resultado)
    clima = pd.DataFrame(filas).sort_values(["cod_ine", "variable", "anio"])
    clima.to_csv(OUT_CLIMA, index=False)
    # Son miles de series por municipio y variable: se anota el servicio
    # consultado, que es lo que identifica la fuente y su aviso legal.
    record_download(
        OUT_CLIMA, f"{BASE_URL}/api",
        organism="AdapteCCa · AEMET y Oficina Española de Cambio Climático",
        resource="Escenarios de cambio climático CMIP6, trayectoria SSP2-4.5",
        license_url="https://adaptecca.es/aviso-legal",
    )
    return clima


def auditar(clima: pd.DataFrame, mapeo: pd.DataFrame) -> pd.DataFrame:
    ventana = clima[clima["anio"].between(2041, 2060)]
    cobertura_ventana = (
        ventana.groupby(["variable", "cod_ine"])["anio"].nunique()
    )
    incompletas = cobertura_ventana[~cobertura_ventana.eq(20)]
    if not incompletas.empty:
        raise ValueError(
            "Series climáticas incompletas en la ventana 2041–2060: "
            f"{len(incompletas)}"
        )
    if set(mapeo["cod_ine"]) != set(universo()["cod_ine"]):
        raise ValueError("El mapeo AdapteCCa no coincide con el universo vigente")
    filas = []
    for variable in VARIABLES.values():
        parte = clima[clima["variable"].eq(variable)]
        filas.append(
            {
                "fuente": "AdapteCCa CMIP6 SSP2-4.5",
                "componente": variable,
                "municipios": parte["cod_ine"].nunique(),
                "pct_universo": 100 * parte["cod_ine"].nunique() / 306,
                "anio_min": parte["anio"].min(),
                "anio_max": parte["anio"].max(),
                "apto_score_principal": parte["cod_ine"].nunique() / 306 >= 0.95,
                "decision": (
                    "principal_con_exclusion_explicita"
                    if parte["cod_ine"].nunique() / 306 >= 0.95
                    else "complementario"
                ),
            }
        )
    filas.extend(
        [
            {
                "fuente": "MITECO SNCZI",
                "componente": "inundacion_fluvial_costera",
                "municipios": np.nan,
                "pct_universo": np.nan,
                "anio_min": np.nan,
                "anio_max": np.nan,
                "apto_score_principal": False,
                "decision": "complementario: ausencia de cartografia no equivale a riesgo cero",
            },
            {
                "fuente": "Registros CCAA",
                "componente": "certificados_energeticos",
                "municipios": np.nan,
                "pct_universo": np.nan,
                "anio_min": np.nan,
                "anio_max": np.nan,
                "apto_score_principal": False,
                "decision": "complementario: sin registro nacional municipal armonizado",
            },
        ]
    )
    salida = pd.DataFrame(filas)
    OUT_AUDITORIA.parent.mkdir(parents=True, exist_ok=True)
    salida.to_csv(OUT_AUDITORIA, index=False)
    if mapeo["adaptecca_id"].duplicated().any():
        raise ValueError("Un mismo identificador AdapteCCa se asignó a varios municipios")
    return salida


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--reuse", action="store_true", help="Reutiliza la descarga climática")
    parser.add_argument("--force-download", action="store_true",
                        help="Rehace el mapeo de regiones aunque ya esté descargado")
    args = parser.parse_args()
    municipios = universo()
    mapeo = crear_mapeo(municipios, args.workers, force=args.force_download)
    if args.reuse and OUT_CLIMA.exists():
        clima = pd.read_csv(OUT_CLIMA, dtype={"cod_ine": str})
    else:
        clima = descargar_clima(mapeo, args.workers)
    auditoria = auditar(clima, mapeo)
    print(auditoria.to_string(index=False))


if __name__ == "__main__":
    main()
