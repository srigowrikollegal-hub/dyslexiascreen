"""Draws the site's background: a mountain range at dusk (layered ridges, alpenglow,
mist, stars and pines). Procedural, so it is original artwork with no licence issues."""
import sys
import numpy as np
from PIL import Image, ImageFilter
W, H = 2400, 1350
rng = np.random.default_rng(11)
Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
hexc = lambda h: np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255


def grad(stops):
    ys = np.array([s for s, _ in stops]); cs = np.array([hexc(c) for _, c in stops])
    t = Y[:, :1] / H
    return np.stack([np.interp(t, ys, cs[:, k]) for k in range(3)], -1) * np.ones((1, W, 1), np.float32)


img = grad([(0, '#0E0B2E'), (.22, '#221A5C'), (.42, '#4A2D86'), (.56, '#8E4597'), (.66, '#D56A8A'), (.73, '#F7A07E'), (.79, '#FFD2A2'), (1, '#FFD2A2')])
# sun low on the horizon with a wide warm glow
sx, sy = .66 * W, .655 * H; d = np.hypot(X - sx, (Y - sy) * 1.15)
img += (np.exp(-(d / 420) ** 2) * .38)[..., None] * hexc('#FFB487') + (np.exp(-(d / 130) ** 2) * .5)[..., None] * hexc('#FFE6C2')
img = np.where((d < 62)[..., None], img * .2 + hexc('#FFF4DE') * .8, img)
# stars, fading towards the horizon
n = 900; px, py = rng.uniform(0, W, n), rng.beta(1.2, 3.2, n) * H * .62; br = rng.uniform(.25, 1, n) * (1 - py / (H * .62)) ** 1.3
star = np.zeros((H, W), np.float32)
for x, y, b in zip(px.astype(int), py.astype(int), br):
    star[y, x] += b
star = np.asarray(Image.fromarray((np.clip(star, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.8)), np.float32) / 255 * 2.2
img += star[..., None] * hexc('#FFF3DA')


def noise1d(n, octaves, seed):
    r = np.random.default_rng(seed); out = np.zeros(n, np.float32); amp, freq = 1.0, 3
    for _ in range(octaves):
        pts = r.uniform(-1, 1, freq + 2); xs = np.linspace(0, freq, n)
        i = xs.astype(int); f = xs - i; f = (1 - np.cos(f * np.pi)) / 2
        out += amp * (pts[i] * (1 - f) + pts[i + 1] * f); amp *= .5; freq *= 2
    return out


def wisps(y0, h, alpha, color, seed):
    global img
    r = np.random.default_rng(seed); band = np.zeros((H, W), np.float32)
    for _ in range(5):
        cx, cy, w = r.uniform(0, W), y0 + r.normal(0, h), r.uniform(300, 900)
        band += np.exp(-((X - cx) / w) ** 2 - ((Y - cy) / (h * .35)) ** 2) * r.uniform(.4, 1)
    tex = noise1d(W, 6, seed + 1)[None, :] * .5 + .5
    a = np.clip(band * tex, 0, 1) * alpha
    img = img * (1 - a[..., None]) + hexc(color) * a[..., None]


wisps(.50 * H, 30, .16, '#FFB39A', 5)
x = np.arange(W)


def layer(base, amp, octs, seed, top, bottom, peaks=(), glow=0.0, mist=None, snow=0.0):
    """Draw one ridge: colour fades from `top` at the crest to `bottom` lower down; optional alpenglow,
    sunlit faces, snow and mist."""
    global img
    ridge = base * H - amp * H * (noise1d(W, octs, seed) * .5 + .5)
    for (px_, ph, pw) in peaks:                                   # sharp, rocky summits
        t = np.clip(1 - np.abs(x - px_ * W) / (pw * W), 0, 1)
        ridge -= ph * H * t ** 1.5 * (1 + .10 * noise1d(W, 9, seed + 7))
    depth = np.clip((Y - ridge[None, :]) / (H * .35), 0, 1)
    col = hexc(top) * (1 - depth[..., None]) + hexc(bottom) * depth[..., None]
    slope = np.gradient(np.convolve(np.pad(ridge, 60, mode='edge'), np.ones(121) / 121, 'same')[60:-60])  # faces turned towards the sun are lit
    lit = np.clip(slope * 1.5, -1, 1)[None, :] * np.exp(-np.clip(Y - ridge[None, :], 0, None) / (H * .22))
    col *= (1 + .2 * lit)[..., None]
    if glow:
        col += (np.exp(-np.clip(Y - ridge[None, :], 0, None) / 55) * glow)[..., None] * hexc('#FF9EAE')
    if snow:
        elev = np.clip(base * H - ridge, 0, None)
        line = ridge + elev * snow * (.55 + .45 * (noise1d(W, 9, seed + 3) * .5 + .5))
        sm = (Y < line[None, :]) & (Y > ridge[None, :])
        col = np.where(sm[..., None], col * .35 + hexc('#FFE3EA') * .65 * (1 + .15 * lit[..., None]), col)
    a = np.clip(Y - ridge[None, :] + .5, 0, 1)
    img = img * (1 - a[..., None]) + col * a[..., None]
    if mist is not None:
        m = np.exp(-np.clip(Y - (ridge[None, :] + H * .09), 0, None) ** 2 / (H * .03) ** 2) * (Y > ridge[None, :]) * mist[1]
        img = img * (1 - m[..., None]) + hexc(mist[0]) * m[..., None]
    return ridge


layer(.73, .09, 6, 21, '#A879AE', '#8D64A0', peaks=[(.16, .07, .09), (.88, .06, .07)], mist=('#E3A2B4', .32))
layer(.80, .08, 7, 22, '#7E5596', '#5E4185', peaks=[(.40, .40, .16), (.30, .16, .07), (.53, .20, .08)], glow=.45, mist=('#B47FA8', .30), snow=.13)
layer(.86, .08, 7, 23, '#4E3679', '#3B2A66', peaks=[(.76, .10, .09)], mist=('#8E6296', .22))
layer(.92, .07, 8, 24, '#2E225A', '#231A47', mist=('#5E4278', .16))
r5 = layer(.985, .07, 8, 25, '#191335', '#120E28')
# pines along the nearest ridge
tree = np.zeros((H, W), np.float32)
for cx in np.sort(rng.uniform(0, W, 160)):
    i = int(cx); base_y = r5[i] + 4; h = rng.uniform(28, 85); w = h * rng.uniform(.22, .3)
    ys, xs = slice(int(base_y - h), int(base_y)), slice(max(int(cx - w), 0), min(int(cx + w) + 1, W))
    yy, xx = Y[ys, xs], X[ys, xs]
    tree[ys, xs] = np.maximum(tree[ys, xs], (np.abs(xx - cx) <= (yy - (base_y - h)) / h * w).astype(np.float32))
tree = np.asarray(Image.fromarray((tree * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.6)), np.float32)[..., None] / 255
img = img * (1 - tree) + hexc('#120E28') * tree
img += rng.normal(0, .012, img.shape).astype(np.float32)          # fine grain
out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
out.save(sys.argv[1], quality=84, optimize=True, progressive=True)
out.resize((960, 540), Image.LANCZOS).save(sys.argv[1].replace('.jpg', '-small.jpg'), quality=80)
print('ok')
