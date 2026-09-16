"""DQS del IPR-4: evidencia observable, independiente del valor del índice."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

VERSION = "dqs-ipr4-1.0"
WEIGHTS = (0.625, 0.375)
COMPONENTS = {
    "asequibilidad": ("indicadores_asequibilidad.csv", "puntuacion_asequibilidad", "anio"),
    "turismo": ("presion_turistica_score.csv", "score_presion_turistica", "fecha"),
    "especulacion": ("presion_especulativa_score.csv", "score_presion_especulativa", "anio"),
    "gentrificacion": ("riesgo_gentrificacion_score.csv", "score_riesgo_gentrificacion", "anio"),
}
EVIDENCE_FILES = [v[0] for v in COMPONENTS.values()] + [
    "indicadores_turisticos.csv", "indicadores_especulativos.csv",
    "ipr_validaciones.csv", "validaciones_integracion.csv",
]


def level(score):
    if score is None:
        return None
    return "alta" if score >= 85 else "media" if score >= 70 else "baja" if score >= 50 else "muy_baja"


def recency(reference_year: int, source_year: int) -> float:
    if not (1900 <= source_year <= reference_year <= 2100 and int(source_year) == source_year and int(reference_year) == reference_year):
        raise ValueError("Periodo estadístico inválido o posterior al IPR")
    return max(0.0, 100.0 - 10 * max(0, reference_year - source_year - 1))


def weighted(coverage, recent, weights=WEIGHTS):
    if len(weights) != 2 or any(not math.isfinite(w) or w < 0 for w in weights) or not math.isclose(sum(weights), 1):
        raise ValueError("Los pesos no negativos deben sumar 1")
    return None if recent is None else weights[0] * coverage + weights[1] * recent


def score_components(evidence: list[dict], year: int, weights=WEIGHTS) -> dict:
    """Coverage cuenta capas válidas; Recency promedia las capas disponibles.

    Un fallo detectable invalida la evidencia, no crea un score de consistencia.
    La falta de periodo en una capa disponible impide agregar el DQS.
    """
    if not 1900 <= year <= 2100 or int(year) != year:
        raise ValueError("Año inválido")
    if len(evidence) != 4 or {e["component"] for e in evidence} != set(COMPONENTS):
        raise ValueError("Se requieren las cuatro capas únicas del IPR-4")
    weighted(0, 0, weights)
    components = []
    for item in evidence:
        item = dict(item)
        issues = list(item.get("issues", []))
        value = item.pop("value", None)
        available = value is not None and math.isfinite(value) and 0 <= value <= 100
        if value is not None and not available:
            issues.append("Valor del componente fuera de rango o no finito")
        if not available:
            issues.append("Componente ausente o no utilizable")
        source_year = item.get("source_year")
        recent = None
        if available:
            if source_year is None:
                issues.append("Periodo estadístico no trazable")
            else:
                recent = recency(year, source_year)
                if source_year < year:
                    issues.append(f"Fuente de referencia {source_year}; desfase de {year - source_year} años")
        components.append({
            **item, "coverage_score": 100.0 if available else 0.0,
            "recency_score": recent, "consistency_score": None,
            "quality_score": weighted(100, recent, weights) if available else 0.0,
            "issues": issues,
        })
    available = [c for c in components if c["coverage_score"] == 100]
    coverage = 100 * len(available) / 4
    recent = (sum(c["recency_score"] for c in available) / len(available)
              if available and all(c["recency_score"] is not None for c in available) else None)
    score = weighted(coverage, recent, weights)
    issues = [f"{c['component']}: {issue}" for c in components for issue in c["issues"]]
    if not available:
        issues.append("Sin información suficiente para calcular DQS")
    return {"score": score, "level": level(score), "coverage": coverage,
            "recency": recent, "consistency": None, "components": components,
            "issues": issues, "scope": "ipr4_observado", "calculation_version": VERSION}


def read_frame(path: Path, period: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"cod_ine": str})
    if not df.cod_ine.str.fullmatch(r"\d{5}").all():
        raise ValueError(f"{path.name}: identificadores inválidos")
    if df.duplicated(["cod_ine", period]).any():
        raise ValueError(f"{path.name}: claves duplicadas")
    if period == "fecha":
        df[period] = pd.to_datetime(df[period], errors="raise")
        years = df[period].dt.year
    else:
        years = pd.to_numeric(df[period], errors="raise")
    if not (years.between(1900, 2100) & years.eq(years.astype(int))).all():
        raise ValueError(f"{path.name}: años inválidos")
    return df


def calculate(processed: Path, ipr: pd.DataFrame, valid_codes: set[str]):
    if ipr.empty or ipr.duplicated(["cod_ine", "anio"]).any():
        raise ValueError("IPR vacío o con claves duplicadas")
    if not set(ipr.cod_ine) <= valid_codes:
        raise ValueError("Municipios IPR ajenos al universo")
    # Reutilizar los informes del pipeline; no convertir sus OK globales en 100 municipal.
    for filename in ("ipr_validaciones.csv", "validaciones_integracion.csv"):
        checks = pd.read_csv(processed / filename)
        if checks.empty or not checks.estado.isin(["OK", "AVISO"]).all():
            raise ValueError(f"Validaciones pendientes o fallidas: {filename}")
    sources = {c: read_frame(processed / spec[0], spec[2]) for c, spec in COMPONENTS.items()}
    tourism = read_frame(processed / "indicadores_turisticos.csv", "fecha")
    speculation = read_frame(processed / "indicadores_especulativos.csv", "anio")
    for name, frame in {**sources, "indicadores_turisticos": tourism, "indicadores_especulativos": speculation}.items():
        if not set(frame.cod_ine) <= valid_codes:
            raise ValueError(f"{name}: municipios ajenos al universo")
    timestamp = datetime.now(timezone.utc).isoformat()
    rows, component_rows, audit = [], [], []
    for year, cohort in ipr.groupby("anio", sort=True):
        if not 1900 <= year <= 2100 or int(year) != year:
            raise ValueError("Año IPR inválido")
        year = int(year)
        selected = {}
        for component, (_, score_col, period) in COMPONENTS.items():
            frame = sources[component]
            # El mes utilizado se conserva en cada fila del IPR; nunca usar el último disponible.
            cut = frame[frame.fecha.dt.year.eq(year)] if period == "fecha" else frame[frame.anio.eq(year)]
            if period == "fecha":
                cut = cut.merge(cohort[["cod_ine", "mes_turismo"]], on="cod_ine", validate="many_to_one")
                cut = cut[cut.fecha.dt.month.eq(cut.mes_turismo)]
            selected[component] = cut
            valid = pd.to_numeric(cut[score_col], errors="coerce").between(0, 100)
            audit.append({"component": component, "anio": year,
                          "municipios_fuente": cut.cod_ine.nunique(),
                          "municipios_valor_valido": cut.loc[valid, "cod_ine"].nunique(),
                          "cobertura_pct": 100 * cut.loc[valid, "cod_ine"].nunique() / len(valid_codes),
                          "missing_valor": int(cut[score_col].isna().sum()),
                          "municipios_sin_fila": len(valid_codes - set(cut.cod_ine)),
                          "valores_invalidos": int((cut[score_col].notna() & ~valid).sum()),
                          "duplicados": 0, "actualizacion_fuente": None,
                          "periodo_min": str(frame[period].min()), "periodo_max": str(frame[period].max())})
        for _, index in cohort.iterrows():
            evidence = []
            for component, (_, score_col, period) in COMPONENTS.items():
                cut = selected[component]
                match = cut[cut.cod_ine.eq(index.cod_ine)]
                if period == "fecha":
                    match = match[match.fecha.dt.month.eq(int(index.mes_turismo))]
                if len(match) > 1:
                    raise ValueError("Corte del componente ambiguo")
                value = None if match.empty or pd.isna(match.iloc[0][score_col]) else float(match.iloc[0][score_col])
                original = index[f"score_origen_{component}"]
                if not ((pd.isna(original) and value is None) or
                        (value is not None and math.isclose(float(original), value, abs_tol=1e-8))):
                    raise ValueError(f"{component}/{index.cod_ine}/{year}: fuente no coincide con IPR; regenerar el índice")
                source_year = year if value is not None else None
                period_label = str(year)
                if component == "turismo" and not match.empty:
                    date = match.iloc[0].fecha
                    period_label = date.date().isoformat()
                    metadata = tourism[tourism.cod_ine.eq(index.cod_ine) & tourism.fecha.eq(date)]
                    source_year = None if metadata.empty or pd.isna(metadata.iloc[0].anio_poblacion) else min(year, metadata.iloc[0].anio_poblacion)
                    if not metadata.empty and metadata.iloc[0].anio_poblacion > year:
                        raise ValueError("Población turística posterior al IPR")
                elif component == "especulacion" and value is not None:
                    metadata = speculation[speculation.cod_ine.eq(index.cod_ine) & speculation.anio.eq(year)]
                    source_year = None if metadata.empty or pd.isna(metadata.iloc[0].anio_referencia) else metadata.iloc[0].anio_referencia
                    period_label = f"{year}; parque residencial {source_year}"
                elif component == "gentrificacion":
                    period_label = f"{year - 3}–{year} (ventana de cambio)"
                if source_year is not None:
                    recency(year, source_year)  # Rechaza metadatos fraccionarios o futuros.
                    source_year = int(source_year)
                evidence.append({"component": component, "value": value,
                                 "source_year": source_year, "statistical_period": period_label})
            quality = score_components(evidence, year)
            quality["calculated_at"] = timestamp
            rows.append({"cod_ine": index.cod_ine, "anio": year, "data_quality": quality})
            for c in quality["components"]:
                component_rows.append({"cod_ine": index.cod_ine, "anio": year,
                                       "calculation_version": VERSION, **c})
    return rows, component_rows, audit


def sensitivity(rows):
    report = []
    for year in sorted({r["anio"] for r in rows}):
        cohort = [r for r in rows if r["anio"] == year and r["data_quality"]["score"] is not None]
        base = pd.Series([r["data_quality"]["score"] for r in cohort], dtype=float)
        for name, weights in {"principal": WEIGHTS, "iguales": (0.5, 0.5), "cobertura_75": (0.75, 0.25)}.items():
            scores = pd.Series([weighted(r["data_quality"]["coverage"], r["data_quality"]["recency"], weights) for r in cohort], dtype=float)
            changes = [r["cod_ine"] for r, s in zip(cohort, scores) if level(s) != r["data_quality"]["level"]]
            # Pearson sobre rangos medios equivale a Spearman y no requiere scipy.
            corr = base.rank().corr(scores.rank()) if base.nunique() > 1 and scores.nunique() > 1 else None
            report.append({"anio": year, "escenario": name, "pesos": list(weights),
                           "municipios": len(cohort), "spearman": corr,
                           "nota": "Ranking constante: correlación no definida" if corr is None else None,
                           "cambios_categoria": changes,
                           "cambio_score_max": float((scores - base).abs().max()) if len(base) else None,
                           "cambio_rango_max": float((scores.rank() - base.rank()).abs().max()) if len(base) else None})
    return report


def persist(connection, rows, schema: Path):
    connection.exec_driver_sql(schema.read_text())
    for row in rows:
        q = row["data_quality"]
        connection.execute(text("""
            INSERT INTO data_quality_municipal
              (cod_ine,anio,calculation_version,dqs_score,quality_level,coverage_score,
               recency_score,consistency_score,calculated_at,details)
            VALUES (:cod,:year,:version,:score,:level,:coverage,:recency,NULL,:at,CAST(:details AS jsonb))
            ON CONFLICT (cod_ine,anio,calculation_version) DO UPDATE SET
              dqs_score=EXCLUDED.dqs_score,quality_level=EXCLUDED.quality_level,
              coverage_score=EXCLUDED.coverage_score,recency_score=EXCLUDED.recency_score,
              consistency_score=EXCLUDED.consistency_score,
              calculated_at=EXCLUDED.calculated_at,details=EXCLUDED.details
        """), {"cod": row["cod_ine"], "year": row["anio"], "version": VERSION,
                  "score": q["score"], "level": q["level"], "coverage": q["coverage"],
                  "recency": q["recency"], "at": q["calculated_at"],
                  "details": json.dumps({k: q[k] for k in ("components", "issues", "scope")}, allow_nan=False)})
