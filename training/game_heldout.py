"""Screening performance of the deployed game model on the held-out 20% of desktop children
(never used for training), at the referral cut-off used by the app and at 0.5."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.ml import game

b = game.bundle(); T = b['test_records']
p = np.array([game.score(game.vector(r['row']))[0] for r in T]); y = np.array([r['y'] for r in T])
out = {'n': int(len(y)), 'n_dyslexia': int(y.sum()), 'cutoffs': {}}
for c in (game.CUTOFF, 0.5):
    pr = p >= c
    tp, tn = int((pr & (y == 1)).sum()), int((~pr & (y == 0)).sum())
    fp, fn = int((pr & (y == 0)).sum()), int((~pr & (y == 1)).sum())
    out['cutoffs'][f'{c:g}'] = dict(sensitivity=tp / (tp + fn), specificity=tn / (tn + fp), accuracy=(tp + tn) / len(y),
                                    confusion=[[tn, fp], [fn, tp]])
from sklearn.metrics import roc_auc_score
out['roc_auc'] = float(roc_auc_score(y, p))
json.dump(out, open(os.path.join(os.path.dirname(game.__file__), '..', '..', 'artifacts', 'game_heldout.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
