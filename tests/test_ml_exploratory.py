"""Regresión metodológica: aproximación OOF y SHAP aislados del índice oficial."""
import ast
import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


ml = module('ml', '25_analisis_ml_exploratorio.py')
index = module('official', '17_indice_riesgo_futuro.py')


class ExploratoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = pd.read_csv(ml.SCORE, dtype={'cod_ine': str, 'version_metodologia': str})
        cls.report = ml.generate()

    def test_official_formula_matches_published_scores_without_ml(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(index, 'OUT_SCORE', Path(directory) / 'score.csv'), patch.object(XGBRegressor, 'fit', side_effect=AssertionError('ML llamado desde score oficial')):
            recomputed = index.calcular()
        actual = recomputed.sort_values('cod_ine').reset_index(drop=True)
        expected = self.source.sort_values('cod_ine').reset_index(drop=True)
        pd.testing.assert_frame_equal(actual, expected, check_dtype=False, atol=1e-10, rtol=1e-10)

    def test_experiment_leaves_all_official_datasets_and_input_unchanged(self):
        files = [p for p in (ROOT / 'data').rglob('*') if p.is_file()]
        before = {p: ml.sha256(p) for p in files}
        original = self.source.copy(deep=True)
        ml.analyze(self.source, {})
        self.assertEqual(before, {p: ml.sha256(p) for p in files})
        pd.testing.assert_frame_equal(original, self.source)

    def test_metrics_match_independent_legacy_cross_validation(self):
        eligible = self.source.loc[self.source.elegible_score].sort_values('cod_ine')
        x = eligible[ml.FEATURES].dropna(axis=1, how='all')
        y = eligible.score_riesgo_futuro.to_numpy()
        cv = KFold(5, shuffle=True, random_state=42)
        approx = cross_val_predict(make_pipeline(SimpleImputer(strategy='median'), XGBRegressor(**ml.PARAMS)), x, y, cv=cv)
        dummy = cross_val_predict(DummyRegressor(strategy='mean'), x, y, cv=cv)
        rows = self.report['rows']
        np.testing.assert_allclose([r['xgboost'] for r in rows], approx)
        np.testing.assert_allclose([r['dummy'] for r in rows], dummy)
        for metric, output in zip(self.report['metrics'], [dummy, approx]):
            self.assertAlmostEqual(metric['mae_cv'], np.mean(abs(y-output)))
            self.assertEqual(metric['n'], len(eligible))
        self.assertEqual([r['cod_ine'] for r in rows], eligible.cod_ine.tolist())
        for fold, (_, test) in enumerate(cv.split(x), 1):
            self.assertEqual([i for i, r in enumerate(rows) if r['fold'] == fold], test.tolist())

    def test_regenerated_artifact_and_shap_alignment(self):
        committed = json.loads(ml.OUTPUT.read_text())
        for key in ['rows', 'metrics', 'features']:
            self.assertEqual(committed[key], self.report[key])
        rows = self.report['rows']
        shap = np.array([r['shap'] for r in rows])
        self.assertEqual(shap.shape, (303, 6))
        self.assertEqual([f['name'] for f in self.report['features']], [f for f in ml.FEATURES if f != 'tendencia_especulacion'])
        np.testing.assert_allclose(shap.sum(axis=1) + [r['shap_base'] for r in rows], [r['xgboost'] for r in rows], atol=1e-4)
        np.testing.assert_allclose(abs(shap).mean(axis=0), [f['mean_abs_shap'] for f in self.report['features']])
        for row in rows:
            self.assertEqual(len(row['feature_values']), 6)
            self.assertEqual(len(row['imputed_values']), 6)
        # Missing gentrification remains visible; imputations use only training rows.
        source = self.source[self.source.elegible_score].sort_values('cod_ine').reset_index(drop=True)
        for row in rows:
            for j, value in enumerate(row['feature_values']):
                if value is None:
                    name = self.report['features'][j]['name']
                    train = [i for i, r in enumerate(rows) if r['fold'] != row['fold']]
                    self.assertAlmostEqual(row['imputed_values'][j], source.iloc[train][name].median())

    def test_shuffling_input_does_not_change_results(self):
        shuffled = ml.analyze(self.source.sample(frac=1, random_state=10), {})
        expected = ml.analyze(self.source, {})
        self.assertEqual(shuffled, expected)

    def test_bad_input_fails_explicitly(self):
        cases = [pd.concat([self.source, self.source.iloc[:1]]), self.source.iloc[:3].copy()]
        missing_target = self.source.copy()
        missing_target.loc[missing_target.elegible_score, 'score_riesgo_futuro'] = np.nan
        cases.append(missing_target)
        bad_eligibility = self.source.copy()
        bad_eligibility['elegible_score'] = 'False'
        cases.append(bad_eligibility)
        for case in cases:
            with self.subTest(shape=case.shape), self.assertRaises(ValueError):
                ml.analyze(case, {})

    def test_ml_imports_and_artifacts_are_absent_from_productive_paths(self):
        paths = [ROOT / '17_indice_riesgo_futuro.py', ROOT / '18_indice_presion_residencial.py', * (ROOT / 'apps/api/app').rglob('*.py'), * (ROOT / 'database').rglob('*.py')]
        for path in paths:
            tree = ast.parse(path.read_text())
            imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
            imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
            self.assertFalse(any(name and (name.startswith(('xgboost', 'shap')) or 'ml_exploratorio' in name) for name in imports), str(path))
            self.assertNotIn('ml_exploratory.json', path.read_text())
        for page in ['ranking', 'observatorio', 'prospectiva', 'municipio/[codIne]']:
            self.assertNotIn('ml_exploratory', (ROOT / 'apps/web/app/(app)' / page / 'page.tsx').read_text())

    def test_cli_rejects_official_score_as_output(self):
        before = ml.sha256(ml.SCORE)
        result = subprocess.run([sys.executable, str(ROOT / '25_analisis_ml_exploratorio.py'),
                                 '--output', str(ml.SCORE)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('no pueden sobrescribir datasets oficiales', result.stderr)
        self.assertEqual(before, ml.sha256(ml.SCORE))

    def test_comparison_csv_matches_the_dashboard(self):
        metrics = pd.read_csv(ml.COMPARISON)
        self.assertEqual(metrics.modelo.tolist(), [m['modelo'] for m in self.report['metrics']])
        np.testing.assert_allclose(metrics.mae_cv, [m['mae_cv'] for m in self.report['metrics']])
        self.assertTrue(metrics.n.eq(self.report['metadata']['n_municipalities']).all())

    def test_traceability_hashes_match_sources(self):
        for source in self.report['metadata']['files']:
            self.assertEqual(source['sha256'], ml.sha256(ROOT / source['dataset']))
        self.assertEqual(self.report['metadata']['cv']['output'], 'out_of_fold')
        self.assertEqual(self.report['metadata']['shap']['sample_size'], 303)


if __name__ == '__main__':
    unittest.main()
