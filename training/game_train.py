"""Gamified-test module (Dytective data).
Model Lab: 13 algorithms, stratified 5-fold CV on desktop children (tablet sessions
added to every training fold only). Deployed model: trained on 80% of desktop children
plus all tablet sessions; the other 20% are kept unseen for Dataset mode."""
import os, sys, json, warnings, time
import numpy as np, pandas as pd, joblib
sys.path.insert(0, os.path.dirname(__file__))
from game_features import RAW, engineered
from lab import metrics_from_probs
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, AdaBoostClassifier, GradientBoostingClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score
import xgboost as xgb
from lightgbm import LGBMClassifier
warnings.filterwarnings('ignore')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESK, TAB = sys.argv[1], sys.argv[2]


def load(p, dev):
    d = pd.read_csv(p, sep=None, engine='python')
    d.columns = [c.strip() for c in d.columns]
    yn = lambda s: s.astype(str).str.strip().str.lower().map({'yes': 1, 'no': 0, '1': 1, '0': 0})
    d['Gender'] = d['Gender'].astype(str).str.strip().str.lower().map({'male': 1, 'female': 0, '1': 1, '2': 0, '0': 0})
    d['Nativelang'] = yn(d['Nativelang']); d['Otherlang'] = yn(d['Otherlang']); d['y'] = yn(d['Dyslexia'])
    for c in RAW:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    d = d.dropna(subset=['y']).reset_index(drop=True)
    E = pd.DataFrame([engineered(r) for r in d[RAW].to_dict('records')])
    X = pd.concat([d[RAW], E], axis=1); X['device_tablet'] = dev
    return X, d['y'].astype(int).values


Xd, yd = load(DESK, 0.0); Xt, yt = load(TAB, 1.0)
FEATS = list(Xd.columns); print('desktop', Xd.shape, yd.mean().round(3), 'tablet', Xt.shape, yt.mean().round(3), flush=True)
XD, XT = Xd.values.astype(np.float32), Xt.values.astype(np.float32)
POS_W = float((yd == 0).sum() / (yd == 1).sum())
XGBP = dict(n_estimators=800, max_depth=6, learning_rate=0.03, subsample=0.8, colsample_bytree=0.8, scale_pos_weight=POS_W,
            eval_metric='logloss', n_jobs=2, verbosity=0)


def ens_margin(xg, et, X):
    zx = xg.predict(X, output_margin=True)
    pe = np.clip(et.predict_proba(X)[:, 1], 1e-4, 1 - 1e-4)
    return 0.5 * zx + 0.5 * np.log(pe / (1 - pe))


def fit_ensemble(X, y):
    xg = xgb.XGBClassifier(**XGBP).fit(X, y)
    et = make_pipeline(SimpleImputer(strategy='median'), ExtraTreesClassifier(500, min_samples_leaf=2, class_weight='balanced_subsample', n_jobs=2, random_state=0)).fit(X, y)
    return xg, et


def fit_platt(X, y, k=3, seed=0):
    z = np.zeros(len(y))
    for a, b in StratifiedKFold(k, shuffle=True, random_state=seed).split(X, y):
        xg, et = fit_ensemble(X[a], y[a]); z[b] = ens_margin(xg, et, X[b])
    lr = LogisticRegression(C=1e6).fit(z[:, None], y)
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


class Proposed:
    """XGBoost + Extra Trees, log-odds average, Platt scaling fitted inside the training data."""
    def fit(self, X, y):
        self.a, self.c = fit_platt(X, y); self.xg, self.et = fit_ensemble(X, y); return self

    def predict_proba(self, X):
        p = 1 / (1 + np.exp(-(self.a * ens_margin(self.xg, self.et, X) + self.c)))
        return np.c_[1 - p, p]


sc = lambda m: make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), m)
im = lambda m: make_pipeline(SimpleImputer(strategy='median'), m)
MODELS = {
    'XGBoost + Extra Trees ensemble (proposed)': lambda: Proposed(),
    'XGBoost': lambda: xgb.XGBClassifier(n_estimators=500, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_jobs=2, verbosity=0),
    'LightGBM': lambda: LGBMClassifier(n_estimators=400, learning_rate=0.03, num_leaves=31, subsample=0.8, colsample_bytree=0.8, verbose=-1),
    'Random Forest': lambda: im(RandomForestClassifier(500, min_samples_leaf=2, n_jobs=2, random_state=0)),
    'Extra Trees': lambda: im(ExtraTreesClassifier(500, min_samples_leaf=2, n_jobs=2, random_state=0)),
    'Gradient Boosting': lambda: im(GradientBoostingClassifier(n_estimators=300, max_depth=3, random_state=0)),
    'AdaBoost': lambda: im(AdaBoostClassifier(n_estimators=300, random_state=0)),
    'Support Vector Machine': lambda: sc(SVC(C=1.0, gamma='scale', probability=True, random_state=0)),
    'Logistic Regression': lambda: sc(LogisticRegression(C=0.1, max_iter=3000)),
    'Multilayer Perceptron': lambda: sc(MLPClassifier((64,), alpha=1e-2, max_iter=400, early_stopping=True, random_state=0)),
    'K-Nearest Neighbours': lambda: sc(KNeighborsClassifier(25)),
    'Naive Bayes': lambda: im(GaussianNB()),
    'Decision Tree': lambda: im(DecisionTreeClassifier(max_depth=6, min_samples_leaf=10, random_state=0)),
}
only = sys.argv[3].split(',') if len(sys.argv) > 3 else None
labp = f'{ROOT}/artifacts/lab_game.json'
lab = json.load(open(labp))['models'] if os.path.exists(labp) else {}
folds = list(StratifiedKFold(5, shuffle=True, random_state=42).split(XD, yd))
for name, mk in MODELS.items():
    if only and not any(o.lower() in name.lower() for o in only):
        continue
    t0 = time.time(); P = np.zeros(len(yd))
    for tr, te in folds:
        Xtr = np.vstack([XD[tr], XT]); ytr = np.r_[yd[tr], yt]
        P[te] = mk().fit(Xtr, ytr).predict_proba(XD[te])[:, 1]
    lab[name] = metrics_from_probs(P[None, :], yd); lab[name]['fit_min'] = round((time.time() - t0) / 60, 1)
    print(f"{name:44s} acc {lab[name]['accuracy']:.3f} auc {lab[name]['roc_auc']:.3f} f1 {lab[name]['f1']:.3f} ({lab[name]['fit_min']} min)", flush=True)
    json.dump({'dataset': f'Dytective gamified test: {len(yd):,} desktop children (+{len(yt):,} tablet sessions used in training only)',
               'cv': 'stratified 5-fold cross-validation', 'models': lab}, open(labp, 'w'), indent=1)

if not only or 'final' in only:
    idx = np.arange(len(yd)); itr, ite = train_test_split(idx, test_size=0.2, stratify=yd, random_state=7)
    Xtr = np.vstack([XD[itr], XT]); ytr = np.r_[yd[itr], yt]
    m = Proposed().fit(Xtr, ytr)
    pte = m.predict_proba(XD[ite])[:, 1]
    held = {'auc': float(roc_auc_score(yd[ite], pte)), 'acc_at_0.5': float(((pte >= 0.5) == yd[ite]).mean()),
            'n': int(len(ite))}
    print('held-out 20%', held, flush=True)
    recs = [{'id': int(i), 'y': int(yd[i]), 'row': {c: float(Xd.loc[i, c]) for c in RAW}} for i in ite]
    joblib.dump({'xgb': m.xg.get_booster(), 'et': m.et, 'platt': (m.a, m.c), 'features': FEATS, 'test_records': recs,
                 'heldout': held}, f'{ROOT}/artifacts/game_model.joblib', compress=3)
    print('saved model')
