"""Auditar primero, estimar después. No reparar ni imputar silenciosamente."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
from esda import Moran, Moran_Local
from libpysal.weights import Queen, Rook, KNN, W, lag_spatial
from pyproj import Geod
from scipy.stats import false_discovery_control
from shapely import equals

VERSION = "spatial-ipr-1.0.0"
CLUSTERS = ("HH", "LL", "HL", "LH", "NS")
QUADRANTS = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}
SCORE = "ipr4_nacional_observado"
# Margen relativo con el que un estadístico simulado cuenta como empate del
# observado. Absorbe el último bit; cualquier diferencia real es muchos
# órdenes de magnitud mayor.
TIE_TOLERANCE = 1e-9


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def audit(geometry: gpd.GeoDataFrame, ipr: pd.DataFrame) -> dict:
    required = {"cod_ine", "anio", SCORE, "version_metodologia", "metodo"}
    if not required <= set(ipr):
        raise ValueError(f"Faltan columnas IPR: {sorted(required - set(ipr))}")
    if "cod_ine" not in geometry:
        raise ValueError("Las geometrías no tienen código INE")
    geo_ids = set(geometry.cod_ine.dropna().astype(str))
    ipr_ids = set(ipr.cod_ine.dropna().astype(str))
    null = geometry.geometry.isna()
    empty = geometry.geometry.is_empty
    invalid = ~geometry.geometry.is_valid & ~null
    # Topological equality also catches reversed rings and redundant vertices.
    duplicates = pd.Series(False, index=geometry.index)
    if not null.any() and not invalid.any():
        left, right = geometry.sindex.query(geometry.geometry, predicate="intersects")
        pairs = left < right
        left, right = left[pairs], right[pairs]
        equal = equals(geometry.geometry.array.take(left), geometry.geometry.array.take(right))
        duplicates.iloc[np.concatenate([left[equal], right[equal]])] = True
    years = pd.to_numeric(ipr.anio, errors="coerce")
    values = pd.to_numeric(ipr[SCORE], errors="coerce")
    year_valid = years.notna() & (years % 1 == 0) & years.between(1900, datetime.now().year)
    same_universe = all(set(group.cod_ine) == geo_ids for _, group in ipr.groupby("anio"))
    report = {
        "municipios_ipr": len(ipr_ids), "observaciones_ipr": len(ipr),
        "municipios_con_geometria": int((~null & ~empty).sum()),
        "geometrias_validas": int((~null & ~empty & ~invalid).sum()),
        "geometrias_nulas": int(null.sum()), "geometrias_vacias": int(empty.sum()),
        "geometrias_invalidas": geometry.loc[invalid, "cod_ine"].tolist(),
        "geometrias_duplicadas": geometry.loc[duplicates, "cod_ine"].tolist(),
        "ids_geometria_duplicados": geometry.loc[geometry.cod_ine.duplicated(False), "cod_ine"].tolist(),
        "ids_ipr_duplicados": ipr.loc[ipr.duplicated(["cod_ine", "anio"], False), "cod_ine"].tolist(),
        "crs": str(geometry.crs), "srid": geometry.crs.to_epsg() if geometry.crs else None,
        "geometria_sin_ipr": sorted(geo_ids - ipr_ids), "ipr_sin_geometria": sorted(ipr_ids - geo_ids),
        "municipios_sin_match": len(geo_ids ^ ipr_ids),
        "codigo_identificador": "cod_ine (INE, cinco dígitos)",
        "codigos_validos": bool(geometry.cod_ine.astype("string").str.fullmatch(r"\d{5}").fillna(False).all()
                                and ipr.cod_ine.astype("string").str.fullmatch(r"\d{5}").fillna(False).all()),
        "anios_validos": bool(year_valid.all()),
        "ipr_valido": bool((np.isfinite(values) & values.between(0, 100)).all()),
        "universo_estable": same_universe,
        "metodologia_comparable": bool(ipr.version_metodologia.notna().all()
            and ipr.metodo.notna().all() and ipr.version_metodologia.nunique() == 1
            and ipr.metodo.nunique() == 1),
        "poligonos": bool(geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all()),
    }
    report["passed"] = bool(
        len(geometry) >= 4 and len(ipr) > 0 and geometry.crs
        and not null.any() and not empty.any() and not invalid.any() and not duplicates.any()
        and not report["ids_geometria_duplicados"] and not report["ids_ipr_duplicados"]
        and report["municipios_sin_match"] == 0
        and all(report[key] for key in ["codigos_validos", "anios_validos", "ipr_valido",
            "universo_estable", "metodologia_comparable", "poligonos"])
    )
    return report


def build_weights(geometry: gpd.GeoDataFrame, method="queen") -> W:
    frame = geometry.sort_values("cod_ine").reset_index(drop=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        raw = {"queen": Queen, "rook": Rook}[method].from_dataframe(frame, ids=frame.cod_ine.tolist())
    # Canonical ID and neighbor ordering is also the order supplied to ESDA.
    weights = W({code: sorted(raw.neighbors[code]) for code in frame.cod_ine},
                id_order=frame.cod_ine.tolist(), silence_warnings=True)
    weights.transform = "r"
    return weights


def weights_summary(weights: W) -> dict:
    degrees = list(weights.cardinalities.values())
    edges = [(code, other) for code in weights.id_order for other in weights.neighbors[code]]
    return {"normalization": "row-standardized", "neighbor_min": min(degrees),
            "neighbor_max": max(degrees), "neighbor_mean": float(np.mean(degrees)),
            "islands": weights.islands, "components": weights.n_components,
            "directed_edges": len(edges),
            "sha256": hashlib.sha256(json.dumps(edges).encode()).hexdigest()}


def evaluate_islands(geometry: gpd.GeoDataFrame, weights: W) -> list[dict]:
    """Diagnostic KNN only: nearest representative point on WGS84 sphere."""
    frame = geometry.to_crs(4326).set_index("cod_ine").loc[weights.id_order]
    points = frame.geometry.representative_point()
    coordinates = np.column_stack([points.x, points.y])
    knn = KNN(coordinates, k=1, ids=weights.id_order, radius=6371.0088, silence_warnings=True)
    geod = Geod(ellps="WGS84")
    result = []
    for code in weights.islands:
        other = knn.neighbors[code][0]
        start, end = points.loc[code], points.loc[other]
        distance = geod.inv(start.x, start.y, end.x, end.y)[2] / 1000
        result.append({"cod_ine": code, "nombre": frame.loc[code, "nombre"],
                       "nearest_cod_ine": other, "distance_km": distance,
                       "applied": False, "method_evaluated": "KNN k=1, arc, representative points"})
    return result


def permutation_p(simulated: np.ndarray, observed, permutations: int) -> np.ndarray:
    """P-valor bilateral de permutaciones con las dos colas inclusivas.

    Cuando una permutación reproduce la configuración observada el estadístico
    simulado es, matemáticamente, el observado. Los dos los calculan rutinas
    distintas (el núcleo compilado de `esda` y la ruta directa de NumPy), así
    que solo coinciden hasta el último bit y la comparación exacta cuenta el
    empate o no según la máquina: con un vecino, ese municipio acumula hasta
    trece empates de 999 tiradas y el p-valor se mueve hasta 0,026 entre
    arquitecturas. La tolerancia relativa mete el empate en ambas colas
    siempre, que es lo que la cola inclusiva declara hacer.
    """
    tolerance = np.maximum(np.abs(observed), 1.0) * TIE_TOLERANCE
    upper = (np.sum(simulated >= observed - tolerance, axis=0) + 1) / (permutations + 1)
    lower = (np.sum(simulated <= observed + tolerance, axis=0) + 1) / (permutations + 1)
    return np.minimum(1.0, 2 * np.minimum(upper, lower))


def estimate(ipr: pd.DataFrame, weights: W, year: int, permutations=999, seed=2023, alpha=0.05) -> dict:
    if permutations < 99 or not 0 < alpha < 1 or not 0 <= seed < 2**32:
        raise ValueError("Permutaciones >= 99, 0 < alpha < 1 y seed uint32 requeridos")
    frame = ipr.set_index("cod_ine").loc[weights.id_order]
    ids = [code for code in weights.id_order if code not in weights.islands]
    if len(ids) < 4:
        raise ValueError("Menos de cuatro municipios con vecinos; no es posible estimar")
    w = W({code: weights.neighbors[code] for code in ids}, id_order=ids, silence_warnings=True)
    w.transform = "r"
    values = frame.loc[ids, SCORE].to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.std(values) == 0:
        raise ValueError("El IPR es constante o no finito; Moran no está definido")
    # ESDA Moran uses NumPy's global RNG; restore it for callers.
    state = np.random.get_state()
    try:
        np.random.seed(seed)
        global_moran = Moran(values, w, permutations=permutations)
    finally:
        np.random.set_state(state)
    with warnings.catch_warnings():
        # We derive explicit inclusive two-sided p-values from sim below, never p_sim.
        warnings.filterwarnings("ignore", message="The alternative hypothesis for conditional randomization", category=DeprecationWarning)
        local = Moran_Local(values, w, permutations=permutations, seed=seed,
                            n_jobs=1, keep_simulations=True, geoda_quads=False)
    # Explicit two-sided randomization tests, inclusive tails with +1 correction.
    # Moran.two_tailed only changes analytical p-values; p_sim is NOT two-sided.
    global_p = float(permutation_p(global_moran.sim, global_moran.I, permutations))
    local_p = permutation_p(local.sim, local.Is, permutations)
    adjusted = false_discovery_control(local_p, method="bh")
    z = (values - values.mean()) / values.std()
    lag = lag_spatial(w, z)
    raw_lag = lag_spatial(w, values)
    # Correct Rayleigh bounds for centered, possibly asymmetric row weights.
    matrix = w.sparse.toarray()
    center = np.eye(len(ids)) - np.ones((len(ids), len(ids))) / len(ids)
    eigenvalues = np.linalg.eigvalsh(center @ ((matrix + matrix.T) / 2) @ center)
    bounds = [float(eigenvalues.min()), float(eigenvalues.max())]
    if not bounds[0] - 1e-10 <= global_moran.I <= bounds[1] + 1e-10:
        raise ValueError("Moran fuera de los límites espectrales de W")
    if not np.isfinite(global_moran.z_sim) or not np.isfinite(local.Is).all():
        raise ValueError("Distribución de permutaciones degenerada")
    significant = bool(global_p <= alpha)
    interpretation = ("agrupación espacial significativa" if global_moran.I > global_moran.EI
                      else "dispersión espacial significativa") if significant else "sin evidencia significativa de autocorrelación"
    positions = {code: i for i, code in enumerate(ids)}
    rows = []
    for code in weights.id_order:
        index = positions.get(code)
        tested = index is not None
        quadrant = QUADRANTS[int(local.q[index])] if tested else None
        # Points exactly on an axis do not belong to a high/low quadrant.
        if tested and (z[index] == 0 or lag[index] == 0):
            quadrant = None
        sig_raw = bool(tested and quadrant and local_p[index] <= alpha)
        sig_fdr = bool(tested and quadrant and adjusted[index] <= alpha)
        rows.append({"cod_ine": code, "anio": int(year), "ipr": float(frame.loc[code, SCORE]),
            "dqs": None, "dqs_level": None,
            "local_moran_i": float(local.Is[index]) if tested else None,
            "p_value": float(local_p[index]) if tested else None,
            "p_value_fdr": float(adjusted[index]) if tested else None,
            "quadrant": quadrant, "cluster_type": quadrant if sig_fdr else "NS",
            "cluster_type_raw": quadrant if sig_raw else "NS",
            "is_significant": sig_fdr, "is_significant_raw": sig_raw,
            "eligible": tested, "exclusion_reason": None if tested else "sin_vecinos_queen",
            "neighbor_count": len(weights.neighbors[code]),
            "neighbors": weights.neighbors[code],
            "standardized_ipr": float(z[index]) if tested else None,
            "spatial_lag": float(lag[index]) if tested else None,
            "spatial_lag_ipr": float(raw_lag[index]) if tested else None})
    summary = [{"cluster_type": kind,
                "count": sum(row["cluster_type"] == kind for row in rows),
                "raw_count": sum(row["cluster_type_raw"] == kind for row in rows),
                "percentage": 100 * sum(row["cluster_type"] == kind for row in rows) / len(rows)}
               for kind in CLUSTERS]
    return {"anio": int(year), "moran_i": float(global_moran.I), "expected_i": float(global_moran.EI),
            "p_value": float(global_p), "z_score": float(global_moran.z_sim),
            "permutations": permutations, "seed": seed, "alpha": alpha,
            "n_municipalities": len(rows), "n_observations": len(ids),
            "n_islands": len(weights.islands), "weights_method": "queen",
            "calculation_version": VERSION, "is_significant": significant,
            "interpretation": interpretation, "spectral_bounds": bounds,
            "main_correction": "fdr_bh", "summary": summary, "items": rows}


def run(geometry_path: Path, ipr_path: Path, destination: Path, permutations=999, seed=2023) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    geometry = gpd.read_file(geometry_path).sort_values("cod_ine").reset_index(drop=True)
    ipr = pd.read_csv(ipr_path, dtype={"cod_ine": str, "version_metodologia": str})
    report = audit(geometry, ipr)
    write_json(destination / "spatial_audit.json", report)
    if not report["passed"]:
        raise ValueError("Auditoría espacial fallida; consulte spatial_audit.json. No se ha calculado Moran/LISA")
    queen, rook = build_weights(geometry), build_weights(geometry, "rook")
    report.update({"queen": weights_summary(queen), "rook": weights_summary(rook),
                   "municipios_sin_vecinos": len(queen.islands),
                   "island_diagnostics": evaluate_islands(geometry, queen)})
    write_json(destination / "spatial_audit.json", report)
    results = [estimate(group, queen, int(year), permutations, seed)
               for year, group in ipr.groupby("anio", sort=True)]
    metadata = {"calculation_version": VERSION,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
        "sources": {"geometry": {"file": geometry_path.name, "sha256": file_hash(geometry_path)},
                    "ipr": {"file": ipr_path.name, "sha256": file_hash(ipr_path)}},
        "libraries": {name: version(name) for name in ["esda", "libpysal", "numpy", "pandas",
            "scipy", "geopandas", "shapely", "numba", "scikit-learn", "pyproj", "pyogrio"]},
        "python": platform.python_version(), "normalization": "row-standardized",
        "island_policy": "exclude_from_inference_keep_in_dataset",
        "p_value_method": "two-sided doubled minimum inclusive permutation tail; "
                          f"+1 correction; relative tie tolerance {TIE_TOLERANCE:g}",
        "z_score_method": "permutation mean and standard deviation (z_sim)",
        "fdr_family": "all municipalities with Queen neighbors, separately per year",
        "main_correction": "fdr_bh", "dqs_available": False,
        "history_comparable": len(results) > 1, "weights_sha256": weights_summary(queen)["sha256"]}
    payload = {"metadata": metadata, "audit": report, "years": results}
    write_json(destination / "spatial_ipr.json", payload)
    pd.DataFrame([{**{k: v for k, v in result.items() if k not in {"items", "summary", "spectral_bounds"}},
                   "calculated_at": metadata["calculated_at"]}
                  for result in results]).to_csv(destination / "spatial_global.csv", index=False)
    local = pd.DataFrame([row for result in results for row in result["items"]])
    local["calculation_version"] = VERSION
    local["calculated_at"] = metadata["calculated_at"]
    local.to_csv(destination / "spatial_lisa.csv", index=False)
    transitions = []
    for before, after in zip(results, results[1:]):
        previous = {row["cod_ine"]: row for row in before["items"]}
        for row in after["items"]:
            transitions.append({"cod_ine": row["cod_ine"], "from_year": before["anio"],
                "to_year": after["anio"], "from_cluster": previous[row["cod_ine"]]["cluster_type"],
                "to_cluster": row["cluster_type"], "eligible": row["eligible"]})
    pd.DataFrame(transitions, columns=["cod_ine", "from_year", "to_year", "from_cluster",
                                      "to_cluster", "eligible"]).to_csv(destination / "spatial_transitions.csv", index=False)
    return payload
