"""Auditoría y panel IPR-4 relativo: ninguna imputación ni mezcla de universos."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

from analytics.normalization import ajustar_hogares, percentil

ROOT = Path(__file__).resolve().parents[1]
VERSION = "historico-relativo-1.0"
WEIGHTS = dict(zip(("asequibilidad", "turismo", "especulacion", "gentrificacion"),
                   (30 / 85, 20 / 85, 20 / 85, 15 / 85)))
VARIABLES = {
    "asequibilidad": ["ratio_asequibilidad"],
    "turismo": ["vut_por_1000_hab", "vut_por_km2"],
    "especulacion": ["tasa_rotacion", "aceleracion_precio", "desacoplamiento_precio_renta"],
    "gentrificacion": ["log_cambio_renta_neta_media_persona_3a", "brecha_precio_renta_3a",
                       "transformacion_hogares_ajustada_3a"],
}
INPUTS = {
    "asequibilidad": "indicadores_asequibilidad.csv",
    "turismo": "indicadores_turisticos.csv",
    "especulacion": "indicadores_especulativos.csv",
    "gentrificacion": "indicadores_gentrificacion.csv",
    "socio": "variables_socioeconomicas_municipales.csv",
    "renta": "renta_hogares.csv",
    "precios": "precios_vivienda_ministerio_final.csv",
    "poblacion": "poblacion_municipal.csv",
    "vut": "turismo_fuentes.csv",
    "transacciones": "transacciones_vivienda_municipal.csv",
    "parque": "parque_viviendas_2021.csv",
    "futuro": "riesgo_futuro_residencial_score.csv",
    "inputs_futuro": "indicadores_riesgo_futuro.csv",
}
SOURCES = {
    "asequibilidad": "MIVAU valor tasado; INE Atlas 30824",
    "turismo": "INE VUT 39363; padrón; geometría municipal",
    "especulacion": "MIVAU transacciones 34010210; Censo INE 59525; valor tasado; Atlas 30824",
    "gentrificacion": "INE Atlas 30824 y 30832; MIVAU valor tasado",
}
METHOD_NOTES = {
    "precios": "Formato XLS distinto hasta 2009; publicación municipal variable y trimestres suprimidos. Exigir cuatro trimestres.",
    "asequibilidad": "Percentiles anuales de universo variable en origen: recalcular en panel fijo.",
    "turismo": "Snapshots no equivalen a media anual; fijar agosto y población del mismo año.",
    "vut": "Agosto desde 2020; meses disponibles cambian en 2024–2025. No enlazar meses diferentes.",
    "renta": "Atlas: cambios de base poblacional; cambios de difusión 2020 y umbrales relativos 2023. Ver auditoría.",
    "socio": "Atlas: cambio FPC de padrón a censo anual; vigilar saltos demográficos. Umbrales relativos 2023 no entran en score.",
    "poblacion": "Padrón anual; se requiere año exacto, sin arrastre as-of en el panel.",
    "parque": "Censo 2021 fijo; no representa evolución anual del parque.",
    "transacciones": "Excluir años sin cuatro trimestres; no se acredita homogeneidad solo por existencia de filas.",
    "especulacion": "Score publicado solo 2022–2023; inputs anteriores requieren percentiles sobre universo fijo.",
    "gentrificacion": "Versión 2.0, ventanas de tres años; recalcular regresión, winsorización y percentiles sobre el panel.",
    "futuro": "Versión 2.0 ANOMALY; horizonte 2041–2060 y tendencias hasta 2023. No es serie observada.",
    "inputs_futuro": "Clima proyectado y tendencias de periodos diferentes; excluir de IPR histórico observado.",
}
PRICE_LAGS = {"asequibilidad": [0], "especulacion": [0, 1, 2], "gentrificacion": [0, 3]}
RAW_FILES = [
    "data/raw/municipios_306_con_geometria.gpkg",
    "data/raw/ministerio_vivienda/valor_tasado_municipios_25000hab.xls",
    "data/raw/ine_renta/atlas_renta_30824.csv",
    "data/raw/ine_turismo/viviendas_turisticas_39363.csv",
    "data/raw/especulacion/transacciones_municipales_34010210.xls",
    "data/raw/especulacion/parque_viviendas_ine_59525.json",
    "data/raw/ine_gentrificacion/demografia_hogares_30832_selectivo.csv",
]


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_inputs(root: Path = ROOT) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    municipalities = gpd.read_file(root / RAW_FILES[0], ignore_geometry=True)
    municipalities["cod_ine"] = municipalities.cod_ine.astype(str).str.zfill(5)
    if len(municipalities) != 306 or municipalities.cod_ine.nunique() != 306:
        raise ValueError("El universo actual debe contener 306 municipios únicos")
    codes = set(municipalities.cod_ine)
    frames = {}
    for name, file in INPUTS.items():
        frame = pd.read_csv(root / "data/processed" / file,
                            dtype={"cod_ine": str, "id_municipio": str})
        if name == "precios":
            frame = frame.rename(columns={"id_municipio": "cod_ine"})
        frame["cod_ine"] = frame.cod_ine.str.zfill(5)
        frame = frame[frame.cod_ine.isin(codes)].copy()
        if "fecha" in frame:
            frame["fecha"] = pd.to_datetime(frame.fecha, errors="raise")
            frame["anio"] = frame.fecha.dt.year
            key = ["cod_ine", "fecha"]
        elif name == "transacciones":
            key = ["cod_ine", "anio", "trimestre"]
        elif name == "parque":
            key = ["cod_ine", "anio_referencia"]
            frame["anio"] = frame.anio_referencia
        elif name in ("futuro", "inputs_futuro"):
            frame["anio"] = frame.anio_base
            key = ["cod_ine", "anio"]
        else:
            key = ["cod_ine", "anio"]
        if frame[key].isna().any().any() or frame.duplicated(key).any():
            raise ValueError(f"Claves nulas o duplicadas en {file}: {key}")
        frames[name] = frame
    return municipalities.sort_values("cod_ine"), frames


def valid_variables(frame: pd.DataFrame, variables: list[str]) -> pd.Series:
    return np.isfinite(frame[variables]).all(axis=1)


def eligible_layers(frames: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Exige años naturales completos también en los retardos de precio."""
    prices = frames["precios"]
    valid_prices = prices[np.isfinite(prices.valor_total) & prices.valor_total.gt(0)]
    quarters = valid_prices.assign(trimestre=valid_prices.fecha.dt.quarter).groupby(
        ["cod_ine", "anio"]
    ).trimestre.nunique()
    complete_prices = set(quarters[quarters.eq(4)].index)
    layers = {}
    for layer, variables in VARIABLES.items():
        frame = frames[layer].copy()
        ok = valid_variables(frame, variables)
        if layer == "turismo":
            ok &= frame.fecha.dt.month.eq(8) & frame.fecha.dt.day.eq(1)
            ok &= frame.anio_poblacion.eq(frame.anio)
            ok &= frame.poblacion.gt(0) & frame.superficie_km2.gt(0)
            ok &= frame[variables].ge(0).all(axis=1)
        else:
            lags = PRICE_LAGS[layer]
            ok &= pd.Series([
                all((code, year - lag) in complete_prices for lag in lags)
                for code, year in zip(frame.cod_ine, frame.anio)
            ], index=frame.index)
            if layer == "asequibilidad":
                ok &= frame.renta_media.gt(0) & frame.ratio_asequibilidad.gt(0)
            elif layer == "especulacion":
                ok &= frame.elegible_score_principal.eq(True)
                ok &= frame.trimestres_tx.eq(4) & frame.viviendas.gt(0)
                ok &= frame.tasa_rotacion.ge(0) & frame.anio_referencia.eq(2021)
            else:
                ok &= frame.elegible_score.eq(True)
                ok &= valid_variables(frame, ["cambio_pct_hogares_unipersonales_3a",
                                             "cambio_pct_mayor_65_3a", "cambio_pct_menor_18_3a"])
        layers[layer] = frame.loc[ok].copy()
    return layers


def exclusion_reason(code, year, layer, frames):
    frame = frames[layer]
    row = frame[frame.cod_ine.eq(code) & frame.anio.eq(year)]
    if layer == "turismo":
        row = row[row.fecha.dt.month.eq(8)]
    reasons = []
    if row.empty:
        reasons.append("fila fuente ausente")
    else:
        for variable in VARIABLES[layer]:
            if not np.isfinite(row[variable]).all():
                reasons.append(f"{variable} ausente/no finito")
    if layer in PRICE_LAGS:
        prices = frames["precios"]
        for lag in PRICE_LAGS[layer]:
            p = prices[prices.cod_ine.eq(code) & prices.anio.eq(year - lag)]
            p = p[np.isfinite(p.valor_total) & p.valor_total.gt(0)]
            count = p.fecha.dt.quarter.nunique()
            if count != 4:
                reasons.append(f"precio {year - lag}: {count}/4 trimestres válidos")
    return f"{layer}:{year}:" + ", ".join(reasons or ["no cumple reglas de elegibilidad (ver metodología)"])


def select_period(layers: dict[str, pd.DataFrame]) -> tuple[list[int], set[str]]:
    """Mayor tramo consecutivo con las cuatro capas y al menos 90% del universo.

    Conserva el umbral de cobertura de la capa de gentrificación. Desempates:
    mayor panel estable y luego periodo más reciente. Nunca salta años vacíos.
    """
    common = sorted(set.intersection(*(set(f.anio) for f in layers.values())))
    candidates = []
    for start in common:
        codes = None
        for end in range(start, max(common) + 1):
            if end not in common:
                break
            annual = set.intersection(*(set(f.loc[f.anio.eq(end), "cod_ine"])
                                        for f in layers.values()))
            codes = annual if codes is None else codes & annual
            if len(codes) < np.ceil(306 * 0.90):
                break
            if end > start:
                candidates.append((end - start + 1, len(codes), end, start, codes.copy()))
    if not candidates:
        return [], set()
    _, _, end, start, codes = max(candidates, key=lambda c: c[:3])
    return list(range(start, end + 1)), codes


def audit(root: Path = ROOT):
    municipalities, frames = load_inputs(root)
    layers = eligible_layers(frames)
    years, codes = select_period(layers)
    records = []
    # Source-variable audit records zero coverage years explicitly, including gaps.
    source_variables = {
        **VARIABLES,
        "precios": ["valor_total"], "renta": ["renta_media"],
        "socio": ["renta_neta_media_persona", "pct_hogares_unipersonales", "pct_mayor_65", "pct_menor_18"],
        "poblacion": ["poblacion"], "vut": ["viviendas_turisticas", "plazas"],
        "transacciones": ["compraventas"], "parque": ["viviendas"],
        "futuro": ["score_riesgo_futuro"],
        "inputs_futuro": ["proyeccion_duracion_max_ola_calor_dias", "proyeccion_grados_dia_refrigeracion",
                          "proyeccion_racha_seca_max_dias", "tendencia_asequibilidad",
                          "tendencia_turismo", "tendencia_gentrificacion"],
    }
    first = min(int(f.anio.min()) for f in frames.values())
    last = max(int(f.anio.max()) for f in frames.values())
    for name, variables in source_variables.items():
        frame = frames[name]
        for variable in variables:
            valid = frame[np.isfinite(frame[variable])]
            available = set(valid.anio)
            gaps = sorted(set(range(int(valid.anio.min()), int(valid.anio.max()) + 1)) - available) if available else []
            for year in range(first, last + 1):
                part = valid[valid.anio.eq(year)]
                records.append({
                    "componente": name, "variable": variable, "anio": year,
                    "archivo": f"data/processed/{INPUTS[name]}",
                    "fuente": SOURCES.get(name, {
                        "precios": "MIVAU valor tasado", "renta": "INE Atlas 30824",
                        "socio": "INE Atlas 30824 y 30832", "poblacion": "INE padrón municipal",
                        "vut": "INE VUT 39363", "transacciones": "MIVAU 34010210",
                        "parque": "INE Censo 59525", "futuro": "ADAPTECCA y tendencias de capas",
                        "inputs_futuro": "ADAPTECCA y tendencias de capas",
                    }.get(name)),
                    "comparabilidad": "no es observación anual" if name in ("futuro", "inputs_futuro") else "condicionada; ver AUDITORIA_IPR_HISTORICO.md",
                    "cambios_metodologicos": METHOD_NOTES[name],
                    "primer_anio": int(valid.anio.min()) if available else None,
                    "ultimo_anio": int(valid.anio.max()) if available else None,
                    "frecuencia": "snapshot" if name in ("vut", "turismo") else "trimestral" if name in ("precios", "transacciones") else "base prospectiva" if name in ("futuro", "inputs_futuro") else "censo fijo" if name == "parque" else "anual",
                    "municipios_validos": part.cod_ine.nunique(), "observaciones": len(part),
                    "cobertura_pct": 100 * part.cod_ine.nunique() / 306,
                    "anios_ausentes": json.dumps(gaps),
                })
    coverage = pd.DataFrame(records)
    universe = municipalities[["cod_ine", "nombre"]].copy()
    universe["included"] = universe.cod_ine.isin(codes)
    universe["reason"] = universe.cod_ine.map(lambda code: "; ".join(
        exclusion_reason(code, year, layer, frames)
        for year in years for layer, frame in layers.items()
        if not ((frame.cod_ine == code) & (frame.anio == year)).any()
    ) if years else "sin periodo histórico viable")
    universe["start_year"] = years[0] if years else None
    universe["end_year"] = years[-1] if years else None
    panel_coverage = pd.DataFrame([
        {"anio": year, "componente": layer, "municipios_elegibles": int(frame[frame.anio.eq(year)].cod_ine.nunique()),
         "municipios_panel": len(set(frame.loc[frame.anio.eq(year), "cod_ine"]) & codes)}
        for year in range(first, last + 1) for layer, frame in layers.items()
    ])
    paths = [f"data/processed/{file}" for file in INPUTS.values()] + RAW_FILES
    paths += [str(p.relative_to(root)) for p in sorted((root / "data/raw/ine_turismo/poblacion_provincias").glob("*.csv"))]
    paths += ["analytics/historical.py", "analytics/normalization.py"]
    sources = [{"path": path, "sha256": sha256(root / path) if (root / path).exists() else None}
               for path in sorted(set(paths))]
    digest = hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()
    metadata = {
        "calculation_version": VERSION, "dataset_sha256": digest,
        "status": "viable" if years else "blocked", "years": years,
        "municipality_count": len(codes), "current_universe_count": 306,
        "tourism_month": 8, "weights": WEIGHTS,
        "normalization": "percentiles_anuales_universo_fijo",
        "sources": sources,
        "limitations": ["Posición relativa; no mide subidas generalizadas sin cambios de orden.",
                        "No equivale al IPR nacional 306/306 de 2023 ni al IPR-5 prospectivo.",
                        "Atlas: cambios en base poblacional; interpretar con cautela los indicadores demográficos.",
                        "Serie corta y ventanas trianuales solapadas; no identifica cambios estructurales ni causalidad."],
    }
    return frames, layers, coverage, panel_coverage, universe, metadata


def calculate(layers, universe: pd.DataFrame, metadata: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    years = metadata["years"]
    codes = set(universe.loc[universe.included, "cod_ine"])
    if metadata["status"] != "viable" or len(years) < 2 or len(codes) < 2:
        raise ValueError("No existe un histórico comparable: consultar auditoría antes de calcular")
    if len(codes) != metadata["municipality_count"] or universe.cod_ine.duplicated().any():
        raise ValueError("El universo no coincide con el manifiesto")
    components = []
    for layer, variables in VARIABLES.items():
        frame = layers[layer]
        frame = frame[frame.cod_ine.isin(codes) & frame.anio.isin(years)].copy()
        if frame.duplicated(["cod_ine", "anio"]).any() or len(frame) != len(codes) * len(years):
            raise ValueError(f"Universo inconsistente o duplicados: {layer}")
        for year, part in frame.groupby("anio"):
            part = part.sort_values("cod_ine").copy()
            if set(part.cod_ine) != codes:
                raise ValueError(f"Universo inconsistente: {layer}/{year}")
            if layer == "gentrificacion":
                part[variables[-1]] = ajustar_hogares(part)
            if not valid_variables(part, variables).all():
                raise ValueError(f"Valores no finitos: {layer}/{year}")
            normalized = []
            for variable in variables:
                raw = part[variable]
                transformed = raw.clip(*raw.quantile([0.01, 0.99])) if layer == "gentrificacion" else raw
                normalized.append(percentil(transformed))
            layer_score = sum(normalized) / len(normalized)
            integrated_score = percentil(layer_score)
            for index, row in part.iterrows():
                components.append({
                    "cod_ine": row.cod_ine, "anio": int(year), "component": layer,
                    "value": float(integrated_score.loc[index]),
                    "layer_score": float(layer_score.loc[index]),
                    "weight": WEIGHTS[layer],
                    "contribution": float(integrated_score.loc[index] * WEIGHTS[layer]),
                    "raw_values": json.dumps({v: float(row[v]) for v in variables}, sort_keys=True),
                    "source_file": f"data/processed/{INPUTS[layer]}",
                    "source_key": f"{row.cod_ine}/{year}-08-01" if layer == "turismo" else f"{row.cod_ine}/{year}",
                    "calculation_version": VERSION,
                })
    components = pd.DataFrame(components).sort_values(["cod_ine", "anio", "component"])
    components["delta_component"] = components.groupby(["cod_ine", "component"]).value.diff()
    components["delta_contribution"] = components.groupby(["cod_ine", "component"]).contribution.diff()
    scores = components.groupby(["cod_ine", "anio"], as_index=False).contribution.sum().rename(columns={"contribution": "ipr_score"})
    # Empates estables frente a diferencias de coma flotante y lectura de CSV.
    ranking_values = scores.ipr_score.round(10)
    scores["ipr_percentile"] = ranking_values.groupby(scores.anio).transform(percentil)
    scores["rank"] = ranking_values.groupby(scores.anio).rank(ascending=False, method="min").astype(int)
    scores["delta_ipr"] = scores.groupby("cod_ine").ipr_score.diff()
    scores["delta_since_start"] = scores.ipr_score - scores.groupby("cod_ine").ipr_score.transform("first")
    scores["rank_change"] = scores.groupby("cod_ine")["rank"].diff()
    scores["calculation_version"] = VERSION
    scores["dataset_sha256"] = metadata["dataset_sha256"]
    validate_results(scores, components, years, codes)
    return scores, components


def validate_results(scores, components, years, codes):
    if sorted(years) != list(range(min(years), max(years) + 1)):
        raise ValueError("Los años deben ser consecutivos")
    for frame, key in [(scores, ["cod_ine", "anio", "calculation_version"]),
                       (components, ["cod_ine", "anio", "component", "calculation_version"])]:
        if frame.duplicated(key).any() or set(frame.anio) != set(years):
            raise ValueError("Duplicados o años inesperados")
        if not all(set(g.cod_ine) == codes for _, g in frame.groupby("anio")):
            raise ValueError("Universo municipal no constante")
    if len(scores) != len(years) * len(codes) or len(components) != len(scores) * len(WEIGHTS):
        raise ValueError("Observaciones ausentes")
    if not scores.ipr_score.between(0, 100).all() or not components.value.between(0, 100).all():
        raise ValueError("IPR o componentes fuera de rango")
    if not components.groupby(["cod_ine", "anio"]).component.agg(set).map(lambda s: s == set(WEIGHTS)).all():
        raise ValueError("Componentes requeridos ausentes")
    expected = components.groupby(["cod_ine", "anio"]).contribution.sum()
    if not np.allclose(expected, scores.set_index(["cod_ine", "anio"]).ipr_score.reindex(expected.index)):
        raise ValueError("Contribuciones inconsistentes")
    if not np.allclose(components.weight, components.component.map(WEIGHTS)) or not np.allclose(
        components.contribution, components.value * components.weight
    ):
        raise ValueError("Ponderaciones o contribuciones incorrectas")
    if not components.layer_score.between(0, 100).all():
        raise ValueError("Score de capa fuera de rango")
    ordered = scores.sort_values(["cod_ine", "anio"])
    checks = {
        "delta_ipr": ordered.groupby("cod_ine").ipr_score.diff(),
        "delta_since_start": ordered.ipr_score - ordered.groupby("cod_ine").ipr_score.transform("first"),
        "rank": ordered.ipr_score.round(10).groupby(ordered.anio).rank(ascending=False, method="min"),
        "ipr_percentile": ordered.ipr_score.round(10).groupby(ordered.anio).transform(percentil),
    }
    checks["rank_change"] = checks["rank"].groupby(ordered.cod_ine).diff()
    for name, expected in checks.items():
        if not np.allclose(ordered[name], expected, equal_nan=True):
            raise ValueError(f"Métrica temporal incorrecta: {name}")
    ordered_components = components.sort_values(["cod_ine", "component", "anio"])
    for name, source in [("delta_component", "value"), ("delta_contribution", "contribution")]:
        expected = ordered_components.groupby(["cod_ine", "component"])[source].diff()
        if not np.allclose(ordered_components[name], expected, equal_nan=True):
            raise ValueError(f"Métrica temporal incorrecta: {name}")


def persist(scores, components, universe, metadata, db_url, root: Path = ROOT):
    """Reemplazo atómico de esta versión; otras versiones permanecen intactas."""
    engine = create_engine(db_url)
    validate_results(scores, components, metadata["years"], set(universe.loc[universe.included, "cod_ine"]))
    if metadata["calculation_version"] != VERSION or not scores.calculation_version.eq(VERSION).all() or not components.calculation_version.eq(VERSION).all():
        raise ValueError("Versión de cálculo inconsistente")
    if not scores.dataset_sha256.eq(metadata["dataset_sha256"]).all():
        raise ValueError("Huella de datos inconsistente")
    with engine.begin() as conn:
        conn.exec_driver_sql((root / "sql/20_ipr_historico.sql").read_text())
        old = conn.execute(text("SELECT dataset_sha256 FROM ipr_historical_runs WHERE calculation_version=:v"), {"v": VERSION}).scalar()
        if old and old != metadata["dataset_sha256"]:
            raise ValueError("Los inputs han cambiado: publicar una nueva calculation_version")
        if old:
            count = conn.execute(text("SELECT count(*) FROM ipr_historical_scores WHERE calculation_version=:v"), {"v": VERSION}).scalar()
            component_count = conn.execute(text("SELECT count(*) FROM ipr_historical_components WHERE calculation_version=:v"), {"v": VERSION}).scalar()
            if count != len(scores) or component_count != len(components):
                raise ValueError("La versión persistida está incompleta")
            return
        conn.execute(text("INSERT INTO ipr_historical_runs (calculation_version,dataset_sha256,metadata) VALUES (:v,:h,CAST(:m AS JSONB))"),
                     {"v": VERSION, "h": metadata["dataset_sha256"], "m": json.dumps(metadata)})
        u = universe.copy()
        u["calculation_version"] = VERSION
        u.to_sql("historical_municipality_universe", conn, if_exists="append", index=False, method="multi")
        scores.to_sql("ipr_historical_scores", conn, if_exists="append", index=False, method="multi")
        components.to_sql("ipr_historical_components", conn, if_exists="append", index=False, method="multi")
    engine.dispose()


def write_audit(coverage, panel_coverage, universe, metadata, output: Path):
    output.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(output / "coverage.csv", index=False)
    panel_coverage.to_csv(output / "eligible_coverage.csv", index=False)
    universe.to_csv(output / "historical_municipality_universe.csv", index=False)
    (output / "manifest.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
