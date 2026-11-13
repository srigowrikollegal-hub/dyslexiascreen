"""Replaces the scikit-learn Extra Trees inside the game model files with the compact
copy used by the server (checks that predictions are unchanged first)."""
import os, sys, joblib, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, ROOT)
from app.ml.compact_forest import compact, predict
for name in ['game_model.joblib', 'game_quick_model.joblib']:
    p = f'{ROOT}/artifacts/{name}'; b = joblib.load(p)
    if 'et' not in b:
        print(name, 'already compact'); continue
    cf = compact(b['et'])
    X = np.random.default_rng(0).normal(0, 3, (300, len(b['features']))).astype(np.float32)
    if 'test_records' in b:
        sys.path.insert(0, f'{ROOT}/training'); from game_features import engineered
        rows = []
        for r in b['test_records'][:200]:
            f = dict(r['row']); f.update(engineered(r['row'])); f['device_tablet'] = 0.0
            rows.append([f[c] for c in b['features']])
        X = np.array(rows, np.float32)
    d = np.abs(predict(cf, X) - b['et'].predict_proba(X)[:, 1]).max()
    print(name, 'max difference', d); assert d < 1e-6
    b['et_c'] = cf; del b['et']; joblib.dump(b, p, compress=3)
print('done')
