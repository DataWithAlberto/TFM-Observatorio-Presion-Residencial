#!/usr/bin/env python3
"""Reconstrucción exploratoria del índice compuesto; nunca calcula el score oficial."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
import subprocess

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold
from xgboost import DMatrix, XGBRegressor

ROOT = Path(__file__).resolve().parent
SCORE = ROOT / 'data/processed/riesgo_futuro_residencial_score.csv'
NAMES = ROOT / 'data/processed/municipios_ine.csv'
OUTPUT = ROOT / 'apps/web/data/ml_exploratory.json'
COMPARISON = ROOT / 'data/processed/riesgo_futuro_comparacion_modelos.csv'
FEATURES = [
    'proyeccion_duracion_max_ola_calor_dias',
    'proyeccion_grados_dia_refrigeracion',
    'proyeccion_racha_seca_max_dias',
    'tendencia_asequibilidad', 'tendencia_turismo',
    'tendencia_especulacion', 'tendencia_gentrificacion',
]
LABELS = ['Ola de calor', 'Grados-día de refrigeración', 'Racha seca',
          'Tendencia de presión de acceso', 'Tendencia turística',
          'Tendencia especulativa', 'Tendencia de gentrificación']
PARAMS = dict(n_estimators=200, max_depth=3, learning_rate=0.03,
              subsample=0.8, colsample_bytree=0.8, objective='reg:squarederror',
              random_state=42, n_jobs=1)
NOTICE = ('El experimento con XGBoost tiene carácter exploratorio. Las variables de '
          'entrada participan en la construcción del índice objetivo: los resultados '
          'no constituyen evidencia de capacidad predictiva independiente ni permiten '
          'inferencias causales. El índice publicado procede exclusivamente de la fórmula interpretable.')
SHAP_NOTICE = ('SHAP explica la salida del modelo XGBoost, no el fenómeno residencial. '
               'Estas contribuciones no representan relaciones causales.')


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(df: pd.DataFrame, names: dict[str, str]) -> dict:
    """Mismo conjunto, folds e imputación de entrenamiento para salidas OOF y SHAP."""
    if df.cod_ine.duplicated().any():
        raise ValueError('Códigos municipales duplicados')
    if set(df.elegible_score.dropna().unique()) - {True, False} or df.elegible_score.isna().any():
        raise ValueError('Elegibilidad debe ser booleana y completa')
    eligible = df.loc[df.elegible_score].sort_values('cod_ine').reset_index(drop=True)
    if len(eligible) < 5:
        raise ValueError('Se requieren al menos cinco municipios elegibles')
    if eligible.anio_base.nunique() != 1 or eligible.version_metodologia.nunique() != 1:
        raise ValueError('Se requiere un único corte y versión metodológica')
    x = eligible[FEATURES].dropna(axis=1, how='all')
    y = eligible.score_riesgo_futuro.to_numpy(dtype=float)
    if not np.isfinite(y).all() or not ((0 <= y) & (y <= 100)).all():
        raise ValueError('Target elegible no finito o fuera de rango')
    if x.empty or np.isinf(x.to_numpy(dtype=float)).any():
        raise ValueError('Features vacías o infinitas')
    n, p = x.shape
    approx, dummy, bases = (np.empty(n) for _ in range(3))
    shap_values, imputed = np.empty((n, p)), np.empty((n, p))
    folds = np.empty(n, dtype=int)
    fold_metrics = []
    models_config = None
    for fold, (train, test) in enumerate(KFold(5, shuffle=True, random_state=42).split(x), 1):
        imputer = SimpleImputer(strategy='median', keep_empty_features=True)
        train_x = imputer.fit_transform(x.iloc[train])
        test_x = imputer.transform(x.iloc[test])
        model = XGBRegressor(**PARAMS).fit(train_x, y[train])
        approx[test] = model.predict(test_x)
        dummy[test] = DummyRegressor(strategy='mean').fit(train_x, y[train]).predict(test_x)
        # TreeSHAP exacto nativo: última columna = base del modelo de este fold.
        contributions = model.get_booster().predict(DMatrix(test_x), pred_contribs=True, approx_contribs=False)
        if contributions.shape != (len(test), p + 1):
            raise ValueError('Dimensión SHAP incompatible con las features')
        np.testing.assert_allclose(contributions.sum(axis=1), approx[test], atol=1e-4, rtol=1e-5)
        shap_values[test], bases[test] = contributions[:, :-1], contributions[:, -1]
        imputed[test], folds[test] = test_x, fold
        fold_metrics.append(dict(fold=fold, n_train=len(train), n_test=len(test),
                                 dummy_mae=float(mean_absolute_error(y[test], dummy[test])),
                                 xgboost_mae=float(mean_absolute_error(y[test], approx[test]))))
        models_config = {k: ('NaN' if isinstance(v, float) and np.isnan(v) else v)
                         for k, v in model.get_params().items()}
    features = [dict(name=name, label=LABELS[FEATURES.index(name)],
                     mean_abs_shap=float(np.abs(shap_values[:, j]).mean()))
                for j, name in enumerate(x.columns)]
    rows = []
    for i, row in eligible.iterrows():
        rows.append(dict(cod_ine=row.cod_ine, nombre=names.get(row.cod_ine, row.cod_ine),
                         score=float(y[i]), xgboost=float(approx[i]), dummy=float(dummy[i]),
                         residual=float(approx[i] - y[i]), absolute_error=float(abs(approx[i] - y[i])),
                         fold=int(folds[i]), shap_base=float(bases[i]), shap=shap_values[i].tolist(),
                         feature_values=[None if pd.isna(v) else float(v) for v in x.iloc[i]],
                         imputed_values=imputed[i].tolist()))
    return dict(schema_version='1.0', purpose='exploratory_index_reconstruction',
                notice=NOTICE, shap_notice=SHAP_NOTICE,
                question='¿Hasta qué punto un modelo no lineal puede aproximar la estructura del índice compuesto utilizando sus componentes?',
                official=dict(model='Fórmula interpretable', formula='0,60 × riesgo climático + 0,40 × tendencia de presión',
                              mae_cv=None, interpretation='Resultado metodológico oficial; define el target, no se entrena ni valida contra sí mismo'),
                metrics=[dict(modelo='dummy_media_cv', label='Dummy', mae_cv=float(mean_absolute_error(y, dummy)), n=n, interpretation='Referencia mínima'),
                         dict(modelo='xgboost_comparativo', label='XGBoost', mae_cv=float(mean_absolute_error(y, approx)), n=n, interpretation='Aproximación exploratoria')],
                features=features, rows=rows,
                metadata=dict(random_state=42, n_municipalities=n, n_universe=len(df), n_features=p,
                              excluded_features=[f for f in FEATURES if f not in x.columns],
                              anio_base=int(eligible.anio_base.iloc[0]), version_metodologia=str(eligible.version_metodologia.iloc[0]),
                              cv=dict(method='KFold', n_splits=5, shuffle=True, random_state=42, output='out_of_fold', folds=fold_metrics),
                              model_params=models_config, explicit_params=PARAMS,
                              imputation='median fitted on training fold; keep_empty_features=True',
                              shap=dict(method='XGBoost native exact TreeSHAP', pred_contribs=True, approx_contribs=False,
                                        scope='all eligible municipalities, held-out fold only', sample_size=n,
                                        base='training-tree expected output, separate for each fold',
                                        global_summary='mean absolute OOF contribution; aggregate of five models, not one fitted model')))


def generate(score: Path = SCORE, names_file: Path = NAMES) -> dict:
    source = pd.read_csv(score, dtype={'cod_ine': str, 'version_metodologia': str})
    names_df = pd.read_csv(names_file, dtype={'id_municipio': str})
    result = analyze(source, dict(zip(names_df.id_municipio, names_df.nombre)))
    try:
        commit = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = 'unknown'
    result['metadata'].update(
        generated_at=datetime.now(timezone.utc).isoformat(),
        pipeline_version=os.getenv('PIPELINE_VERSION', commit),
        versions={name: version(name) for name in ['numpy', 'pandas', 'scikit-learn', 'xgboost']},
        python_version=platform.python_version(),
        files=[dict(dataset=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path),
                    sha256=sha256(path), file_size=path.stat().st_size, status='present')
               for path in [score, names_file, Path(__file__).resolve(), ROOT / '17_indice_riesgo_futuro.py']],
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--comparison', type=Path, default=COMPARISON)
    args = parser.parse_args()
    # Salidas restringidas a artefactos experimentales; nunca permitir sobrescribir scores.
    protected = {p.resolve() for p in (ROOT / 'data').rglob('*') if p.is_file()} - {COMPARISON.resolve()}
    destinations = [args.output.resolve(), args.comparison.resolve()]
    if any(p in protected for p in destinations) or len(set(destinations)) != 2:
        parser.error('Las salidas deben ser distintas y no pueden sobrescribir datasets oficiales')
    result = generate()
    for path in [args.output, args.comparison]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    comparison = pd.DataFrame(result['metrics'])
    comparison['decision'] = 'exploratorio: reconstrucción del índice; sin validez predictiva independiente; excluido del score oficial'
    comparison.to_csv(args.comparison, index=False)
    print(f"{result['metadata']['n_municipalities']} municipios; {result['metadata']['n_features']} features; salidas OOF y SHAP: {args.output}")
    print(comparison[['label', 'mae_cv', 'n']].to_string(index=False))
    print(NOTICE)


if __name__ == '__main__':
    main()
