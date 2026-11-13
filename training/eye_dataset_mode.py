"""Eye-tracking Dataset mode: real ETDD70 recordings (fixations on the original
stimuli) with each child's out-of-fold risk from the proposed ensemble, i.e. a
prediction made by a model that never saw that child."""
import os, sys, json, glob, shutil, warnings
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from sklearn.model_selection import StratifiedKFold
warnings.filterwarnings('ignore')
import eye_train  # noqa: reuses the feature table and the proposed model definition (runs its Model Lab too)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ET, OUTIMG = sys.argv[1], os.path.join(ROOT, 'static', 'img', 'etdd')
os.makedirs(OUTIMG, exist_ok=True)
F = eye_train.F; y = eye_train.y; X = eye_train.X
P = np.zeros(len(y))
for tr, te in StratifiedKFold(5, shuffle=True, random_state=2026).split(X, y):
    P[te] = eye_train.hetero_ensemble().fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
TASKS = [('T1_Syllables', 's7_stimuli_t1.jpg', 'Syllables'), ('T4_Meaningful_Text', 's7_stimuli_t4.jpg', 'Story'),
         ('T5_Pseudo_Text', 's7_stimuli_t5.jpg', 'Made-up words')]
for _, img, _ in TASKS:
    shutil.copy(os.path.join(ET, 'stim', 'images', img), os.path.join(OUTIMG, img))
kids = []
for i, sid in enumerate(F.sid.values):
    rec = {'sid': int(sid), 'y': int(y[i]), 'risk': float(P[i]), 'tasks': []}
    for t, img, name in TASKS:
        fx = pd.read_csv(os.path.join(ET, 'raw', 'data', f'Subject_{sid}_{t}_fixations.csv'))
        fx = fx[fx.eye.isin(['b', 'R', 'r', 'L', 'l'])] if 'eye' in fx else fx
        rec['tasks'].append({'name': name, 'img': f'/img/etdd/{img}', 'w': 1680, 'h': 1050,
                             'fix': [[round(float(a), 1), round(float(b), 1), int(c)] for a, b, c in
                                     zip(fx.orig_fix_x, fx.orig_fix_y, fx.duration_ms)],
                             'reading_s': round(float((fx.end_ms.max() - fx.start_ms.min()) / 1000), 1)})
    kids.append(rec)
acc = float(((P >= 0.5) == y).mean())
json.dump({'children': kids, 'oof_accuracy': acc}, open(os.path.join(ROOT, 'artifacts', 'etdd_samples.json'), 'w'))
print('saved', len(kids), 'children; out-of-fold accuracy', round(acc, 3))
