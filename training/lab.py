"""Shared evaluation helpers for the Model Lab: repeated stratified k-fold
cross-validation with identical splits for every algorithm."""
import numpy as np
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (roc_auc_score, accuracy_score, precision_score, recall_score, f1_score,
                             confusion_matrix, roc_curve, average_precision_score)


def cv_probs(make, X, y, repeats=5, folds=5, seed=0):
    P = np.zeros((repeats, len(y)))
    for r in range(repeats):
        for tr, te in StratifiedKFold(folds, shuffle=True, random_state=seed + r).split(X, y):
            m = make().fit(X[tr], y[tr])
            P[r, te] = m.predict_proba(X[te])[:, 1]
    return P


def metrics_from_probs(P, y, thr=0.5):
    out = {k: [] for k in ['accuracy', 'roc_auc', 'precision', 'recall', 'f1', 'specificity', 'avg_precision']}
    for p in P:
        q = (p >= thr).astype(int)
        tn, fp, fn, tp = confusion_matrix(y, q, labels=[0, 1]).ravel()
        out['accuracy'].append(accuracy_score(y, q)); out['roc_auc'].append(roc_auc_score(y, p))
        out['precision'].append(precision_score(y, q, zero_division=0)); out['recall'].append(recall_score(y, q))
        out['f1'].append(f1_score(y, q, zero_division=0)); out['specificity'].append(tn / (tn + fp))
        out['avg_precision'].append(average_precision_score(y, p))
    res = {k: float(np.mean(v)) for k, v in out.items()}
    res.update({k + '_sd': float(np.std(v)) for k, v in out.items()})
    pm = P.mean(0)
    f, t, _ = roc_curve(y, pm)
    idx = np.unique(np.linspace(0, len(f) - 1, min(len(f), 60)).astype(int))
    res['roc'] = {'fpr': [round(float(x), 4) for x in f[idx]], 'tpr': [round(float(x), 4) for x in t[idx]]}
    res['confusion'] = confusion_matrix(y, (pm >= thr).astype(int), labels=[0, 1]).tolist()
    res['threshold'] = thr
    return res
