"""Eye-tracking module training (ETDD70, 70 children).
1) Model Lab: 12 algorithms on the 84 gaze measures, identical repeated CV splits.
2) Webcam-ready model: logistic regression on per-word and ratio measures that
   do not depend on text length, so they can be computed from any passage."""
import json, sys, os, warnings
import numpy as np, pandas as pd, joblib
sys.path.insert(0, os.path.dirname(__file__))
from lab import cv_probs, metrics_from_probs
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (RandomForestClassifier, ExtraTreesClassifier, AdaBoostClassifier,
                              GradientBoostingClassifier, VotingClassifier)
from sklearn.neural_network import MLPClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
warnings.filterwarnings('ignore')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = pd.read_csv(f'{ROOT}/data/et_features.csv')
y = F.y.values
ALL = [c for c in F.columns if c not in ('sid', 'y')]
X = F[ALL].values.astype(float)
sc = lambda m: (lambda: make_pipeline(StandardScaler(), m()))
cal = lambda base: (lambda: CalibratedClassifierCV(base(), method='sigmoid', ensemble=False, cv=StratifiedKFold(5, shuffle=True, random_state=7)))
def hetero_ensemble():
    """Proposed: soft-voting ensemble of five different learners, then Platt calibration."""
    return VotingClassifier([
        ('lr', make_pipeline(StandardScaler(), LogisticRegression(C=0.1, max_iter=5000))),
        ('svm', make_pipeline(StandardScaler(), SVC(C=1.0, gamma='scale', probability=True, random_state=0))),
        ('knn', make_pipeline(StandardScaler(), KNeighborsClassifier(7))),
        ('mlp', make_pipeline(StandardScaler(), MLPClassifier((32,), alpha=1.0, max_iter=3000, random_state=0))),
        ('et', ExtraTreesClassifier(300, min_samples_leaf=2, random_state=0, n_jobs=2))], voting='soft')


MODELS = {
    'Heterogeneous ensemble (proposed)': lambda: hetero_ensemble(),
    'Logistic Regression': cal(sc(lambda: LogisticRegression(C=0.1, max_iter=5000))),
    'Support Vector Machine': cal(sc(lambda: SVC(C=1.0, gamma='scale'))),
    'Random Forest': lambda: RandomForestClassifier(300, min_samples_leaf=2, random_state=0, n_jobs=2),
    'Extra Trees': lambda: ExtraTreesClassifier(300, min_samples_leaf=2, random_state=0, n_jobs=2),
    'XGBoost': lambda: XGBClassifier(n_estimators=300, max_depth=2, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, n_jobs=2, verbosity=0),
    'LightGBM': lambda: LGBMClassifier(n_estimators=200, num_leaves=7, learning_rate=0.05, min_child_samples=5, verbose=-1),
    'Gradient Boosting': lambda: GradientBoostingClassifier(n_estimators=150, max_depth=2, random_state=0),
    'AdaBoost': lambda: AdaBoostClassifier(n_estimators=150, random_state=0),
    'K-Nearest Neighbours': sc(lambda: KNeighborsClassifier(7)),
    'Naive Bayes': sc(lambda: GaussianNB()),
    'Decision Tree': lambda: DecisionTreeClassifier(max_depth=4, random_state=0),
    'Multilayer Perceptron': sc(lambda: MLPClassifier((32,), alpha=1.0, max_iter=3000, random_state=0)),
}
lab = {}
for name, make in MODELS.items():
    P = cv_probs(make, X, y, repeats=10)
    lab[name] = metrics_from_probs(P, y)
    print(f"{name:42s} acc {lab[name]['accuracy']:.3f} auc {lab[name]['roc_auc']:.3f} f1 {lab[name]['f1']:.3f}", flush=True)

# ---------------------------------------------------------------- webcam-ready model
def webcam_feats(df):
    out = pd.DataFrame(index=df.index)
    for t in ['Syl', 'Mean', 'Pseudo']:
        for c in ['aoi_dwell_mean', 'aoi_nfix_mean', 'aoi_skip_rate', 'aoi_first_fix_dur_mean', 'aoi_revisits_mean',
                  'aoi_reread_mean', 'mean_fix_dur', 'fix_dur_median', 'ratio_progress_regress']:
            out[f'{t}_{c}'] = df[f'{t}_{c}']
        out[f'{t}_regress_per_fix'] = df[f'{t}_n_regress'] / df[f'{t}_n_fix']
    return out
W = webcam_feats(F); WCOLS = list(W.columns)
make_w = cal(sc(lambda: LogisticRegression(C=0.1, max_iter=5000)))
Pw = cv_probs(make_w, W.values, y, repeats=10)
web = metrics_from_probs(Pw, y)
print('webcam-ready model', round(web['accuracy'], 3), round(web['roc_auc'], 3))
final = make_w().fit(W.values, y)
os.makedirs(f'{ROOT}/artifacts', exist_ok=True)
joblib.dump({'model': final, 'features': WCOLS, 'feature_means': W.mean().to_dict()}, f'{ROOT}/artifacts/eye_webcam_model.joblib')
json.dump({'dataset': 'ETDD70 (70 children, 35 with dyslexia)', 'cv': '10 x stratified 5-fold',
           'n_features': len(ALL), 'models': lab, 'webcam_model': {**web, 'n_features': len(WCOLS), 'features': WCOLS}},
          open(f'{ROOT}/artifacts/lab_eye.json', 'w'), indent=1)
