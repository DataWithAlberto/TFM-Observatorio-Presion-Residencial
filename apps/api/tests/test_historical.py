import json

import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.core.database import get_engine
from analytics.historical import ROOT, persist

client = TestClient(app)


def test_historical_municipality_contract_and_exclusion():
    response = client.get("/api/v1/municipios/28079/historico?serie=homogenea")
    assert response.status_code == 200
    data = response.json()
    assert data["included"] and data["metadata"]["municipality_count"] == 277
    assert [r["anio"] for r in data["items"]] == [2020, 2021, 2022, 2023]
    assert data["metadata"]["calculated_at"]
    for row in data["items"]:
        assert len(row["components"]) == 4
        assert abs(sum(c["contribution"] for c in row["components"]) - row["ipr_score"]) < 1e-10
        for component in row["components"]:
            assert component["source_key"].startswith("28079/")
            assert json.loads(component["raw_values"])
    excluded = client.get("/api/v1/municipios/20030/historico?serie=homogenea").json()
    assert not excluded["included"] and excluded["reason"] and excluded["items"] == []
    assert client.get("/api/v1/municipios/00000/historico?serie=homogenea").status_code == 404
    assert isinstance(client.get("/api/v1/municipios/28079/historico").json(), list)


def test_yearly_rankings_and_change_filters():
    universes = []
    for year in (2020, 2021, 2022, 2023):
        response = client.get(f"/api/v1/ranking?producto=historico&anio={year}")
        assert response.status_code == 200
        rows = response.json()
        assert len(rows) == 277 and rows[0]["ranking"] == 1
        assert all(row["anio"] == year for row in rows)
        universes.append({r["cod_ine"] for r in rows})
    assert all(codes == universes[0] for codes in universes)
    for order, field, positive in [("incremento", "delta_ipr", True), ("descenso", "delta_ipr", False),
                                   ("subida_ranking", "rank_change", False), ("bajada_ranking", "rank_change", True)]:
        rows = client.get(f"/api/v1/ranking?producto=historico&anio=2023&orden={order}").json()
        values = [r[field] for r in rows]
        assert values and all(v > 0 if positive else v < 0 for v in values)
        assert values == sorted(values, reverse=positive)
    assert client.get("/api/v1/ranking?producto=historico&anio=2020&orden=incremento").json() == []
    assert client.get("/api/v1/ranking?producto=historico&anio=2018").status_code == 422
    assert client.get("/api/v1/ranking?producto=historico&capa=riesgo_futuro").status_code == 422
    assert client.get("/api/v1/ranking?orden=incremento").status_code == 422
    catalogue = client.get("/api/v1/catalogo").json()
    assert catalogue["years"] == [2023]
    assert catalogue["historical"]["years"] == [2020, 2021, 2022, 2023]


def test_database_duplicate_observation_is_rejected():
    with get_engine().connect() as conn:
        transaction = conn.begin()
        try:
            with pytest.raises(IntegrityError):
                conn.execute(text("INSERT INTO ipr_historical_scores SELECT * FROM ipr_historical_scores LIMIT 1"))
        finally:
            transaction.rollback()


def test_historical_load_is_idempotent_and_rejects_changed_inputs():
    path = ROOT / "data/processed/ipr_historical"
    scores = pd.read_csv(path / "scores.csv", dtype={"cod_ine": str})
    components = pd.read_csv(path / "components.csv", dtype={"cod_ine": str})
    universe = pd.read_csv(path / "historical_municipality_universe.csv", dtype={"cod_ine": str}, keep_default_na=False)
    metadata = json.loads((path / "manifest.json").read_text())
    db_url = get_engine().url.render_as_string(hide_password=False)
    before = client.get("/api/v1/municipios/28079/historico?serie=homogenea").json()
    persist(scores, components, universe, metadata, db_url)
    assert client.get("/api/v1/municipios/28079/historico?serie=homogenea").json() == before
    changed = {**metadata, "dataset_sha256": "0" * 64}
    with pytest.raises(ValueError, match="nueva calculation_version"):
        persist(scores.assign(dataset_sha256=changed["dataset_sha256"]), components, universe, changed, db_url)
    assert client.get("/api/v1/municipios/28079/historico?serie=homogenea").json() == before
