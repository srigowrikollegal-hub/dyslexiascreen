# DyslexiaScreen

A web platform that screens children for dyslexia risk with three machine learning
modules and combines them into one **Reading Difficulty Index (RDI)**.

Final-year capstone project, Department of Information Science and Engineering,
Dayananda Sagar Academy of Technology and Management, Bengaluru.
Team: K R Srigowri (1DT23IS064), Rajshree Gupta (1DT23IS117). Guide: Dr. Vanajaroselin Chirchi.

## Modules

| Module | Input | Model | Explanation |
|---|---|---|---|
| Gamified test | 32 exercises (letters, syllables, words, made-up words, visual search, spelling, grammar, word building, memory, dictation); clicks, hits, misses per exercise | XGBoost + Extra Trees ensemble averaged on the log-odds scale, Platt calibration (Dytective dataset) | TreeSHAP contribution of each measure |
| Handwriting | Letters written on a drawing pad, letter images, or a photo of a page | Convolutional neural network (3 blocks + 256-filter layer, global average pooling), ONNX Runtime on the server | Class activation map (Grad-CAM) per letter |
| Eye tracking | Webcam gaze (WebGazer) while reading syllables, a story and made-up words | Fixations by dispersion threshold (I-DT), word-level reading measures, logistic model trained on ETDD70 | Contribution of each reading measure |

**Fusion.** Each module's calibrated risk is centred at its own referral cut-off and the
centred log-odds are averaged: `logit(RDI) = Σ w_k [logit(p_k) − logit(c_k)]`, with equal
weights over the modules completed. RDI ≥ 0.5 means "refer for assessment".

**Model Lab.** Every module compares 10–13 algorithms (Logistic Regression, SVM, KNN,
Naive Bayes, Decision Tree, Random Forest, Extra Trees, AdaBoost, Gradient Boosting,
XGBoost, LightGBM, MLP, CNN) on the same data split, with accuracy, ROC-AUC, precision,
recall, F1, ROC curves and confusion matrices.

## Architecture

- **Backend:** Python, FastAPI, SQLAlchemy (PostgreSQL in production, SQLite locally), JWT login with bcrypt-hashed passwords.
- **Machine learning:** scikit-learn, XGBoost, LightGBM, TensorFlow (training) and ONNX Runtime (serving).
- **Frontend:** HTML, CSS and JavaScript single-page app; WebGazer for webcam eye tracking; Chart.js.
- **Hosting:** Render (web service + PostgreSQL), defined in `render.yaml`.

```
app/            FastAPI server (main.py, db.py, auth.py) and ml/ (game, handwriting, eye, fusion)
static/         Frontend (index.html, css/, js/, vendor/)
training/       Training scripts for every module and the Model Lab
artifacts/      Trained models and Model Lab results
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | /api/auth/register, /api/auth/login | Create account, log in (returns token) |
| GET/POST | /api/children | List or add child profiles |
| GET | /api/children/{id}/report | Latest result of each module and the RDI |
| POST | /api/game/predict | Score a completed gamified test |
| GET | /api/game/sample | Score a held-out child from the dataset (Dataset mode) |
| POST | /api/handwriting/predict, /api/handwriting/sheet | Classify letter images or a page photo |
| POST | /api/eye/analyze | Analyse webcam gaze from the three reading tasks |
| GET | /api/lab | Model Lab results |

## Run locally

```
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Then open http://localhost:8000.

## Datasets

- Dytective gamified test (Rello et al., PLoS ONE 2020).
- Dyslexia handwriting corpus (Isa et al.; Kaggle).
- ETDD70 eye-tracking dataset (Sedmidubsky et al., 2024; Zenodo, CC BY 4.0).
