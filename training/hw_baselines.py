"""Classical baselines for handwriting (HOG features), same official Train/Test split
as the CNN, and assembly of the handwriting Model Lab file."""
import os, sys, json, time
import numpy as np, pandas as pd
from skimage.feature import hog
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, roc_auc_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

D, ART = sys.argv[1], sys.argv[2]
X = np.load(f'{D}/hw_X32.npy'); M = pd.read_csv(f'{D}/hw_meta.csv'); y = M.y.values
nl = M.groupby('key').y.nunique(); conflict = set(nl[nl > 1].index)
tr = M[(M.split == 'Train') & ~M.key.isin(conflict)].drop_duplicates('key').index.values
te = M[M.split == 'Test'].index.values
rng = np.random.default_rng(0); tr_s = rng.choice(tr, min(40000, len(tr)), replace=False)
H = lambda ix: np.stack([hog(X[i], orientations=9, pixels_per_cell=(4, 4), cells_per_block=(2, 2)) for i in ix]).astype(np.float32)
t0 = time.time(); Htr, Hte = H(tr_s), H(te); print('hog', Htr.shape, round(time.time() - t0), 's', flush=True)
MODELS = {
    'Logistic Regression': lambda: make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=400)),
    'Linear SVM': lambda: make_pipeline(StandardScaler(), CalibratedClassifierCV(LinearSVC(C=0.05), cv=3)),
    'K-Nearest Neighbours': lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(7, n_jobs=2)),
    'Naive Bayes': lambda: GaussianNB(),
    'Decision Tree': lambda: DecisionTreeClassifier(max_depth=16, random_state=0),
    'Random Forest': lambda: RandomForestClassifier(300, n_jobs=2, random_state=0),
    'Extra Trees': lambda: ExtraTreesClassifier(300, n_jobs=2, random_state=0),
    'XGBoost': lambda: XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, n_jobs=2, verbosity=0),
    'LightGBM': lambda: LGBMClassifier(n_estimators=300, num_leaves=31, learning_rate=0.1, verbose=-1),
    'Multilayer Perceptron': lambda: make_pipeline(StandardScaler(), MLPClassifier((256,), alpha=1e-3, max_iter=60, early_stopping=True, random_state=0)),
}


def score(yt, P):
    P = np.asarray(P, np.float64); P = np.clip(P, 1e-12, None); P = P / P.sum(1, keepdims=True)
    pred = P.argmax(1)
    return dict(accuracy=accuracy_score(yt, pred), macro_f1=f1_score(yt, pred, average='macro'),
                precision=precision_score(yt, pred, average='macro'), recall=recall_score(yt, pred, average='macro'),
                roc_auc=roc_auc_score(yt, P, multi_class='ovr', average='macro'), confusion=confusion_matrix(yt, pred).tolist())


lab = {}
for name, mk in MODELS.items():
    t0 = time.time(); m = mk().fit(Htr, y[tr_s]); P = m.predict_proba(Hte)
    lab[name] = {**score(y[te], P), 'features': 'HOG (1,764 values)', 'train_images': len(tr_s), 'fit_s': round(time.time() - t0, 1)}
    print(f"{name:24s} acc {lab[name]['accuracy']:.3f} f1 {lab[name]['macro_f1']:.3f} ({lab[name]['fit_s']} s)", flush=True)
cnn = json.load(open(f'{ART}/hw_cnn_result.json'))
lab = {'Convolutional Neural Network (proposed)': {k: cnn[k] for k in ['accuracy', 'macro_f1', 'precision', 'recall', 'roc_auc', 'confusion', 'per_class_recall', 'params', 'epochs']},
       **lab}
json.dump({'dataset': 'Dyslexia handwriting corpus (Isa et al.), official Train/Test split',
           'classes': ['Normal', 'Reversal', 'Corrected'], 'n_test': int(len(te)), 'models': lab},
          open(f'{ART}/lab_handwriting.json', 'w'), indent=1)
print('saved')
