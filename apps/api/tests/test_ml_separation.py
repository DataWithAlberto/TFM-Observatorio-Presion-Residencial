"""El ML no forma parte del contrato productivo de consulta municipal."""
import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parents[3]


def test_official_api_is_unchanged_after_exploratory_run():
    client = TestClient(app)
    paths = [
        '/api/v1/indice?producto=prospectivo',
        '/api/v1/municipios/28079?producto=prospectivo',
        '/api/v1/prospectiva',
    ]
    before = [client.get(path) for path in paths]
    assert all(response.status_code == 200 for response in before)
    spec = importlib.util.spec_from_file_location('ml_api_regression', ROOT / '25_analisis_ml_exploratorio.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.generate()
    for path, response in zip(paths, before):
        assert client.get(path).json() == response.json()
    schema_paths = app.openapi()['paths']
    assert not any('/analysis/ml' in path or '/analisis-ml' in path for path in schema_paths)
    assert client.get('/api/v1/analysis/ml/comparison').status_code == 404
