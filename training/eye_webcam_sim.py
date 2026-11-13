"""Webcam-quality training data for the live eye-tracking model.

The live app gets gaze from a laptop webcam (WebGazer): about 30 samples a second,
a calibration offset, slow drift and jitter. ETDD70 was recorded with a 250 Hz
research eye tracker. To make training match the live app, each ETDD70 recording
is degraded to webcam quality and passed through exactly the same code the server
runs live (I-DT fixations, word boxes, reading measures in app/ml/eye.py).

1) Word boxes are found on the three ETDD70 stimulus images (dark text, joined
   letters, connected components).
2) Each child's fixations become a 30 Hz gaze stream; noise is added
   (offset, drift, jitter) and smoothed like WebGazer's Kalman filter.
3) Features: the 10 reading measures per task plus reading time per word.
4) Logistic regression with Platt calibration; evaluated with children (not
   noise draws) as the unit, 10 x 5-fold cross-validation."""
import os, sys, json, glob
import numpy as np, pandas as pd, joblib
from PIL import Image
from scipy import ndimage
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.dirname(__file__))
from app.ml.eye import task_measures
from lab import metrics_from_probs
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold

ET = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/etdd'
TASKS = {'T1_Syllables': ('Syl', 's7_stimuli_t1.jpg'), 'T4_Meaningful_Text': ('Mean', 's7_stimuli_t4.jpg'),
         'T5_Pseudo_Text': ('Pseudo', 's7_stimuli_t5.jpg')}
MEAS = ['aoi_dwell_mean', 'aoi_nfix_mean', 'aoi_skip_rate', 'aoi_first_fix_dur_mean', 'aoi_revisits_mean',
        'aoi_reread_mean', 'mean_fix_dur', 'fix_dur_median', 'ratio_progress_regress', 'regress_per_fix', 'time_per_word']
DRAWS = 6


def word_boxes(path):
    g = np.asarray(Image.open(path).convert('L'), float)
    ink = g < 110
    lab, n = ndimage.label(ndimage.binary_dilation(ink, structure=np.ones((5, 15))))
    boxes = []
    for sl in ndimage.find_objects(lab):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if h >= 12 and w >= 12 and h < 200:
            boxes.append({'x': sl[1].start, 'y': sl[0].start, 'w': w, 'h': h})
    ys = np.array([b['y'] + b['h'] / 2 for b in boxes]); order = np.argsort(ys)
    line, lines, last = 0, [], None
    for i in order:                                # group into lines, then read left to right
        if last is not None and ys[i] - last > 25:
            line += 1
        boxes[i]['line'] = line; last = ys[i]
    return sorted(boxes, key=lambda b: (b['line'], b['x']))


def gaze_stream(fx, rng, hz=30):
    """Fixations -> 30 Hz webcam-like gaze samples (t, x, y)."""
    t = np.arange(fx.start_ms.iloc[0], fx.end_ms.iloc[-1], 1000 / hz)
    st, en = fx.start_ms.values, fx.end_ms.values; xs, ys = fx.orig_fix_x.values, fx.orig_fix_y.values
    k = np.clip(np.searchsorted(st, t, side='right') - 1, 0, len(st) - 1)
    inside = t <= en[k]
    nxt = np.clip(k + 1, 0, len(st) - 1)
    a = np.where(inside, 0.0, np.clip((t - en[k]) / np.maximum(st[nxt] - en[k], 1), 0, 1))
    x = xs[k] + a * (xs[nxt] - xs[k]); y = ys[k] + a * (ys[nxt] - ys[k])
    n = len(t)
    off = rng.normal(0, 45, 2)                                           # calibration offset
    drift = np.zeros((n, 2)); e = rng.normal(0, 30 * np.sqrt(1 - .97 ** 2), (n, 2))
    for i in range(1, n):
        drift[i] = .97 * drift[i - 1] + e[i]                             # slow drift
    jit = rng.normal(0, 45, (n, 2))                                      # frame-to-frame jitter
    g = np.c_[x, y] + off + drift + jit
    for i in range(1, n):
        g[i] = g[i - 1] + 0.45 * (g[i] - g[i - 1])                       # smoothing like WebGazer's Kalman filter
    return [[float(tt - t[0]), float(px), float(py)] for tt, (px, py) in zip(t, g)]


def features(samples, boxes):
    m, s, _ = task_measures(samples, boxes)
    m['time_per_word'] = s['reading_time_ms'] / max(len(boxes), 1)
    return m


if __name__ == '__main__':
    lab = pd.read_csv(f'{ET}/dyslexia_class_label.csv').set_index('subject_id')['class_id']
    BOX = {k: word_boxes(f'{ET}/stim/images/{img}') for k, (_, img) in TASKS.items()}
    for k, b in BOX.items():
        print(k, 'word boxes', len(b), 'lines', b[-1]['line'] + 1, 'median h', int(np.median([q['h'] for q in b])))
    rng = np.random.default_rng(2026)
    rows = []
    for sid in lab.index:
        F = {}
        for k in TASKS:
            p = glob.glob(f'{ET}/raw/data/Subject_{sid}_{k}_fixations.csv')
            if p:
                d = pd.read_csv(p[0]); d = d[d.eye == 'b'] if 'b' in set(d.eye) else d
                F[k] = d.sort_values('start_ms').reset_index(drop=True)
        if len(F) < 3:
            continue
        for r in range(DRAWS):
            row = {'sid': sid, 'y': int(lab[sid]), 'draw': r}
            for k, (tag, _) in TASKS.items():
                for c, v in features(gaze_stream(F[k], rng), BOX[k]).items():
                    row[f'{tag}_{c}'] = v
            rows.append(row)
    D = pd.DataFrame(rows); COLS = [c for c in D.columns if c not in ('sid', 'y', 'draw')]
    print('children', D.sid.nunique(), 'rows', len(D), 'features', len(COLS))
    make = lambda: CalibratedClassifierCV(make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000)),
                                          method='sigmoid', ensemble=False, cv=StratifiedKFold(5, shuffle=True, random_state=7))
    kids = D.groupby('sid').y.first(); S, Y = kids.index.values, kids.values
    P = np.zeros((10, len(S)))
    for rep in range(10):                                             # children are the unit of evaluation
        for tr, te in StratifiedKFold(5, shuffle=True, random_state=rep).split(S, Y):
            m = make().fit(D[D.sid.isin(S[tr])][COLS].values, D[D.sid.isin(S[tr])].y.values)
            one = D[D.sid.isin(S[te]) & (D.draw == rep % DRAWS)].set_index('sid').loc[S[te]]
            P[rep, te] = m.predict_proba(one[COLS].values)[:, 1]
    res = metrics_from_probs(P, Y)
    print('webcam-simulated model: acc', round(res['accuracy'], 3), 'auc', round(res['roc_auc'], 3), 'f1', round(res['f1'], 3))
    final = make().fit(D[COLS].values, D.y.values)
    means = D[D.y == 0][COLS].mean().to_dict()                      # missing task -> typical reader's value
    joblib.dump({'model': final, 'features': COLS, 'feature_means': means, 'trained_on': 'ETDD70 degraded to webcam quality'},
                f'{ROOT}/artifacts/eye_webcam_model.joblib')
    L = json.load(open(f'{ROOT}/artifacts/lab_eye.json'))
    L['webcam_model'] = {**res, 'n_features': len(COLS), 'features': COLS,
                         'note': 'ETDD70 degraded to webcam quality (30 Hz, offset, drift, jitter, smoothing), same feature code as the live app'}
    json.dump(L, open(f'{ROOT}/artifacts/lab_eye.json', 'w'), indent=1)
    print('typical vs dyslexic medians:')
    print(D.groupby('y')[[f'{t}_time_per_word' for t in ('Syl', 'Mean', 'Pseudo')] + ['Mean_regress_per_fix', 'Mean_mean_fix_dur']].median().round(2))
