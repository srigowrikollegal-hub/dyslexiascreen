"""Handwriting module: letter images -> canonical 32x32 form -> CNN (ONNX) ->
normal / reversal / corrected, with a class activation map for each letter.
A handwriting sheet is split into letters by connected components first."""
import os, io, json, base64
import numpy as np
from PIL import Image
from scipy import ndimage

ART = os.path.join(os.path.dirname(__file__), '..', '..', 'artifacts')
CLASSES = ['Normal', 'Reversal', 'Corrected']
S = 32
_sess = _meta = None


def load():
    global _sess, _meta
    if _sess is None:
        import onnxruntime as ort
        _sess = ort.InferenceSession(os.path.join(ART, 'hw_cnn.onnx'), providers=['CPUExecutionProvider'])
        _meta = json.load(open(os.path.join(ART, 'hw_meta.json')))
        _meta['W'] = np.array(_meta['dense_kernel'], np.float32)        # (channels, 3)
    return _sess, _meta


def otsu(g):
    hist = np.bincount(g.ravel(), minlength=256).astype(float); p = hist / max(hist.sum(), 1)
    om = np.cumsum(p); mu = np.cumsum(p * np.arange(256)); mt = mu[-1]
    with np.errstate(divide='ignore', invalid='ignore'):
        sb = (mt * om - mu) ** 2 / (om * (1 - om))
    sb[~np.isfinite(sb)] = 0
    return int(np.argmax(sb))


def to_gray_ink(img: Image.Image):
    """Grayscale with bright ink on a dark background."""
    if img.mode in ('RGBA', 'LA'):
        bg = Image.new('RGBA', img.size, (255, 255, 255, 255)); bg.alpha_composite(img.convert('RGBA')); img = bg
    g = np.asarray(img.convert('L'), dtype=np.uint8)
    border = np.concatenate([g[0], g[-1], g[:, 0], g[:, -1]])
    return 255 - g if np.median(border) > 127 else g


def canon(g):
    """Same canonical form as training: Otsu, crop to ink, centre with 20% margin, 32x32."""
    t = otsu(g); b = (g > max(t, 1)).astype(np.uint8)
    ys, xs = np.nonzero(b)
    if len(ys) == 0:
        return None
    b = b[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    h, w = b.shape; side = int(np.ceil(max(h, w) * 1.2)) + 2
    pad = np.zeros((side, side), np.uint8); y0, x0 = (side - h) // 2, (side - w) // 2
    pad[y0:y0 + h, x0:x0 + w] = b * 255
    return np.asarray(Image.fromarray(pad).resize((S, S), Image.BILINEAR), dtype=np.uint8)


def softmax(z, T=1.0):
    z = z / T; z = z - z.max(-1, keepdims=True); e = np.exp(z); return e / e.sum(-1, keepdims=True)


def cam_png(img32, act, w):
    cam = np.maximum(act @ w, 0)                        # (h, w)
    cam = cam / (cam.max() + 1e-9)
    cam = np.asarray(Image.fromarray((cam * 255).astype(np.uint8)).resize((128, 128), Image.BILINEAR), float) / 255
    base = np.asarray(Image.fromarray(img32).resize((128, 128), Image.BILINEAR), float) / 255
    rgb = np.stack([base * 0.55 + cam * 0.9, base * 0.55 + cam * 0.35, base * 0.55 + 0.15 * (1 - cam)], -1)
    rgb = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    buf = io.BytesIO(); Image.fromarray(rgb).save(buf, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def classify(canon_imgs):
    sess, meta = load()
    X = (np.stack(canon_imgs).astype(np.float32) / 255.0)[..., None]
    act, logits = sess.run(['act', 'logits'], {'image': X})
    P = softmax(logits, meta.get('temperature', 1.0))
    out = []
    for i in range(len(X)):
        k = int(P[i].argmax())
        out.append({'pred': CLASSES[k], 'probs': {c: float(P[i, j]) for j, c in enumerate(CLASSES)},
                    'cam': cam_png(canon_imgs[i], act[i], meta['W'][:, k])})
    return out


def summarise(letters):
    if not letters:
        return {'risk': None, 'label': 'No letters found', 'letters': []}
    p_h = float(np.mean([l['probs']['Reversal'] + l['probs']['Corrected'] for l in letters]))
    n_rev = sum(l['pred'] == 'Reversal' for l in letters); n_cor = sum(l['pred'] == 'Corrected' for l in letters)
    label = 'Frequent reversals' if p_h >= 0.5 else ('Some reversals' if p_h >= 0.3 else 'Typical letter forms')
    return {'risk': p_h, 'label': label, 'n_letters': len(letters), 'n_reversal': n_rev, 'n_corrected': n_cor,
            'letters': letters}


def predict_images(blobs):
    imgs = []
    for b in blobs:
        c = canon(to_gray_ink(Image.open(io.BytesIO(b))))
        if c is not None:
            imgs.append(c)
    return summarise(classify(imgs) if imgs else [])


def predict_sheet(blob, max_letters=60):
    """Split a photo or scan of handwriting into letters, then classify each."""
    img = Image.open(io.BytesIO(blob)); img.thumbnail((1600, 1600))
    g = to_gray_ink(img)
    g = ndimage.gaussian_filter(g, 1)
    t = otsu(g); b = g > max(t, 10)
    b = ndimage.binary_closing(b, iterations=2)
    lab, n = ndimage.label(b)
    objs = ndimage.find_objects(lab)
    H, W = b.shape; boxes = []
    for i, sl in enumerate(objs):
        h = sl[0].stop - sl[0].start; w = sl[1].stop - sl[1].start
        area = (lab[sl] == i + 1).sum()
        if area < 0.00004 * H * W or h < 8 or h > 0.6 * H or w > 0.6 * W:
            continue
        boxes.append([sl[0].start, sl[1].start, sl[0].stop, sl[1].stop])
    # merge dots of i / j with the stroke below them
    boxes.sort(key=lambda r: (r[0] + r[2]) / 2)
    merged = []
    for r in boxes:
        for m in merged:
            ox = min(r[3], m[3]) - max(r[1], m[1])
            if ox > 0.5 * min(r[3] - r[1], m[3] - m[1]) and (r[2] - r[0]) * (r[3] - r[1]) < 0.25 * (m[2] - m[0]) * (m[3] - m[1]) and abs(r[2] - m[0]) < (m[2] - m[0]):
                m[0], m[1], m[2], m[3] = min(m[0], r[0]), min(m[1], r[1]), max(m[2], r[2]), max(m[3], r[3]); break
        else:
            merged.append(list(r))
    # reading order: group into lines, then left to right
    hs = np.median([r[2] - r[0] for r in merged]) if merged else 1
    merged.sort(key=lambda r: (round(((r[0] + r[2]) / 2) / (hs * 1.2)), r[1]))
    merged = merged[:max_letters]
    crops, kept = [], []
    for r in merged:
        c = canon(g[r[0]:r[2], r[1]:r[3]])
        if c is not None:
            crops.append(c); kept.append(r)
    res = summarise(classify(crops) if crops else [])
    for l, r in zip(res['letters'], kept):
        l['box'] = {'y': r[0] / H, 'x': r[1] / W, 'h': (r[2] - r[0]) / H, 'w': (r[3] - r[1]) / W}
    res['sheet_size'] = [W, H]
    return res
