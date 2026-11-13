"""Short form of the gamified test (10 of the 32 exercises, about 2 minutes).
Same recipe as the full model (XGBoost + Extra Trees, log-odds average, Platt scaling),
same 5-fold splits and the same held-out 20% of desktop children."""
import os, sys, json, warnings
import numpy as np, pandas as pd, joblib
sys.path.insert(0, os.path.dirname(__file__))
from game_features import RAW, QUICK, quick_features
from lab import metrics_from_probs
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
import xgboost as xgb
warnings.filterwarnings('ignore')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(p, dev):
    d = pd.read_csv(p, sep=None, engine='python'); d.columns = [c.strip() for c in d.columns]
    yn = lambda s: s.astype(str).str.strip().str.lower().map({'yes': 1, 'no': 0, '1': 1, '0': 0})
    d['Gender'] = d['Gender'].astype(str).str.strip().str.lower().map({'male': 1, 'female': 0, '1': 1, '2': 0, '0': 0})
    d['Nativelang'] = yn(d['Nativelang']); d['Otherlang'] = yn(d['Otherlang']); d['y'] = yn(d['Dyslexia'])
    for c in RAW:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['y']).reset_index(drop=True)
    X = pd.DataFrame([quick_features(r) for r in d[RAW].to_dict('records')]); X['device_tablet'] = dev
    return X, d['y'].astype(int).values


Xd, yd = load(sys.argv[1], 0.0); Xt, yt = load(sys.argv[2], 1.0)
FEATS = list(Xd.columns); XD, XT = Xd.values.astype(np.float32), Xt.values.astype(np.float32)
print('features', len(FEATS), flush=True)
XGBP = dict(n_estimators=800, max_depth=6, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=float((yd == 0).sum() / (yd == 1).sum()), eval_metric='logloss', n_jobs=2, verbosity=0)


def fit_ens(X, y):
    return (xgb.XGBClassifier(**XGBP).fit(X, y),
            make_pipeline(SimpleImputer(strategy='median'), ExtraTreesClassifier(500, min_samples_leaf=2, class_weight='balanced_subsample', n_jobs=2, random_state=0)).fit(X, y))


def margin(xg, et, X):
    pe = np.clip(et.predict_proba(X)[:, 1], 1e-4, 1 - 1e-4)
    return 0.5 * xg.predict(X, output_margin=True) + 0.5 * np.log(pe / (1 - pe))


def fit(X, y):
    z = np.zeros(len(y))
    for a, b in StratifiedKFold(3, shuffle=True, random_state=0).split(X, y):
        z[b] = margin(*fit_ens(X[a], y[a]), X[b])
    lr = LogisticRegression(C=1e6).fit(z[:, None], y); xg, et = fit_ens(X, y)
    return xg, et, (float(lr.coef_[0, 0]), float(lr.intercept_[0]))


def proba(m, X):
    xg, et, (a, c) = m
    return 1 / (1 + np.exp(-(a * margin(xg, et, X) + c)))


P = np.zeros(len(yd))
for tr, te in StratifiedKFold(5, shuffle=True, random_state=42).split(XD, yd):
    P[te] = proba(fit(np.vstack([XD[tr], XT]), np.r_[yd[tr], yt]), XD[te])
cv = metrics_from_probs(P[None, :], yd)
print('short form 5-fold CV: acc', round(cv['accuracy'], 3), 'auc', round(cv['roc_auc'], 3), flush=True)
idx = np.arange(len(yd)); itr, ite = train_test_split(idx, test_size=0.2, stratify=yd, random_state=7)
m = fit(np.vstack([XD[itr], XT]), np.r_[yd[itr], yt]); pte = proba(m, XD[ite])
c = 0.11; pr = pte >= c; yt_ = yd[ite]
held = {'n': int(len(ite)), 'roc_auc': float(roc_auc_score(yt_, pte)),
        'sensitivity': float((pr & (yt_ == 1)).sum() / (yt_ == 1).sum()), 'specificity': float((~pr & (yt_ == 0)).sum() / (yt_ == 0).sum())}
print('held-out', held, flush=True)
joblib.dump({'xgb': m[0].get_booster(), 'et': m[1], 'platt': m[2], 'features': FEATS, 'items': QUICK, 'heldout': held},
            f'{ROOT}/artifacts/game_quick_model.joblib', compress=3)
L = json.load(open(f'{ROOT}/artifacts/lab_game.json'))
L['short_form'] = {'items': QUICK, 'cv': {k: cv[k] for k in ('accuracy', 'roc_auc', 'precision', 'recall', 'f1', 'specificity')}, 'heldout': held}
json.dump(L, open(f'{ROOT}/artifacts/lab_game.json', 'w'), indent=1)
print('saved')
