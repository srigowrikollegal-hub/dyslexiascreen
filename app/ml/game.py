"""Gamified-test module: XGBoost + Extra Trees ensemble averaged on the
log-odds scale, Platt calibration, and TreeSHAP reasons from the XGBoost member."""
import os, sys, json
import numpy as np, joblib

ART = os.path.join(os.path.dirname(__file__), '..', '..', 'artifacts')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'training'))
from game_features import engineered, items_to_row, RAW  # noqa: E402

_b = None
CUTOFF = 0.11
NICE = {'letters': 'letter sounds', 'syllables': 'syllables', 'words': 'words', 'visual': 'visual search', 'pseudo': 'made-up words',
        'spelling': 'spelling', 'building': 'word building', 'memory': 'memory', 'dictation': 'dictation'}


def bundle():
    global _b
    if _b is None:
        _b = joblib.load(os.path.join(ART, 'game_model.joblib'))
    return _b


def label_of(name):
    if name in ('Gender', 'Nativelang', 'Otherlang', 'Age', 'device_tablet'):
        return {'Gender': 'gender', 'Nativelang': 'tested in first language', 'Otherlang': 'speaks another language',
                'Age': 'age', 'device_tablet': 'device'}[name]
    for m in ['Clicks', 'Hits', 'Misses', 'Score', 'Accuracy', 'Missrate']:
        if name.startswith(m) and name[len(m):].isdigit():
            return f'exercise {name[len(m):]}: {m.lower().replace("missrate", "miss rate")}'
    g = name.split('_')[0]
    if g in NICE:
        return f'{NICE[g]}: ' + {'acc': 'accuracy', 'miss': 'miss rate', 'hits': 'correct answers'}.get(name.split('_', 1)[1], name.split('_', 1)[1])
    return name.replace('_', ' ')


def vector(row, device_tablet=0.0):
    b = bundle(); f = dict(row); f.update(engineered(row)); f['device_tablet'] = device_tablet
    return np.array([[float(f[c]) for c in b['features']]], np.float32)


def score(x):
    b = bundle()
    import xgboost as xgb
    z_x = float(b['xgb'].predict(xgb.DMatrix(x), output_margin=True)[0])
    p_e = float(np.clip(b['et'].predict_proba(x)[0, 1], 1e-4, 1 - 1e-4))
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


def predict_from_items(child, items):
    row = items_to_row(items, child.age, child.gender, child.native_speaker, child.other_language)
    p, reasons = score(vector(row))
    tot_c = sum(i['clicks'] for i in items); tot_h = sum(i['hits'] for i in items)
    summary = {'exercises': len(items), 'correct': int(tot_h), 'clicks': int(tot_c),
               'accuracy': f"{100 * tot_h / tot_c:.0f}%" if tot_c else '–'}
    return result(p, reasons, {'summary': summary})


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
