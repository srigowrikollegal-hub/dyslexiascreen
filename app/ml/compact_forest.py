"""Compact copy of a trained Extra Trees model (median imputer + forest) for the server.
Same predictions as scikit-learn, about a quarter of the memory, so the free 512 MB
server can hold both game models at once."""
import numpy as np


def compact(pipe):
    imp, forest = pipe[0], pipe[-1]
    L, R, F, T, P, roots = [], [], [], [], [], []
    off = 0
    for est in forest.estimators_:
        t = est.tree_
        v = t.value[:, 0, :]; p = (v[:, 1] / np.maximum(v.sum(1), 1e-12)).astype(np.float32)
        left, right = t.children_left.astype(np.int32), t.children_right.astype(np.int32)
        leaf = left < 0
        L.append(np.where(leaf, -1, left + off)); R.append(np.where(leaf, -1, right + off))
        F.append(np.where(leaf, 0, t.feature).astype(np.int32)); T.append(t.threshold.astype(np.float64)); P.append(p)
        roots.append(off); off += t.node_count
    return {'medians': imp.statistics_.astype(np.float64), 'left': np.concatenate(L), 'right': np.concatenate(R),
            'feature': np.concatenate(F), 'threshold': np.concatenate(T), 'p': np.concatenate(P), 'roots': np.array(roots, np.int32)}


def predict(cf, X):
    """Probability of the positive class for each row of X (same as pipeline.predict_proba(X)[:, 1])."""
    X = np.asarray(X, np.float64)
    out = np.empty(len(X))
    for r, x in enumerate(X):
        x = np.where(np.isnan(x), cf['medians'], x).astype(np.float32).astype(np.float64)
        idx = cf['roots'].copy()
        while True:
            lf = cf['left'][idx]; inner = lf >= 0
            if not inner.any():
                break
            i = idx[inner]
            go_left = x[cf['feature'][i]] <= cf['threshold'][i]
            idx[inner] = np.where(go_left, cf['left'][i], cf['right'][i])
        out[r] = cf['p'][idx].mean()
    return out
