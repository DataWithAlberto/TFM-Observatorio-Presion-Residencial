"""Invariantes longitudinales y regresión del corte transversal publicado."""

import importlib.util
import io
from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from analytics.historical import ROOT, VARIABLES, audit, calculate, eligible_layers, select_period, validate_results
from analytics.normalization import ajustar_hogares, percentil


@pytest.fixture(scope="module")
def audited():
    return audit()


@pytest.fixture(scope="module")
def calculated(audited):
    _, layers, _, _, universe, metadata = audited
    return calculate(layers, universe, metadata)


def test_actual_period_universe_and_coverage(audited, calculated):
    _, _, coverage, _, universe, metadata = audited
    scores, components = calculated
    assert metadata["years"] == [2020, 2021, 2022, 2023]
    assert universe.included.sum() == 277
    assert len(universe) == 306
    assert universe.loc[~universe.included, "reason"].str.len().gt(0).all()
    assert len(scores) == 1108 and len(components) == 4432
    assert all(scores.groupby("anio").cod_ine.agg(set).map(lambda codes: codes == set(universe.loc[universe.included, "cod_ine"])))
    tourism = coverage[(coverage.componente == "turismo") & (coverage.variable == "vut_por_1000_hab")]
    assert tourism[tourism.anio.eq(2019)].municipios_validos.item() == 0
    assert tourism[tourism.anio.eq(2020)].municipios_validos.item() == 306
    for code in ("20030", "20067", "48015", "48027", "48036", "48054", "48084"):
        assert not universe.loc[universe.cod_ine.eq(code), "included"].item()


def test_selection_does_not_assume_dates_or_bridge_gaps():
    codes = [f"{n:05d}" for n in range(280)]
    frame = pd.DataFrame([(c, y) for y in (2011, 2012, 2014, 2015) for c in codes], columns=["cod_ine", "anio"])
    years, selected = select_period(dict.fromkeys(VARIABLES, frame))
    assert years == [2014, 2015] and selected == set(codes)
    _, selected = select_period({**dict.fromkeys(VARIABLES, frame), "turismo": frame[frame.anio.eq(2015)]})
    assert not selected


def test_tourism_requires_august_and_matching_population(audited):
    frames = deepcopy(audited[0])
    index = frames["turismo"].index[frames["turismo"].fecha.eq(pd.Timestamp("2020-08-01"))][0]
    code = frames["turismo"].loc[index, "cod_ine"]
    frames["turismo"].loc[index, "anio_poblacion"] = 2019
    eligible = eligible_layers(frames)["turismo"]
    assert not ((eligible.cod_ine == code) & (eligible.anio == 2020)).any()
    assert eligible.fecha.dt.month.eq(8).all()


def test_reproducibility_under_input_permutation(audited, calculated):
    _, layers, _, _, universe, metadata = audited
    permuted = {k: f.sample(frac=1, random_state=7) for k, f in layers.items()}
    scores, components = calculate(permuted, universe, metadata)
    pd.testing.assert_frame_equal(scores, calculated[0], atol=1e-12, rtol=1e-12)
    pd.testing.assert_frame_equal(components.reset_index(drop=True), calculated[1].reset_index(drop=True), atol=1e-12, rtol=1e-12)


@pytest.mark.parametrize("mutation", ["duplicate", "missing", "infinite"])
def test_invalid_components_never_produce_a_partial_ipr(audited, mutation):
    _, layers, _, _, universe, metadata = audited
    layers = deepcopy(layers)
    frame = layers["asequibilidad"]
    index = frame.index[frame.cod_ine.eq("28079") & frame.anio.eq(2020)][0]
    if mutation == "duplicate":
        layers["asequibilidad"] = pd.concat([frame, frame.loc[[index]]])
    elif mutation == "missing":
        layers["asequibilidad"] = frame.drop(index)
    else:
        layers["asequibilidad"].loc[index, "ratio_asequibilidad"] = np.inf
    with pytest.raises(ValueError):
        calculate(layers, universe, metadata)


def test_normalization_does_not_claim_absolute_pressure_changes():
    baseline = pd.Series([10.0, 20.0, 30.0, np.nan])
    pd.testing.assert_series_equal(percentil(baseline), percentil(baseline + 10))
    assert np.isnan(percentil(baseline).iloc[-1])
    # A municipality can change percentile even when its own raw value is fixed.
    assert percentil(pd.Series([10.0, 20.0, 30.0])).iloc[1] == 50
    assert percentil(pd.Series([25.0, 20.0, 30.0])).iloc[1] == 0
    assert percentil(pd.Series([1.0, 1.0, 1.0])).eq(50).all()


def test_deltas_reconcile_with_contributions(calculated):
    scores, components = calculated
    changes = components.groupby(["cod_ine", "anio"]).delta_contribution.sum(min_count=4)
    np.testing.assert_allclose(changes, scores.set_index(["cod_ine", "anio"]).delta_ipr, atol=1e-12)
    assert scores[scores.anio.eq(2020)].delta_ipr.isna().all()
    assert scores[scores.anio.eq(2020)].rank_change.isna().all()


def test_csv_round_trip_preserves_rankings_and_validation(audited, calculated):
    scores, components = [pd.read_csv(io.StringIO(frame.to_csv(index=False)), dtype={"cod_ine": str}) for frame in calculated]
    validate_results(scores, components, audited[-1]["years"], set(scores.cod_ine))


@pytest.mark.parametrize("field", ["rank", "rank_change", "ipr_percentile", "delta_ipr", "delta_since_start"])
def test_temporal_metric_corruption_is_rejected(audited, calculated, field):
    scores, components = calculated
    scores = scores.copy()
    index = scores.index[scores.anio.eq(2021)][0]
    scores.loc[index, field] += 1
    with pytest.raises(ValueError):
        validate_results(scores, components, audited[-1]["years"], set(scores.cod_ine))


def test_current_ipr_remains_numerically_identical():
    spec = importlib.util.spec_from_file_location("current_ipr", ROOT / "18_indice_presion_residencial.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result, _ = module.construir_resultados(module.cargar_matriz())
    existing = pd.read_csv(ROOT / "data/processed/indice_presion_residencial_2023.csv", dtype={"cod_ine": str}).sort_values("cod_ine")
    for column in ("ipr4_nacional_observado", "ipr5_prospectivo", "ranking_ipr4", "ranking_ipr5_prospectivo"):
        np.testing.assert_allclose(result[column].to_numpy(dtype=float, na_value=np.nan), existing[column], rtol=1e-12, atol=1e-12)


def test_shared_household_adjustment_preserves_current_layer(audited):
    for _, group in audited[0]["gentrificacion"].groupby("anio"):
        np.testing.assert_allclose(ajustar_hogares(group), group.transformacion_hogares_ajustada_3a,
                                   atol=1e-12, equal_nan=True)
