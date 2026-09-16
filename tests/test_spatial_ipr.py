"""Validación estadística con geometrías sintéticas y el universo real."""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box, Polygon

from spatial_ipr.analysis import audit, build_weights, estimate, permutation_p, run, SCORE

ROOT = Path(__file__).resolve().parents[1]


def fixture_frames():
    geometry = gpd.GeoDataFrame({"cod_ine": [f"{i:05}" for i in range(16)],
        "nombre": [f"M{i}" for i in range(16)]},
        geometry=[box(i % 4, i // 4, i % 4 + 1, i // 4 + 1) for i in range(16)], crs=4326)
    ipr = pd.DataFrame({"cod_ine": geometry.cod_ine, "anio": 2023,
        SCORE: [10.0 + (i // 4) * 20 + i % 4 for i in range(16)],
        "version_metodologia": "test", "metodo": "fixed"})
    return geometry, ipr


def test_real_audit_and_permutation_reproduction():
    geometry = gpd.read_file(ROOT / "data/raw/municipios_306_con_geometria.gpkg")
    ipr = pd.read_csv(ROOT / "data/processed/indice_presion_residencial_2023.csv", dtype={"cod_ine": str})
    report = audit(geometry, ipr)
    assert report["passed"] and report["geometrias_validas"] == 306
    assert report["municipios_sin_match"] == 0
    weights = build_weights(geometry)
    assert len(weights.islands) == 86
    assert weights.neighbors == build_weights(geometry.sample(frac=1, random_state=8)).neighbors
    result = estimate(ipr.sample(frac=1, random_state=5), weights, 2023)
    saved = json.loads((ROOT / "data/processed/spatial/spatial_ipr.json").read_text())["years"][0]
    assert result["moran_i"] == pytest.approx(saved["moran_i"], abs=1e-12)
    assert result["p_value"] == saved["p_value"]
    assert result["n_observations"] == 220
    for actual, expected in zip(result["items"], saved["items"]):
        assert actual["cod_ine"] == expected["cod_ine"]
        assert actual["cluster_type"] == expected["cluster_type"]
        assert actual["p_value"] == expected["p_value"]
        assert actual["p_value_fdr"] == expected["p_value_fdr"]
    lower, upper = result["spectral_bounds"]
    assert lower <= result["moran_i"] <= upper
    assert sum(row["count"] for row in result["summary"]) == 306
    assert sum(row["percentage"] for row in result["summary"]) == pytest.approx(100)


@pytest.mark.parametrize("problem", ["null", "invalid", "duplicate_geometry", "duplicate_id", "unmatched", "missing_year", "bad_code", "null_code", "bad_score", "bad_year", "crs", "method"])
def test_audit_blocks_inconsistent_inputs(problem):
    geometry, ipr = fixture_frames()
    if problem == "null": geometry.loc[0, "geometry"] = None
    if problem == "invalid": geometry.loc[0, "geometry"] = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])
    if problem == "duplicate_geometry": geometry.loc[0, "geometry"] = geometry.loc[1, "geometry"]
    if problem == "duplicate_id": ipr.loc[0, "cod_ine"] = ipr.loc[1, "cod_ine"]
    if problem == "unmatched": ipr.loc[0, "cod_ine"] = "99999"
    if problem == "missing_year": ipr = pd.concat([ipr, ipr.iloc[1:].assign(anio=2022)])
    if problem == "bad_code": ipr.loc[0, "cod_ine"] = "abcde"
    if problem == "null_code": ipr.loc[0, "cod_ine"] = None
    if problem == "bad_score": ipr.loc[0, SCORE] = np.inf
    if problem == "bad_year": ipr.loc[0, "anio"] = 9999
    if problem == "crs": geometry = geometry.set_crs(None, allow_override=True)
    if problem == "method": ipr.loc[0, "metodo"] = "incomparable"
    assert not audit(geometry, ipr)["passed"]


def test_failed_audit_persists_report_without_results(tmp_path):
    geometry, ipr = fixture_frames()
    geometry.to_file(tmp_path / "geometry.gpkg")
    ipr.loc[0, "cod_ine"] = "99999"
    ipr.to_csv(tmp_path / "ipr.csv", index=False)
    with pytest.raises(ValueError, match="Auditoría"):
        run(tmp_path / "geometry.gpkg", tmp_path / "ipr.csv", tmp_path / "results")
    assert not json.loads((tmp_path / "results/spatial_audit.json").read_text())["passed"]
    assert not (tmp_path / "results/spatial_ipr.json").exists()


def test_contiguity_reproducibility_and_significance():
    geometry, ipr = fixture_frames()
    queen, rook = build_weights(geometry), build_weights(geometry, "rook")
    assert queen.neighbors["00000"] == ["00001", "00004", "00005"]
    assert rook.neighbors["00000"] == ["00001", "00004"]
    assert np.allclose(queen.sparse.sum(axis=1), 1)
    a = estimate(ipr, queen, 2023, permutations=199)
    b = estimate(ipr.sample(frac=1, random_state=1), queen, 2023, permutations=199)
    assert a == b
    assert a["moran_i"] > .5 and a["p_value"] <= .05
    for row in a["items"]:
        assert 0 <= row["p_value"] <= row["p_value_fdr"] <= 1
        assert row["cluster_type"] in {"HH", "LL", "HL", "LH", "NS"}
        assert row["is_significant"] == (row["cluster_type"] != "NS")
        assert row["is_significant"] <= row["is_significant_raw"]
        assert row["local_moran_i"] == pytest.approx(15 / 16 * row["standardized_ipr"] * row["spatial_lag"])
    x = np.array([row["standardized_ipr"] for row in a["items"]])
    y = np.array([row["spatial_lag"] for row in a["items"]])
    assert x @ y / (x @ x) == pytest.approx(a["moran_i"])


def test_isolated_municipality_is_preserved_and_not_given_a_p_value():
    geometry, ipr = fixture_frames()
    geometry.loc[15, "geometry"] = box(20, 20, 21, 21)
    result = estimate(ipr, build_weights(geometry), 2023, permutations=99)
    island = next(row for row in result["items"] if row["cod_ine"] == "00015")
    assert result["n_observations"] == 15 and len(result["items"]) == 16
    assert not island["eligible"] and island["cluster_type"] == "NS"
    assert island["p_value"] is None and island["local_moran_i"] is None
    assert island["ipr"] == ipr.iloc[15][SCORE]
    assert island["neighbors"] == []


def test_degenerate_values_and_isolated_universe_are_rejected():
    geometry, ipr = fixture_frames()
    with pytest.raises(ValueError, match="constante"):
        estimate(ipr.assign(**{SCORE: 50}), build_weights(geometry), 2023)
    geometry.geometry = [box(i * 3, 0, i * 3 + 1, 1) for i in range(16)]
    with pytest.raises(ValueError, match="cuatro"):
        estimate(ipr, build_weights(geometry), 2023)


def test_comparable_history_and_transitions(tmp_path):
    geometry, ipr = fixture_frames()
    geometry.to_file(tmp_path / "geometry.gpkg")
    pd.concat([ipr, ipr.assign(anio=2022)]).to_csv(tmp_path / "ipr.csv", index=False)
    payload = run(tmp_path / "geometry.gpkg", tmp_path / "ipr.csv", tmp_path / "results", permutations=99)
    assert payload["metadata"]["history_comparable"]
    assert [row["anio"] for row in payload["years"]] == [2022, 2023]
    transitions = pd.read_csv(tmp_path / "results/spatial_transitions.csv")
    assert len(transitions) == 16
    assert (transitions.from_cluster == transitions.to_cluster).all()


def test_tie_counting_survives_last_bit_noise():
    """Un empate matemático cuenta igual aunque el bit final no coincida.

    El estadístico simulado y el observado los calculan rutinas distintas, así
    que una permutación que reproduce la configuración observada puede devolver
    el vecino de coma flotante en lugar del valor exacto. Con igualdad estricta
    el p-valor cambiaba de máquina; aquí se exige que no se mueva.
    """
    observed = np.array([2.0, -0.5])
    simulated = np.vstack([np.tile(observed, (10, 1)),
                           np.tile(observed - 1.0, (89, 1))])
    exact = permutation_p(simulated, observed, 99)
    assert exact.tolist() == [2 * 11 / 100, 2 * 11 / 100]
    for direccion in (np.inf, -np.inf):
        movido = simulated.copy()
        movido[:10] = np.nextafter(movido[:10], direccion)
        assert permutation_p(movido, observed, 99).tolist() == exact.tolist()
    # Una diferencia real, muy por encima de la tolerancia, sí cuenta.
    lejos = simulated.copy()
    lejos[:10] = observed - 1e-3
    assert permutation_p(lejos, observed, 99)[0] == 2 * 1 / 100
