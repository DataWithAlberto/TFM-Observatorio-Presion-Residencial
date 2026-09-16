import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.observatory import ObservatoryService

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]


def test_spatial_serves_persisted_results_and_no_internal_geometry():
    response = client.get("/api/v1/espacial?anio=2023")
    assert response.status_code == 200
    body = response.json()
    expected = json.loads((ROOT / "data/processed/spatial/spatial_ipr.json").read_text())["years"][0]
    assert body["global_result"]["moran_i"] == expected["moran_i"]
    assert body["global_result"]["p_value"] == expected["p_value"]
    assert body["global_result"]["n_observations"] == 220
    assert len(body["items"]) == 306
    assert len({row["cod_ine"] for row in body["items"]}) == 306
    for row, saved in zip(body["items"], expected["items"]):
        for key in ["cod_ine", "anio", "ipr", "p_value", "p_value_fdr", "cluster_type", "eligible"]:
            assert row[key] == saved[key]
        assert "geometry" not in row and "neighbors" not in row
    assert len([row for row in body["items"] if row["p_value"] is None]) == 86


def test_spatial_history_and_invalid_requests():
    body = client.get("/api/v1/espacial/historico").json()
    assert [row["anio"] for row in body["years"]] == [2023]
    assert not body["history_comparable"] and not body["dqs_available"]
    assert client.get("/api/v1/espacial?anio=2020").status_code == 422
    assert client.get("/api/v1/espacial?anio=0").status_code == 422
    assert client.get("/api/v1/municipios/99999/espacial?anio=2023").status_code == 404
    assert client.get("/api/v1/municipios/28079/espacial?anio=2020").status_code == 422


def test_spatial_neighbors_explain_local_result():
    row = client.get("/api/v1/municipios/29007/espacial?anio=2023").json()
    assert row["cluster_type_raw"] == "HH" and row["cluster_type"] == "NS"
    assert row["neighbor_count"] == len(row["neighbors"]) == 4
    assert sum(n["weight"] for n in row["neighbors"]) == pytest.approx(1)
    assert sum(n["weight"] * n["ipr"] for n in row["neighbors"]) == pytest.approx(row["spatial_lag_ipr"])
    assert row["dqs"] is None
    assert {n["cod_ine"] for n in row["neighbors"]} == {"29025", "29067", "29070", "29901"}


def test_spatial_empty_pipeline_has_explicit_error():
    class EmptyRepository:
        def spatial_history(self):
            return {"years": []}
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exception:
        ObservatoryService(EmptyRepository()).spatial(None)
    assert exception.value.status_code == 503
