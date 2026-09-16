#!/usr/bin/env python3
"""Contraste externo del IPR congelado. No reconstruye ni modifica sus capas."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
import requests
from scipy import stats

ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config/validacion_externa.json"
RAW = ROOT / "data/raw/validacion_externa/VDP001_01.csv.gz"
IPR = ROOT / "data/processed/indice_presion_residencial_2023.csv"
OUT = ROOT / "data/processed/validacion_externa"
PUBLIC = ROOT / "apps/web/public/validacion-externa"
MANIFEST = ROOT / "data/processed/validacion_externa/manifest.json"
Y = "alquiler_mediano_mensual"
X = "ipr4_nacional_observado"
X5 = "ipr5_prospectivo"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    temporary.replace(path)


def source(config: dict, refresh: bool) -> dict:
    metadata_path = RAW.with_suffix(".metadata.json")
    if refresh or not RAW.exists():
        response = requests.get(config["url"], timeout=180)
        response.raise_for_status()
        content = response.content
        if not content.decode("utf-8-sig").startswith("COD_PROVINCIA;"):
            raise ValueError("La descarga no contiene el esquema CSV esperado")
        RAW.parent.mkdir(parents=True, exist_ok=True)
        temporary = RAW.with_suffix(".part")
        temporary.write_bytes(gzip.compress(content, mtime=0))
        temporary.replace(RAW)
        write_json(metadata_path, {
            "source_url": config["url"], "downloaded_at": now(),
            "download_sha256": hashlib.sha256(content).hexdigest(),
            "archive_sha256": sha(RAW),
            # Mismos campos que el resto de descargas, para que el anexo de
            # fuentes pueda leer todas las fuentes de la misma manera.
            "organism": "Ministerio de Vivienda y Agenda Urbana",
            "resource": config["indicador"],
            "statistical_period": str(config["periodo_externo"]),
            "license_url": "https://www.mivau.gob.es/el-ministerio/aviso-legal",
        })
    metadata = json.loads(metadata_path.read_text())
    if (metadata["source_url"] != config["url"] or
            metadata["archive_sha256"] != sha(RAW) or
            metadata["download_sha256"] != hashlib.sha256(gzip.decompress(RAW.read_bytes())).hexdigest()):
        raise ValueError("La copia de la fuente no coincide con su trazabilidad")
    return metadata


def codes(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip()
    if not values.str.fullmatch(r"\d{1,5}").fillna(False).all():
        raise ValueError("Identificador municipal inválido")
    return values.str.zfill(5)


def load_ipr(path: Path, config: dict) -> pd.DataFrame:
    frame = pd.read_csv(path, dtype={"cod_ine": str})
    frame = frame[["cod_ine", "nombre", "anio", X, X5]].copy()
    frame["cod_ine"] = codes(frame.cod_ine)
    if frame.cod_ine.duplicated().any() or len(frame) != config["universo"]:
        raise ValueError("Universo del IPR inesperado o duplicado")
    if not frame.anio.eq(config["periodo_ipr"]).all():
        raise ValueError("Periodo del IPR incompatible con el protocolo")
    for column in [X, X5]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
        if not frame[column].dropna().between(0, 100).all():
            raise ValueError("IPR fuera de rango")
    if frame[X].isna().any():
        raise ValueError("El protocolo exige universo IPR-4 completo")
    return frame.sort_values("cod_ine").reset_index(drop=True)


def process_external(raw: pd.DataFrame, universe: pd.DataFrame, config: dict) -> pd.DataFrame:
    required = {"COD_PROVINCIA", "COD_POSTAL", "NOMBRE_MUNICIPIO", "AÑO", "VALOR", *config["filtros"]}
    if not required.issubset(raw.columns):
        raise ValueError(f"Faltan columnas: {sorted(required - set(raw.columns))}")
    mask = pd.Series(True, index=raw.index)
    for key, value in config["filtros"].items():
        mask &= raw[key].eq(value)
    selected = raw.loc[mask].copy()
    selected["anio_externo"] = pd.to_numeric(selected["AÑO"], errors="raise")
    years = [config["periodo_externo"], *config["robustez_temporal"]]
    selected = selected[selected.anio_externo.isin(years)].copy()
    selected["cod_ine"] = codes(selected.COD_POSTAL)
    province = selected.COD_PROVINCIA.astype("string").str.zfill(2)
    if not selected.cod_ine.str[:2].eq(province).all():
        raise ValueError("El código municipal no concuerda con la provincia")
    if selected.duplicated(["cod_ine", "anio_externo"]).any():
        raise ValueError("Duplicados municipio-periodo en fuente externa")
    value = selected.VALOR.astype("string").str.strip().replace({"": pd.NA, "..": pd.NA, "...": pd.NA, ":": pd.NA, "-": pd.NA})
    # El CSV usa punto decimal. No eliminar puntos como si fueran miles.
    selected[Y] = pd.to_numeric(value.str.replace(",", ".", regex=False), errors="raise")
    observed = selected[Y].dropna()
    if not (np.isfinite(observed).all() and observed.gt(0).all()):
        raise ValueError("Cuantía de alquiler no positiva o no finita")
    selected["presente_fuente"] = True
    grid = pd.MultiIndex.from_product([universe.cod_ine, years], names=["cod_ine", "anio_externo"]).to_frame(index=False)
    external = grid.merge(
        selected[["cod_ine", "anio_externo", Y, "presente_fuente"]],
        on=["cod_ine", "anio_externo"], how="left", validate="one_to_one",
    )
    external["estado"] = np.where(external[Y].notna(), "observado", np.where(external.presente_fuente.eq(True), "valor_ausente", "sin_registro"))
    external["unidad"] = config["unidad"]
    external["uso"] = "external_validation"
    return external.drop(columns="presente_fuente").sort_values(["anio_externo", "cod_ine"])


def quartiles(values: pd.Series) -> pd.Series:
    boundaries = values.quantile([0, .25, .5, .75, 1]).to_numpy()
    if len(np.unique(boundaries)) != 5:
        return pd.Series(pd.NA, index=values.index, dtype="string")
    return pd.cut(values, bins=boundaries, labels=["Q1", "Q2", "Q3", "Q4"], include_lowest=True).astype("string")


def correlation(frame: pd.DataFrame, x: str, name: str, year: int, config: dict) -> dict:
    sample = frame.dropna(subset=[x, Y])
    n = len(sample)
    result = {"analisis": name, "producto": x, "periodo_ipr": config["periodo_ipr"], "periodo_externo": year,
              "n": n, "universo": config["universo"], "cobertura": n / config["universo"],
              "rho": None, "p_value": None, "p_asintotico": None,
              "metodo_p": "permutación bilateral de rangos; corrección +1", "estado": "no_estimable"}
    if n < 3 or sample[x].nunique() < 2 or sample[Y].nunique() < 2:
        return result
    a, b = stats.rankdata(sample[x]), stats.rankdata(sample[Y])
    a, b = a - a.mean(), b - b.mean()
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    rho = float(np.dot(a, b) / denominator)
    rng = np.random.default_rng(config["semilla"])
    # Reordenar una sola variable mantiene sus valores y empates intactos.
    extreme = sum(abs(float(np.dot(a, rng.permutation(b)) / denominator)) >= abs(rho) - 1e-14
                  for _ in range(config["permutaciones"]))
    result.update(rho=rho, p_value=(extreme + 1) / (config["permutaciones"] + 1),
                  p_asintotico=float(stats.spearmanr(sample[x], sample[Y]).pvalue), estado="estimado")
    return result


def analyze(universe: pd.DataFrame, external: pd.DataFrame, config: dict) -> tuple[dict, pd.DataFrame]:
    universe = universe.copy()
    universe["cuartil_ipr"] = quartiles(universe[X])
    year = config["periodo_externo"]
    paired = universe.merge(external[external.anio_externo.eq(year)], on="cod_ine", how="left", validate="one_to_one")
    sample = paired.dropna(subset=[X, Y])
    if len(sample) / len(universe) < config["cobertura_minima"]:
        raise ValueError("Regla de parada: cobertura externa inferior al 90%; no se genera validación")
    results = [correlation(sample, X, "principal", year, config)]
    keep = pd.Series(True, index=sample.index)
    for column in [X, Y]:
        low, high = sample[column].quantile(config["extremos"])
        keep &= sample[column].between(low, high)
    results.append(correlation(sample[keep], X, "sin_extremos_p01_p99", year, config))
    complete5 = sample.dropna(subset=[X5])
    results.append(correlation(complete5, X5, "ipr5_exploratorio", year, config))
    results.append(correlation(complete5, X, "ipr4_misma_muestra_ipr5", year, config))
    panel = external.pivot(index="cod_ine", columns="anio_externo", values=Y).dropna()
    for temporal_year in [year, *config["robustez_temporal"]]:
        temporal = universe.merge(panel[[temporal_year]].rename(columns={temporal_year: Y}), on="cod_ine", validate="one_to_one")
        results.append(correlation(temporal, X, "sensibilidad_temporal_muestra_comun", temporal_year, config))
    groups = []
    arrays = []
    for label, group in sample.dropna(subset=["cuartil_ipr"]).groupby("cuartil_ipr", sort=True):
        s = group[Y]
        groups.append({"cuartil": str(label), "n": len(s), "mediana": float(s.median()), "p25": float(s.quantile(.25)), "p75": float(s.quantile(.75))})
        arrays.append(s.to_numpy())
    kruskal = {"h": None, "p_value": None, "estado": "no_estimable"}
    if len(arrays) == 4 and all(len(a) >= 5 for a in arrays) and sample[Y].nunique() > 1:
        h, p = stats.kruskal(*arrays)
        kruskal = {"h": float(h), "p_value": float(p), "estado": "estimado_exploratorio"}
    distributions = []
    for label, s in [("ipr_universo", universe[X]), ("ipr_pareado", sample[X]), (Y, sample[Y])]:
        q1, q3 = s.quantile([.25, .75])
        distributions.append({"variable": label, "n": len(s), "media": float(s.mean()), "desviacion": float(s.std()),
                              "min": float(s.min()), "p25": float(q1), "mediana": float(s.median()), "p75": float(q3),
                              "max": float(s.max()), "outliers_1_5_iqr": int((~s.between(q1 - 1.5*(q3-q1), q3 + 1.5*(q3-q1))).sum())})
    principal = results[0]
    if principal["rho"] is None:
        interpretation = "No se puede estimar la asociación con estos datos."
    elif principal["p_value"] >= config["alpha"]:
        interpretation = "No se obtiene evidencia estadística suficiente de asociación. No se rechaza H0; esto no demuestra ausencia de relación."
    elif principal["rho"] > 0:
        interpretation = "Se observa una asociación positiva consistente con la hipótesis de mayores costes de alquiler en municipios con mayor IPR."
    else:
        interpretation = "La asociación observada es negativa y contradice la dirección esperada. Se conserva este resultado."
    coverage = [{"anio": int(y), "observados": int(g[Y].notna().sum()), "ausentes": int(g[Y].isna().sum()), "universo": len(universe)}
                for y, g in external.groupby("anio_externo")]
    return {"protocolo": config, "correlaciones": results, "grupos": groups, "kruskal_wallis": kruskal,
            "distribuciones": distributions, "cobertura_por_anio": coverage,
            "ausentes": paired.loc[paired[Y].isna(), ["cod_ine", "nombre", "estado"]].to_dict("records"),
            "excluidos_extremos": sample.loc[~keep, "cod_ine"].tolist(), "interpretacion": interpretation,
            "pearson": "No calculado: se contrasta relación monótona sin asumir linealidad ni normalidad.",
            "limitaciones": "Correlación no implica causalidad ni capacidad predictiva. El alquiler declarado no mide esfuerzo, contratos nuevos o desplazamiento. La superficie, composición del parque, ingresos y localización pueden explicar asociaciones. Cobertura incompleta y no aleatoria; no extrapolar a toda España. Los p-values suponen independencia municipal y pueden ser optimistas por dependencia territorial. IPR-5 incorpora proyecciones, por lo que su contraste contemporáneo no valida su horizonte futuro."}, paired


def render(result: dict, paired: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    sample = paired.dropna(subset=[X, Y])
    main = result["correlaciones"][0]
    plt.rcParams.update({"font.size": 11, "svg.hashsalt": "tfm-external-v1"})
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    ax.scatter(sample[X], sample[Y], s=22, alpha=.65, color="#147d80", edgecolor="none")
    rho_label = f"{main['rho']:.3f}" if main['rho'] is not None else "no estimable"
    ax.set(xlabel="IPR-4 observado · 2023 (0–100)", ylabel="Alquiler mediano de vivienda colectiva (€/mes)",
           title=f"Validación externa · 2023 · N={main['n']} · Spearman ρ={rho_label}")
    ax.grid(alpha=.15)
    fig.savefig(PUBLIC / "dispersion.svg", metadata={"Date": None})
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5), layout="constrained")
    groups = result["grupos"]
    if groups:
        ax.boxplot([sample.loc[sample.cuartil_ipr.eq(g['cuartil']), Y] for g in groups],
                   tick_labels=[f"{g['cuartil']}\nN={g['n']}" for g in groups], showfliers=True)
    else:
        ax.text(.5, .5, "Cuartiles no estimables: límites coincidentes", ha="center", transform=ax.transAxes)
    ax.set(xlabel="Cuartiles del IPR-4 del universo de 306 municipios", ylabel="Alquiler mediano de vivienda colectiva (€/mes)",
           title="Distribución del alquiler por nivel de IPR · 2023")
    ax.grid(axis="y", alpha=.15)
    fig.savefig(PUBLIC / "cuartiles.svg", metadata={"Date": None})
    plt.close(fig)


def markdown_table(records: list[dict]) -> str:
    if not records:
        return "No estimable.\n"
    headers = list(records[0])
    def cell(v):
        return "—" if v is None else (f"{v:.6g}" if isinstance(v, float) else str(v))
    return "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"]*len(headers)) + " |\n" + "\n".join("| " + " | ".join(cell(r[h]) for h in headers) + " |" for r in records) + "\n"


def report(result: dict) -> str:
    c = result["protocolo"]
    return f"""# Validación externa del IPR: resultados

Informe generado por `24_validacion_externa_ipr.py`. Protocolo y candidatos:
[evaluación previa](CANDIDATOS_VALIDACION_EXTERNA.md).

Indicador: **{c['indicador']}**, {c['unidad']}. Fuente:
[MIVAU SERPAVI]({c['url']}). Corte principal: {c['periodo_externo']}.
Descarga: {result['fuente']['downloaded_at']}. Hash y linaje: `data/processed/validacion_externa/manifest.json`.

{result['interpretacion']} Esto aporta un contraste convergente limitado al coste
del alquiler; no certifica que el IPR sea correcto ni que todas sus dimensiones
estén validadas. No se ajustaron sus pesos o componentes.

## Hipótesis fijada antes del cálculo

H1: {c['h1']} H0: {c['h0']}
Prueba bilateral, alfa {c['alpha']}. Spearman con {c['permutaciones']} permutaciones,
semilla {c['semilla']}; p mínimo posible {1/(c['permutaciones']+1):.6g}.
La dirección positiva se evalúa junto con el p bilateral, sin cambiar de prueba.

## Cobertura y ausencias

{markdown_table(result['cobertura_por_anio'])}
Ausentes en 2023 (sin imputación; no se codifican como cero):

{markdown_table(result['ausentes'])}
## Correlaciones y robustez

Solo `principal` es el contraste principal. Los demás son exploratorios;
no se selecciona el mayor coeficiente ni se interpretan sus p-values como
confirmaciones independientes. Cobertura = N/306 en todas las filas.

{markdown_table(result['correlaciones'])}
Sin extremos: se retiraron {len(result['excluidos_extremos'])} observaciones,
fuera de P1–P99 de alguna variable: {', '.join(result['excluidos_extremos'])}.
La sensibilidad temporal mantiene IPR 2023 y restringe a municipios con alquiler
en los tres años; no es una serie histórica del IPR ni predicción causal.
{result['pearson']}

## Exploración de distribuciones

{markdown_table(result['distribuciones'])}
Los outliers descriptivos usan 1,5 × IQR; son distintos del recorte de robustez
P1–P99. Se conservan todos en el análisis principal. No se aplica transformación
al alquiler ni se calcula esfuerzo dividiendo por renta del propio IPR.

![Dispersión: IPR y alquiler](../apps/web/public/validacion-externa/dispersion.svg)

## Grupos de presión

{markdown_table(result['grupos'])}
Kruskal–Wallis global, exploratorio:

{markdown_table([result['kruskal_wallis']])}
Los límites proceden del IPR de los 306 municipios; los empates permanecen
juntos. El contraste global no identifica por sí solo diferencias Q1–Q4.

![Alquiler por cuartil del IPR](../apps/web/public/validacion-externa/cuartiles.svg)

## Limitaciones e interpretación

{result['limitaciones']}

Un resultado débil, negativo o no significativo se publica con la misma regla.
Puede deberse a diferencias conceptuales, periodo, cobertura, heterogeneidad
territorial o limitaciones del propio índice. No se modifica la fórmula como
respuesta al contraste.

## Reproducción

Desde la raíz: `python 24_validacion_externa_ipr.py` usa la descarga archivada y
verifica su SHA-256. `--refresh` descarga la versión vigente y registra nueva
fecha y hashes; los resultados pueden cambiar por revisiones de la fuente.
Las copias de datos externos y los pares analíticos se guardan en
`data/processed/validacion_externa/`, separados de la construcción.
El dashboard usa la instantánea del mismo análisis, generada en
`apps/web/public/validacion-externa/`; requiere reconstrucción del frontend
para actualizar la página. El manifest conserva ejecuciones y hashes de código,
protocolo, IPR, fuente y salidas. No incorpora retroactivamente el resto de P1.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Descargar una nueva versión oficial")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    metadata = source(config, args.refresh)
    universe = load_ipr(IPR, config)
    raw = pd.read_csv(RAW, sep=";", encoding="utf-8-sig", dtype=str)
    external = process_external(raw, universe, config)
    result, paired = analyze(universe, external, config)
    result["fuente"] = metadata
    OUT.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    external.to_csv(OUT / "alquiler_municipal.csv", index=False)
    paired.to_csv(OUT / "pares_ipr_alquiler_2023.csv", index=False)
    pd.DataFrame(result["correlaciones"]).to_csv(OUT / "correlaciones.csv", index=False)
    pd.DataFrame(result["grupos"]).to_csv(OUT / "cuartiles.csv", index=False)
    write_json(OUT / "resultados.json", result)
    write_json(PUBLIC / "resultados.json", result)
    paired.to_csv(PUBLIC / "pares_ipr_alquiler_2023.csv", index=False)
    render(result, paired)
    report_path = ROOT / "docs/RESULTADOS_VALIDACION_EXTERNA.md"
    report_path.write_text(report(result))
    inputs = [IPR, RAW, RAW.with_suffix(".metadata.json"), CONFIG, Path(__file__),
              ROOT / "docs/AUDITORIA_IPR_VALIDACION_EXTERNA.md", ROOT / "docs/CANDIDATOS_VALIDACION_EXTERNA.md"]
    outputs = sorted(OUT.glob("*")) + sorted(PUBLIC.glob("*")) + [report_path]
    def files(paths):
        return [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in paths if p.is_file()]
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"schema_version": "1.0", "runs": []}
    manifest["runs"].append({"pipeline": "external_validation_ipr", "generated_at": now(), "usage": "external_validation",
                             "code_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                             "working_tree_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()),
                             "source": metadata, "statistical_period": config["periodo_externo"],
                             "inputs": files(inputs), "outputs": files(outputs),
                             "packages": {p: importlib.metadata.version(p) for p in ["numpy", "pandas", "scipy", "matplotlib", "requests"]}})
    write_json(MANIFEST, manifest)
    print(json.dumps(result["correlaciones"][0], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
