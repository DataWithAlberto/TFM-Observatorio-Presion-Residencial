from pathlib import Path

import pandas as pd
import pytest

from database.bootstrap.data_quality import (
    COMPONENTS, calculate, level, recency, score_components, sensitivity,
)

ROOT = Path(__file__).resolve().parents[1]


def evidence(year=2023):
    return [{"component": c, "value": 50.0, "source_year": year,
             "statistical_period": str(year)} for c in COMPONENTS]


def test_complete_current_and_independent_of_ipr_values():
    values = evidence()
    a = score_components(values, 2023)
    values[0]["value"] = 0
    values[1]["value"] = 100
    b = score_components(values, 2023)
    assert a == b
    assert a["score"] == a["coverage"] == a["recency"] == 100
    assert a["consistency"] is None
    assert a["level"] == "alta"


def test_old_missing_and_inconsistent_cases():
    old = score_components(evidence(2010), 2023)
    assert old["recency"] == 0
    assert old["score"] == 62.5
    assert old["level"] == "baja"
    missing = evidence()
    missing[0]["value"] = None
    result = score_components(missing, 2023)
    assert result["coverage"] == 75
    assert result["recency"] == 100
    assert result["score"] == 84.375
    assert result["level"] == "media"
    assert result["components"][0]["recency_score"] is None
    missing[0]["value"] = 101
    invalid = score_components(missing, 2023)
    assert invalid["score"] == result["score"]
    assert invalid["consistency"] is None
    assert any("fuera de rango" in issue for issue in invalid["issues"])


def test_no_information_and_unknown_period_do_not_produce_scores():
    missing = evidence()
    for item in missing:
        item["value"] = None
    assert score_components(missing, 2023)["score"] is None
    partial = evidence()
    partial[0]["source_year"] = None
    assert score_components(partial, 2023)["score"] is None


@pytest.mark.parametrize("score,expected", [(0, "muy_baja"), (49.99, "muy_baja"), (50, "baja"), (69.99, "baja"), (70, "media"), (84.99, "media"), (85, "alta"), (100, "alta"), (None, None)])
def test_thresholds(score, expected):
    assert level(score) == expected


def test_period_and_weight_guards():
    assert recency(2023, 2022) == 100
    assert recency(2023, 2021) == 90
    assert recency(2023, 2020) == 80
    for weights in [(0.5, 0.3), (-0.1, 1.1), (float("nan"), 0), (1,)]:
        with pytest.raises(ValueError):
            score_components(evidence(), 2023, weights)
    for year in [1899, 2101, 2023.5]:
        with pytest.raises(ValueError):
            score_components(evidence(), year)
    with pytest.raises(ValueError):
        score_components(evidence(2024), 2023)
    with pytest.raises(ValueError):
        score_components([evidence()[0]] * 4, 2023)


def dataset():
    frame = pd.read_csv(ROOT / "data/processed/indice_presion_residencial_2023.csv", dtype={"cod_ine": str})
    return frame, set(frame.cod_ine)


def test_real_dataset_traceability_and_sensitivity():
    frame, codes = dataset()
    original = frame.copy(deep=True)
    rows, components, audit = calculate(ROOT / "data/processed", frame, codes)
    pd.testing.assert_frame_equal(frame, original)
    assert len(rows) == 306 and len(components) == 1224 and len(audit) == 4
    for row in rows:
        q = row["data_quality"]
        assert q["score"] == 99.0625
        assert q["coverage"] == 100 and q["recency"] == 97.5
        assert q["consistency"] is None
        assert q["components"][2]["source_year"] == 2021
        assert q["components"][3]["source_year"] == 2023
    report = sensitivity(rows)
    assert all(r["spearman"] is None and not r["cambios_categoria"] for r in report)
    assert max(r["cambio_score_max"] for r in report) == 0.3125


def test_duplicate_unknown_and_stale_inputs_fail():
    frame, codes = dataset()
    with pytest.raises(ValueError, match="duplicadas"):
        calculate(ROOT / "data/processed", pd.concat([frame, frame]), codes)
    with pytest.raises(ValueError, match="ajenos"):
        calculate(ROOT / "data/processed", frame, set())
    frame.loc[0, "score_origen_turismo"] += 1
    with pytest.raises(ValueError, match="no coincide"):
        calculate(ROOT / "data/processed", frame, codes)


def test_sensitivity_reports_category_changes_and_real_correlations():
    rows = []
    for i, year in enumerate([2023, 2021, 2015]):
        ev = evidence(year)
        if i == 0:
            ev[0]["value"] = None
        rows.append({"cod_ine": str(i), "anio": 2023, "data_quality": score_components(ev, 2023)})
    report = sensitivity(rows)
    assert report[0]["spearman"] == pytest.approx(1)
    assert "0" in report[1]["cambios_categoria"]


def test_source_validation_reports_and_period_metadata(tmp_path):
    import shutil
    from database.bootstrap.data_quality import EVIDENCE_FILES
    for name in EVIDENCE_FILES:
        shutil.copy(ROOT / "data/processed" / name, tmp_path / name)
    frame, codes = dataset()
    path = tmp_path / "indicadores_especulativos.csv"
    meta = pd.read_csv(path, dtype={"cod_ine": str})
    meta.loc[(meta.cod_ine == frame.iloc[0].cod_ine) & (meta.anio == 2023), "anio_referencia"] = None
    meta.to_csv(path, index=False)
    rows, _, _ = calculate(tmp_path, frame, codes)
    assert rows[0]["data_quality"]["score"] is None
    (tmp_path / "ipr_validaciones.csv").write_text("prueba,estado,detalle\ncontrol,ERROR,fallo\n")
    with pytest.raises(ValueError, match="fallidas"):
        calculate(tmp_path, frame, codes)


def test_scores_are_specific_to_municipality_and_year():
    frame, codes = dataset()
    current = frame[frame.cod_ine.eq("28079")].copy()
    previous = current.copy()
    previous["anio"] = 2022
    for component, (filename, score_column, period) in COMPONENTS.items():
        source = pd.read_csv(ROOT / "data/processed" / filename, dtype={"cod_ine": str})
        selected = source[source.cod_ine.eq("28079")]
        selected = selected[selected[period].eq("2022-08-01" if period == "fecha" else 2022)]
        previous[f"score_origen_{component}"] = selected.iloc[0][score_column]
    rows, _, _ = calculate(ROOT / "data/processed", pd.concat([previous, current]), codes)
    assert [(r["anio"], r["data_quality"]["score"]) for r in rows] == [(2022, 100), (2023, 99.0625)]
