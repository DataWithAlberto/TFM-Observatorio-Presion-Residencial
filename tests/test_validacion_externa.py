"""Contratos de independencia, cobertura, ingesta e inferencia externa."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("external", ROOT / "24_validacion_externa_ipr.py")
external = importlib.util.module_from_spec(spec)
spec.loader.exec_module(external)


@pytest.fixture
def config():
    c = json.loads(external.CONFIG.read_text())
    c.update(universo=20, permutaciones=199)
    return c


@pytest.fixture
def universe(config):
    return pd.DataFrame({"cod_ine": [f"01{i:03}" for i in range(20)], "nombre": [f"M{i}" for i in range(20)],
                         "anio": 2023, external.X: np.arange(20)*5., external.X5: np.arange(20)*4.})


def raw_rows(universe, config):
    rows = []
    for year in [2022, 2023, 2024]:
        for i, row in universe.iterrows():
            rows.append({"COD_POSTAL": row.cod_ine, "COD_PROVINCIA": "01", "NOMBRE_MUNICIPIO": row.nombre,
                         "AÑO": str(year), "VALOR": str(300 + i*20.5), **config['filtros']})
    return pd.DataFrame(rows)


def test_ingestion_filters_decimal_codes_and_preserves_missing(universe, config):
    raw = raw_rows(universe, config)
    # Missing published value is not zero and differs from absent municipality.
    raw.loc[raw.index[20], "VALOR"] = ".."
    raw = raw.drop(index=21)
    ignored = raw.iloc[[0]].assign(TIPO_VIVIENDA="UNIFAMILIAR", VALOR="99999")
    result = external.process_external(pd.concat([raw, ignored]), universe, config)
    cut = result[result.anio_externo.eq(2023)].set_index("cod_ine")
    assert cut.loc["01000", "estado"] == "valor_ausente"
    assert cut.loc["01001", "estado"] == "sin_registro"
    assert pd.isna(cut.loc["01001", external.Y])
    assert cut.loc["01003", external.Y] == 361.5
    assert len(result) == 60
    assert external.X not in result.columns


@pytest.mark.parametrize("bad", ["duplicate", "province", "zero", "infinite", "text", "schema", "code"])
def test_rejects_corrupt_source(universe, config, bad):
    raw = raw_rows(universe, config)
    if bad == "duplicate":
        raw = pd.concat([raw, raw.iloc[[0]]])
    elif bad == "schema":
        raw = raw.drop(columns="TIPO_MEDIDA")
    else:
        column, value = {"province": ("COD_PROVINCIA", "02"), "zero": ("VALOR", "0"),
                         "infinite": ("VALOR", "inf"), "text": ("VALOR", "oops"),
                         "code": ("COD_POSTAL", "010000")}[bad]
        raw.loc[0, column] = value
    with pytest.raises(ValueError):
        external.process_external(raw, universe, config)


def test_stops_below_predefined_coverage(universe, config):
    raw = raw_rows(universe, config)
    raw = raw[~raw.COD_POSTAL.isin(["01000", "01001", "01002"])]
    values = external.process_external(raw, universe, config)
    with pytest.raises(ValueError, match="Regla de parada"):
        external.analyze(universe, values, config)


def test_negative_association_is_reported_and_index_not_mutated(universe, config):
    before = universe.copy(deep=True)
    values = external.process_external(raw_rows(universe, config), universe, config)
    values[external.Y] = 1000 - values[external.Y]
    result, paired = external.analyze(universe, values, config)
    assert result["correlaciones"][0]["rho"] == pytest.approx(-1.)
    assert result["correlaciones"][0]["p_value"] > 0
    assert "contradice" in result["interpretacion"]
    assert len(result["grupos"]) == 4
    assert len(paired) == 20
    pd.testing.assert_frame_equal(universe, before)


def test_constant_and_insufficient_samples_do_not_emit_nan(config):
    for frame in [pd.DataFrame({external.X: [1, 1, 1], external.Y: [2, 3, 4]}),
                  pd.DataFrame({external.X: [1, 2], external.Y: [2, 3]})]:
        result = external.correlation(frame, external.X, "test", 2023, config)
        assert result["rho"] is None and result["p_value"] is None
        json.dumps(result, allow_nan=False)


def test_non_significant_result_is_not_hidden(universe, config):
    values = external.process_external(raw_rows(universe, config), universe, config)
    values[external.Y] = [400 if i % 2 else 600 for i in range(len(values))]
    result, _ = external.analyze(universe, values, config)
    assert result["correlaciones"][0]["p_value"] >= config["alpha"]
    assert "No se obtiene evidencia" in result["interpretacion"]


def test_permutation_is_reproducible_with_ties(config):
    frame = pd.DataFrame({external.X: [1, 2, 2, 3, 4, 5], external.Y: [2, 1, 2, 4, 5, 3]})
    a = external.correlation(frame, external.X, "test", 2023, config)
    b = external.correlation(frame, external.X, "test", 2023, config)
    assert a == b
    assert a["rho"] == pytest.approx(external.stats.spearmanr(frame[external.X], frame[external.Y]).statistic)


def test_quartiles_do_not_split_ties():
    values = pd.Series([0, 10, 20, 20, 20, 30, 40, 50, 60, 70])
    groups = external.quartiles(values)
    assert groups[values.eq(20)].nunique() == 1
    assert external.quartiles(pd.Series([1, 1, 1, 1, 1])).isna().all()


def test_common_temporal_sample_and_missing_ipr5(universe, config):
    universe.loc[0, external.X5] = np.nan
    raw = raw_rows(universe, config)
    raw = raw[~(raw.COD_POSTAL.eq("01001") & raw['AÑO'].eq('2022'))]
    values = external.process_external(raw, universe, config)
    result, _ = external.analyze(universe, values, config)
    rows = result["correlaciones"]
    assert rows[0]["n"] == 20
    assert rows[2]["n"] == rows[3]["n"] == 19
    assert [r["n"] for r in rows if r["analisis"].startswith("sensibilidad_temporal")] == [19, 19, 19]


def test_archived_source_hash_and_real_coverage():
    config = json.loads(external.CONFIG.read_text())
    external.source(config, refresh=False)
    universe = external.load_ipr(external.IPR, config)
    raw = pd.read_csv(external.RAW, sep=';', dtype=str)
    values = external.process_external(raw, universe, config)
    cut = values[values.anio_externo.eq(2023)]
    assert cut[external.Y].notna().sum() == 295
    assert set(cut.loc[cut[external.Y].isna(), 'cod_ine'].str[:2]) == {'01', '48'}
    assert cut.set_index('cod_ine').loc['28079', external.Y] == 825


def test_rejects_cached_source_without_matching_provenance(tmp_path, monkeypatch, config):
    archive = tmp_path / 'source.csv.gz'
    archive.write_bytes(external.gzip.compress(b'changed data'))
    archive.with_suffix('.metadata.json').write_text(json.dumps({
        'source_url': config['url'], 'downloaded_at': '2026-09-11T00:00:00Z',
        'archive_sha256': 'incorrect', 'download_sha256': 'incorrect',
    }))
    monkeypatch.setattr(external, 'RAW', archive)
    with pytest.raises(ValueError, match='trazabilidad'):
        external.source(config, refresh=False)
