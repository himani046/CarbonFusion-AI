"""CarbonFusion AI: GEDI-supervised AGBD regression and geographic evaluation.

GEDI L4A AGBD labels are modeled reference estimates, not field truth.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBRegressor
import joblib

OPTICAL = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B11', 'B12', 'ndvi', 'ndmi', 'ndre']
TERRAIN = ['elevation', 'slope']
REQUIRED = ['longitude', 'latitude', 'agbd', 'agbd_se'] + OPTICAL + TERRAIN


def prepare(df: pd.DataFrame, block_deg=0.08):
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError(f'Missing columns: {missing}')
    df = df.copy().replace([np.inf, -np.inf], np.nan).dropna(subset=REQUIRED)
    df = df[(df.agbd > 0) & (df.agbd < 600) & (df.agbd_se >= 0) &
            (df.agbd_se / df.agbd <= 0.5)].copy()
    if not len(df):
        raise ValueError('No rows remain after filtering; check GEDI QC and units')
    bx = np.floor(df.longitude.to_numpy() / block_deg).astype(int)
    by = np.floor(df.latitude.to_numpy() / block_deg).astype(int)
    df['spatial_block'] = pd.Series([f'{x}_{y}' for x, y in zip(bx, by)], index=df.index)
    return df


def score(y, pred):
    return {'mae_mg_ha': float(mean_absolute_error(y, pred)),
            'rmse_mg_ha': float(np.sqrt(mean_squared_error(y, pred))),
            'r2': float(r2_score(y, pred))}


def make_model(kind, seed):
    if kind == 'random_forest':
        return RandomForestRegressor(n_estimators=150, min_samples_leaf=4,
                                     n_jobs=-1, random_state=seed)
    return XGBRegressor(n_estimators=250, max_depth=5, learning_rate=0.06,
                        subsample=0.85, colsample_bytree=0.85,
                        objective='reg:squarederror', n_jobs=4, random_state=seed)


def run_experiment(csv_path, output_dir, seed=42, block_deg=0.08):
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    df = prepare(pd.read_csv(csv_path), block_deg=block_deg)
    groups = df.spatial_block.to_numpy()
    if df.spatial_block.nunique() < 8:
        raise ValueError('At least 8 spatial blocks are needed for this demo split')

    split = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
    train_cal_idx, test_idx = next(split.split(df, groups=groups))
    interim = df.iloc[train_cal_idx].reset_index(drop=True)
    holdout = df.iloc[test_idx].copy()
    split2 = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed+1)
    fit_idx, cal_idx = next(split2.split(interim, groups=interim.spatial_block))
    fit = interim.iloc[fit_idx]
    cal = interim.iloc[cal_idx]

    comparisons = []
    specs = [('random_forest_optical', 'random_forest', OPTICAL),
             ('xgboost_optical', 'xgboost', OPTICAL),
             ('xgboost_optical_terrain', 'xgboost', OPTICAL + TERRAIN)]
    trained = {}
    for name, kind, features in specs:
        model = make_model(kind, seed)
        model.fit(fit[features], fit.agbd)
        predictions = np.maximum(0, model.predict(holdout[features]))
        comparisons.append({'model': name, **score(holdout.agbd, predictions)})
        trained[name] = (model, features)

    model, features = trained['xgboost_optical_terrain']
    # Interval coverage against GEDI modeled references; no shift guarantee.
    cal_pred = np.maximum(0, model.predict(cal[features]))
    residuals = np.abs(cal.agbd.to_numpy() - cal_pred)
    alpha = 0.10
    q_level = min(1., np.ceil((len(residuals)+1)*(1-alpha)) / len(residuals))
    q = float(np.quantile(residuals, q_level, method='higher'))
    p = np.maximum(0, model.predict(holdout[features]))
    lower, upper = np.maximum(0, p-q), p+q
    coverage = float(np.mean((holdout.agbd.to_numpy() >= lower) & (holdout.agbd.to_numpy() <= upper)))
    width = float(np.mean(upper-lower))

    results = {'data': {'rows_after_qc': len(df), 'fit_rows': len(fit),
                        'calibration_rows': len(cal), 'test_rows': len(holdout),
                        'spatial_blocks': int(df.spatial_block.nunique()),
                        'block_degrees': block_deg},
               'comparison': comparisons,
               'uncertainty': {'method': 'split_conformal_absolute_residual',
                               'nominal_coverage': 0.9, 'empirical_test_coverage': coverage,
                               'mean_interval_width_mg_ha': width,
                               'calibration_half_width_mg_ha': q},
               'notes': ['GEDI AGBD is modeled reference data, not field truth.',
                         'Spatial groups help limit leakage; this is not fully buffered spatial CV.',
                         'Intervals are marginal and not guaranteed under geographic shift.',
                         'Data provenance must be checked for each input CSV; GEDI labels are modeled and are not field ground truth.']}
    with open(out/'metrics.json', 'w') as f:
        json.dump(results, f, indent=2)
    test_out = holdout[['longitude','latitude','agbd','agbd_se','spatial_block']].copy()
    test_out['pred_agbd'] = p
    test_out['pi_low'] = lower
    test_out['pi_high'] = upper
    test_out['pred_carbon_t_ha'] = p * 0.47
    test_out.to_csv(out/'heldout_predictions.csv', index=False)
    joblib.dump({'model': model, 'features': features, 'conformal_half_width': q,
                 'carbon_fraction': 0.47}, out/'biomass_model.joblib')
    return results
