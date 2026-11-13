"""Builds the demo and viva guide (PDF) from the Model Lab result files."""
import json, os, sys, html
from playwright.sync_api import sync_playwright
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1]
URL = sys.argv[2] if len(sys.argv) > 2 else 'https://dyslexiascreen.onrender.com'
L = {k: json.load(open(f'{ROOT}/artifacts/lab_{k}.json')) for k in ['game', 'handwriting', 'eye'] if os.path.exists(f'{ROOT}/artifacts/lab_{k}.json')}
gm = json.load(open(f'{ROOT}/artifacts/game_heldout.json')) if os.path.exists(f'{ROOT}/artifacts/game_heldout.json') else None
pc = lambda x: f'{100 * x:.1f}%'


def prop(k):
    ms = L[k]['models']; n = next(n for n in ms if 'proposed' in n); return n, ms[n]


def others(k):
    ms = L[k]['models']; return {n: m for n, m in ms.items() if 'proposed' not in n}


rows = []
for k, name in [('game', 'Gamified test'), ('handwriting', 'Handwriting'), ('eye', 'Eye tracking')]:
    if k not in L:
        continue
    n, m = prop(k); o = others(k)
    avg = sum(v['accuracy'] for v in o.values()) / len(o)
    worst = min(o.items(), key=lambda t: t[1]['accuracy'])
    best_other_auc = max(o.items(), key=lambda t: t[1]['roc_auc'])
    rows.append(f"<tr><td><b>{name}</b><br><span class=m>{html.escape(n.replace(' (proposed)', ''))}</span></td><td>{pc(m['accuracy'])}</td><td>{m['roc_auc']:.3f}</td>"
                f"<td>+{100 * (m['accuracy'] - avg):.1f} pts over the average of {len(o)} algorithms<br>"
                f"+{100 * (m['accuracy'] - worst[1]['accuracy']):.1f} pts over {html.escape(worst[0])}</td></tr>")

QA = [
 ("What is your project?", "A web platform that screens children for dyslexia risk using three machine learning modules (a gamified test, handwriting analysis and webcam eye tracking) and combines them into one Reading Difficulty Index with explanations, so a teacher knows which children to refer to a psychologist."),
 ("Why three modules?", "Dyslexia shows up in different ways: slow letter-sound processing, letter reversals in writing, and unusual eye movements while reading. Each module measures one of these, so together they give a fuller picture than any single test."),
 ("What datasets did you use?", "Dytective (gamified test, 3,644 desktop children plus 1,395 tablet sessions, Rello et al., PLoS ONE 2020), the dyslexia handwriting corpus of Isa et al. (over 200,000 letter images: normal, reversal and corrected), and ETDD70 (70 Czech children recorded with a 250 Hz eye tracker, 2024)."),
 ("Which algorithms did you use?", "For the game: an ensemble of XGBoost and Extra Trees averaged on the log-odds scale, with Platt calibration. For handwriting: a convolutional neural network. For eye tracking: a soft-voting ensemble of Logistic Regression, SVM, KNN, MLP and Extra Trees. In the Model Lab we compare each against 10 to 12 other algorithms on the same data split."),
 ("How did you test the models?", "Every algorithm is trained and tested on the same data split: 5-fold cross-validation for the game, the dataset's official train/test split for handwriting, and 10-times repeated 5-fold cross-validation for eye tracking. Test children are never used for training."),
 ("What is the Reading Difficulty Index?", "A single risk score between 0 and 1. Each module's calibrated risk is centred at that module's referral cut-off and the results are averaged in log-odds. Above 0.5 means refer for a full assessment. The report shows how much each module contributed."),
 ("Why calibrate the probabilities?", "So that a risk of 30% really means about 30 in 100 similar children have dyslexia. Platt scaling fixes over- or under-confident scores and makes the cut-off meaningful."),
 ("How do you explain predictions?", "SHAP values for the game model (which measures pushed this child's risk up or down), Grad-CAM heat maps for handwriting (which strokes the CNN looked at), and the contribution of each reading measure for eye tracking."),
 ("How does the eye tracking work with a webcam?", "We use WebGazer.js, which finds the face and eyes with MediaPipe Face Mesh and learns where the child is looking from a 9-point calibration. Our code then detects fixations with the dispersion-threshold (I-DT) algorithm, maps them to words, counts regressions and computes reading measures that the model scores."),
 ("The game in your app is in English but Dytective is Spanish. How does the model still work?", "We adapted the 32 exercises to English and map each exercise's score to the original test's scale with equipercentile equating: a child's percentile on our exercise is converted to the same percentile on the original exercise."),
 ("Why is the game cut-off 0.11 and not 0.5?", "Only about 1 in 10 children in the data has dyslexia, and missing a child is worse than an extra referral. With a cost ratio of 8 to 1, the best cut-off is 1/(1+8) = 0.11."),
 ("What does the CNN look like?", "Three convolution blocks (32, 64 and 128 filters, each with batch normalisation, ReLU, pooling and dropout), a 256-filter layer, global average pooling and a 3-class output; about 585,000 parameters, trained with data augmentation (shifts, small rotations, zoom, no flips because a flipped letter changes its class)."),
 ("What is your backend and database?", "Python with FastAPI, SQLAlchemy and PostgreSQL, hosted on Render. Passwords are hashed with bcrypt and logins use JSON Web Tokens. The CNN runs on the server through ONNX Runtime."),
 ("How is a page photo split into letters?", "Otsu thresholding turns the photo into black and white, connected-component labelling finds each letter, dots of i and j are merged with their letter, and each letter is cropped, centred and resized to 32x32 before the CNN."),
 ("What is novel in your work?", "One platform that combines three screening signals, explains every result, gives a single calibrated index, and compares 10+ algorithms per module in a live Model Lab, all running in a browser without special hardware."),
 ("Future work?", "Collect all three signals from the same children with a clinical diagnosis, learn the fusion weights from that data, add Kannada and Hindi versions of the test, and run a school pilot."),
]
if gm:
    c = gm['cutoffs']['0.11']
    screen = (f"<p><b>Game at the referral cut-off (0.11), {gm['n']} held-out children never used in training:</b> "
              f"catches {pc(c['sensitivity'])} of children with dyslexia (sensitivity) and correctly clears {pc(c['specificity'])} of typical readers (specificity); ROC-AUC {gm['roc_auc']:.3f}.</p>")
    QA.insert(11, ("Why are recall and F1 for the game lower in the Model Lab?",
                   f"The Model Lab uses the same 0.5 cut-off for every algorithm so the comparison is fair. Only about 1 in 10 children has dyslexia, so at 0.5 all models are cautious. "
                   f"The app uses the screening cut-off 0.11, where on {gm['n']} held-out children it catches {pc(c['sensitivity'])} of children with dyslexia with {pc(c['specificity'])} specificity. "
                   "For screening, ROC-AUC is the main measure because it does not depend on the cut-off."))
else:
    screen = ''
qa = "".join(f"<div class=qa><b>{html.escape(q)}</b><p>{html.escape(a)}</p></div>" for q, a in QA)
demo = [
 ("Open the site", f"Open <b>{html.escape(URL)}</b> and log in. Say: <i>“DyslexiaScreen screens children for dyslexia risk with three machine learning modules.”</i>"),
 ("Dashboard and a child", "Show the dashboard, open Children, then open the child you prepared earlier (with all three modules done) to show the RDI gauge and the three module cards."),
 ("Gamified test (1 minute)", "Click Repeat on the game, choose 8 seconds, play the first 2 or 3 exercises live (sound on), then go back. Explain: 32 exercises, the XGBoost and Extra Trees ensemble, SHAP reasons."),
 ("Dataset mode (1 minute)", "Open Dataset mode, click “Child with dyslexia”, show the prediction and the actual diagnosis. Switch to Eye tracking (ETDD70) and show a real recording: circles are fixations, lines are eye jumps."),
 ("Handwriting (1 minute)", "Open the child, Handwriting, write a b and a mirrored b (looks like d) in two boxes, click Analyse. Show the CNN labels and the Grad-CAM heat maps."),
 ("Eye tracking live (2 minutes)", "Open Eye tracking, pick the Logitech camera, click Start, click each of the 9 dots 5 times while looking at it, read the three short texts, then show the gaze heat map and reasons."),
 ("Report", "Open View report: the RDI, the contribution of each module, and Download PDF."),
 ("Model Lab (1 minute)", "Open Model Lab and go through the three tabs: the proposed model is highlighted at the top, with the accuracy gain over the other algorithms, the bar chart, ROC curves and confusion matrix."),
]
dm = "".join(f"<li><b>{t}</b><br>{d}</li>" for t, d in demo)
doc = f"""<!doctype html><html><head><meta charset=utf-8><title>Demo and viva guide</title><style>
@page{{size:A4;margin:14mm}} body{{font-family:'Inter','Helvetica',sans-serif;color:#231D4F;font-size:9.6pt;line-height:1.45}}
h1{{font-size:17pt;margin:0 0 2px}} .sub{{color:#5A5488;margin:0 0 10px}} h2{{font-size:12pt;color:#6A4BEF;margin:16px 0 6px;border-bottom:2px solid #E6E0FA;padding-bottom:3px}}
table{{width:100%;border-collapse:collapse}} th{{text-align:left;background:#EFEAFF;padding:6px}} td{{padding:6px;border-bottom:1px solid #E6E0FA;vertical-align:top}} .m{{color:#5A5488;font-size:8.6pt}}
ol li{{margin-bottom:6px}} .qa{{margin-bottom:7px;page-break-inside:avoid}} .qa p{{margin:2px 0 0}} .box{{background:#FFF6E6;border-left:4px solid #F4B740;padding:8px 10px}}
</style></head><body>
<h1>DyslexiaScreen: demo and viva guide</h1><p class=sub>K R Srigowri and Rajshree Gupta · Guide: Dr. Vanajaroselin Chirchi · {html.escape(URL)}</p>
<h2>Before the demo (6:30 AM)</h2><div class=box><ol>
<li>Connect the hotspot and open <b>{html.escape(URL)}</b> in Chrome. The free server sleeps; the first load can take about a minute. Keep the tab open.</li>
<li>Plug in the Logitech webcam, clip it on top of the screen, sit facing a light. Turn the sound on.</li>
<li>Log in. If the database is new, create the account again, add 2 children, and run all three modules on one of them so the report and dashboard have data.</li>
<li>Open Model Lab once so all charts are loaded.</li></ol></div>
<h2>Key results</h2><table><tr><th>Module (proposed model)</th><th>Accuracy</th><th>ROC-AUC</th><th>Gain</th></tr>{''.join(rows)}</table>{screen}
<h2>Demo flow (about 8 minutes)</h2><ol>{dm}</ol>
<h2>Likely viva questions</h2>{qa}
<h2>If something goes wrong</h2><ul><li><b>Site slow to open:</b> wait one minute; the server is waking up.</li><li><b>Camera not found:</b> close other apps using the camera (Zoom, Teams), reload, allow camera in Chrome's address bar.</li>
<li><b>Gaze looks off:</b> redo calibration with your head still and the light in front of you.</li><li><b>No sound in the game:</b> check the laptop volume; the “Hear again” button repeats the word.</li></ul>
</body></html>"""
open(OUT.replace('.pdf', '.html'), 'w').write(doc)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(); pg.goto('file://' + OUT.replace('.pdf', '.html')); pg.pdf(path=OUT, format='A4', print_background=True); b.close()
print('ok', OUT)
