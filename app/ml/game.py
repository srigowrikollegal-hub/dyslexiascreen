"""Gamified-test module: XGBoost + Extra Trees ensemble averaged on the
log-odds scale, Platt calibration, and TreeSHAP reasons from the XGBoost member."""
import os, sys, json
import numpy as np, joblib

ART = os.path.join(os.path.dirname(__file__), '..', '..', 'artifacts')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'training'))
from game_features import engineered, items_to_row, RAW, QUICK, quick_features  # noqa: E402
from app.ml.compact_forest import predict as forest_predict  # noqa: E402

_b = None
_bq = None
CUTOFF = 0.11
NICE = {'quick': 'short test', 'letter': 'letter sounds', 'syllable': 'syllables', 'word': 'words', 'pairs': 'visual search', 'pseudo': 'made-up words',
        'spelling': 'spelling', 'building': 'word building', 'memory': 'memory and dictation', 'total': 'whole test', 'overall': 'whole test'}
SUFFIX = {'Clicks': 'taps', 'Hits': 'correct answers', 'Misses': 'mistakes', 'accuracy': 'accuracy', 'missrate': 'mistake rate'}
SPECIAL = {'n_skipped': 'exercises skipped', 'n_low_accuracy': 'exercises below 50% accuracy', 'accuracy_spread': 'uneven accuracy across exercises',
           'hits_per_year_of_age': 'correct answers for age', 'device_tablet': 'device',
           'quick_low_accuracy': 'exercises below 50% accuracy', 'quick_hits_per_year_of_age': 'correct answers for age',
           'quick_accuracy': 'overall accuracy', 'quick_missrate': 'overall mistake rate'}


def bundle():
    global _b
    if _b is None:
        _b = joblib.load(os.path.join(ART, 'game_model.joblib'))
    return _b


def label_of(name):
    if name in SPECIAL:
        return SPECIAL[name]
    if name in ('Gender', 'Nativelang', 'Otherlang', 'Age'):
        return {'Gender': 'gender', 'Nativelang': 'tested in first language', 'Otherlang': 'speaks another language', 'Age': 'age'}[name]
    for m in ['Clicks', 'Hits', 'Misses', 'Score', 'Accuracy', 'Missrate']:
        if name.startswith(m) and name[len(m):].isdigit():
            return f'exercise {name[len(m):]}: ' + {'Clicks': 'taps', 'Hits': 'correct', 'Misses': 'mistakes', 'Score': 'score', 'Accuracy': 'accuracy', 'Missrate': 'mistake rate'}[m]
    g, _, rest = name.partition('_')
    if g in NICE:
        return f'{NICE[g]}: {SUFFIX.get(rest, rest)}'
    return name.replace('_', ' ')


def bundle_quick():
    global _bq
    if _bq is None:
        _bq = joblib.load(os.path.join(ART, 'game_quick_model.joblib'))
    return _bq


def vector(row, device_tablet=0.0):
    b = bundle(); f = dict(row); f.update(engineered(row)); f['device_tablet'] = device_tablet
    return np.array([[float(f[c]) for c in b['features']]], np.float32)


def score(x, b=None):
    b = b or bundle()
    import xgboost as xgb
    z_x = float(b['xgb'].predict(xgb.DMatrix(x), output_margin=True)[0])
    p_e = float(np.clip(forest_predict(b['et_c'], x)[0], 1e-4, 1 - 1e-4))
    z = 0.5 * z_x + 0.5 * np.log(p_e / (1 - p_e))
    a, c = b['platt']
    p = float(1 / (1 + np.exp(-(a * z + c))))
    contrib = b['xgb'].predict(xgb.DMatrix(x), pred_contribs=True)[0][:-1]
    order = np.argsort(-np.abs(contrib))[:8]
    reasons = [{'feature': b['features'][i], 'label': label_of(b['features'][i]), 'effect': float(contrib[i])} for i in order]
    return p, reasons


def result(p, reasons, extra=None):
    refer = p >= CUTOFF
    label = 'High risk: refer for assessment' if p >= 0.3 else ('At risk: refer for assessment' if refer else 'Low risk')
    out = {'risk': p, 'refer': bool(refer), 'cutoff': CUTOFF, 'label': label, 'reasons': reasons,
           'model': 'XGBoost + Extra Trees ensemble (calibrated)'}
    if extra:
        out.update(extra)
    return out


def predict_from_items(child, items, seconds=12):
    row = items_to_row(items, child.age, child.gender, child.native_speaker, child.other_language, seconds)
    short = {int(i['q']) for i in items} <= set(QUICK)
    if short:                                   # short form: 10 exercises, its own trained model
        bq = bundle_quick(); f = quick_features(row); f['device_tablet'] = 0.0
        p, reasons = score(np.array([[float(f[c]) for c in bq['features']]], np.float32), bq)
    else:
        p, reasons = score(vector(row))
    tot_c = sum(i['clicks'] for i in items); tot_h = sum(i['hits'] for i in items)
    summary = {'exercises': len(items), 'correct': int(tot_h), 'clicks': int(tot_c),
               'accuracy': f"{100 * tot_h / tot_c:.0f}%" if tot_c else '–'}
    return result(p, reasons, {'summary': summary, 'form': 'short (10 exercises)' if short else 'full (32 exercises)',
                               'model': 'XGBoost + Extra Trees ensemble (calibrated)' + (', short form' if short else '')})


def dataset_sample(dyslexia=None):
    b = bundle(); T = b['test_records']
    idx = [i for i, r in enumerate(T) if dyslexia is None or r['y'] == int(dyslexia)]
    i = int(np.random.choice(idx)); r = T[i]
    p, reasons = score(vector(r['row'], r.get('device_tablet', 0.0)))
    tot_c = sum(r['row'][f'Clicks{q}'] for q in range(1, 33)); tot_h = sum(r['row'][f'Hits{q}'] for q in range(1, 33))
    return result(p, reasons, {'truth': r['y'], 'record': r['id'], 'age': int(r['row']['Age']),
                               'gender': 'male' if r['row']['Gender'] == 1 else 'female',
                               'summary': {'exercises': 32, 'correct': int(tot_h), 'clicks': int(tot_c),
                                           'accuracy': f"{100 * tot_h / tot_c:.0f}%" if tot_c else '–'}})
