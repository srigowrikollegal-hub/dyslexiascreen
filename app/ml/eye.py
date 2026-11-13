"""Eye-tracking module: turns raw webcam gaze samples into fixations,
saccades, regressions and word-level reading measures, then scores them with
the logistic model trained on ETDD70 degraded to webcam quality
(see training/eye_webcam_sim.py)."""
import os
import numpy as np, joblib

ART = os.path.join(os.path.dirname(__file__), '..', '..', 'artifacts')
_bundle = None
TASKS = {'syllables': 'Syl', 'passage': 'Mean', 'pseudo': 'Pseudo'}


def bundle():
    global _bundle
    if _bundle is None:
        _bundle = joblib.load(os.path.join(ART, 'eye_webcam_model.joblib'))
    return _bundle


def fixations_idt(samples, max_disp=90.0, min_dur=100.0):
    """Dispersion-threshold identification (I-DT). samples: list of (t_ms, x, y)."""
    s = np.asarray(samples, float)
    if len(s) < 3:
        return []
    fx, i, n = [], 0, len(s)
    while i < n:
        j = i
        while j + 1 < n and s[j + 1, 0] - s[i, 0] < min_dur:
            j += 1
        if j + 1 >= n:
            break
        win = s[i:j + 1]
        if (np.ptp(win[:, 1]) + np.ptp(win[:, 2])) <= max_disp:
            while j + 1 < n:
                w2 = s[i:j + 2]
                if (np.ptp(w2[:, 1]) + np.ptp(w2[:, 2])) > max_disp:
                    break
                j += 1
            w = s[i:j + 1]
            fx.append({'start': float(w[0, 0]), 'dur': float(w[-1, 0] - w[0, 0]),
                       'x': float(w[:, 1].mean()), 'y': float(w[:, 2].mean())})
            i = j + 1
        else:
            i += 1
    return fx


def assign_aoi(fx, boxes, ytol=45.0, xtol=25.0):
    """Index of the word box a fixation falls on (nearest box within tolerance), else -1."""
    best, bd = -1, 1e9
    for k, b in enumerate(boxes):
        dx = max(b['x'] - fx['x'], 0, fx['x'] - (b['x'] + b['w']))
        dy = max(b['y'] - fx['y'], 0, fx['y'] - (b['y'] + b['h']))
        if dx <= xtol and dy <= ytol:
            d = dx + 2 * dy
            if d < bd:
                bd, best = d, k
    return best


def task_measures(samples, boxes):
    fx = fixations_idt(samples)
    nA = max(len(boxes), 1)
    for f in fx:
        f['aoi'] = assign_aoi(f, boxes)
    dwell = np.zeros(nA); nfix = np.zeros(nA); first = np.full(nA, np.nan); visits = np.zeros(nA)
    reread = np.zeros(nA); first_pass_done = np.zeros(nA, bool); maxseen = -1; prev = None
    n_reg = n_prog = 0
    for f in fx:
        a = f['aoi']
        if a >= 0:
            dwell[a] += f['dur']; nfix[a] += 1
            if np.isnan(first[a]):
                first[a] = f['dur']
            if a != prev:
                visits[a] += 1
            if a < maxseen:
                reread[a] += f['dur']
            maxseen = max(maxseen, a)
        if prev is not None and a >= 0 and prev >= 0 and a != prev:
            if a < prev:
                n_reg += 1
            else:
                n_prog += 1
        if a >= 0:
            prev = a
    durs = np.array([f['dur'] for f in fx]) if fx else np.array([0.0])
    skipped = (nfix == 0).mean() if nA else 0
    m = {
        'aoi_dwell_mean': float(dwell.mean()), 'aoi_nfix_mean': float(nfix.mean()), 'aoi_skip_rate': float(skipped),
        'aoi_first_fix_dur_mean': float(np.nanmean(first)) if np.isfinite(first).any() else 0.0,
        'aoi_revisits_mean': float(np.maximum(visits - 1, 0).mean()), 'aoi_reread_mean': float(reread.mean()),
        'mean_fix_dur': float(durs.mean()), 'fix_dur_median': float(np.median(durs)),
        'ratio_progress_regress': float(n_prog / max(n_reg, 1)), 'regress_per_fix': float(n_reg / max(len(fx), 1)),
    }
    summary = {'fixations': len(fx), 'regressions': n_reg, 'progressions': n_prog,
               'reading_time_ms': float(samples[-1][0] - samples[0][0]) if len(samples) > 1 else 0.0,
               'words': nA, 'words_fixated': int((nfix > 0).sum())}
    return m, summary, fx


def analyse(tasks):
    """tasks: {'syllables'|'passage'|'pseudo': {'samples': [[t,x,y],...], 'boxes': [...]}}"""
    b = bundle(); feats = dict(b['feature_means'])
    out = {}
    for key, tag in TASKS.items():
        if key not in tasks:
            continue
        m, summ, fx = task_measures(tasks[key]['samples'], tasks[key]['boxes'])
        m['time_per_word'] = summ['reading_time_ms'] / max(summ['words'], 1)   # reading speed (ms per word)
        for k, v in m.items():
            feats[f'{tag}_{k}'] = v
        out[key] = {'measures': m, 'summary': summ,
                    'fixations': [{k: round(v, 1) if isinstance(v, float) else v for k, v in f.items()} for f in fx]}
    x = np.array([[feats[c] for c in b['features']]])
    p = float(b['model'].predict_proba(x)[0, 1])
    # contribution of each measure in the logistic model (log-odds, before calibration)
    base = b['model'].calibrated_classifiers_[0].estimator
    scaler, lr = base[0], base[-1]
    z = scaler.transform(x)[0]; contrib = lr.coef_[0] * z
    order = np.argsort(-np.abs(contrib))[:6]
    reasons = [{'feature': b['features'][i], 'effect': float(contrib[i])} for i in order]
    return {'risk': p, 'tasks': out, 'reasons': reasons}
