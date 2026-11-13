"""Feature construction for the gamified test (Dytective format), shared by
training and the server so both build exactly the same model inputs."""
import numpy as np

FAM = {"letter": range(1, 5), "syllable": range(5, 10), "word": range(10, 14), "pairs": range(14, 18),
       "pseudo": range(18, 22), "spelling": range(22, 27), "building": range(27, 30), "memory": range(30, 33)}
MEAS = ['Clicks', 'Hits', 'Misses', 'Score', 'Accuracy', 'Missrate']
RAW = ['Gender', 'Nativelang', 'Otherlang', 'Age'] + [f'{m}{q}' for q in range(1, 33) for m in MEAS]
NAN = float('nan')


def _div(a, b):
    return a / b if (b and b == b and a == a) else NAN


def _sum(vals):
    v = np.array(vals, float)
    return float(np.nansum(v)) if np.isfinite(v).any() else NAN


def engineered(row):
    """41 summaries of one child's 32 exercises (same definitions as the paper's module1_v2.py)."""
    f = {}
    for m in ['Clicks', 'Hits', 'Misses']:
        f[f'total_{m}'] = _sum([row[f'{m}{q}'] for q in range(1, 33)])
        for k, qs in FAM.items():
            f[f'{k}_{m}'] = _sum([row[f'{m}{q}'] for q in qs])
    f['overall_accuracy'] = _div(f['total_Hits'], f['total_Clicks'])
    f['overall_missrate'] = _div(f['total_Misses'], f['total_Clicks'])
    for k in FAM:
        f[f'{k}_accuracy'] = _div(f[f'{k}_Hits'], f[f'{k}_Clicks'])
    acc = np.array([row[f'Accuracy{q}'] for q in range(1, 33)], float)
    f['n_skipped'] = float(sum(row[f'Clicks{q}'] == 0 for q in range(1, 33)))
    f['n_low_accuracy'] = float((acc < 0.5).sum())
    f['accuracy_spread'] = float(np.nanstd(acc, ddof=1))
    f['hits_per_year_of_age'] = _div(f['total_Hits'], float(row['Age']))
    return f


# Maximum correct responses per exercise in the English web version (moles depend on time).
HMAX = {**{q: 4 for q in range(5, 14)}, **{q: 5 for q in range(14, 18)}, **{q: 4 for q in range(18, 22)},
        22: 4, 23: 4, 24: 3, 25: 3, 26: 4, 27: 15, 28: 10, 29: 6, 30: 11, 31: 4, 32: 4}
CMAX = {31: 25, 32: 21}
_EQ = None


def _eq():
    global _EQ
    if _EQ is None:
        import os, json
        _EQ = {int(k): v for k, v in json.load(open(os.path.join(os.path.dirname(__file__), '..', 'artifacts', 'game_equating.json'))).items()}
    return _EQ


def _q(table, f):
    """Quantile function from a 101-point table at fraction f in [0, 1]."""
    f = min(max(f, 0.0), 1.0) * 100
    lo = int(np.floor(f)); hi = min(lo + 1, 100)
    return table[lo] + (table[hi] - table[lo]) * (f - lo)


def _cdf(table, v):
    return float(np.searchsorted(np.array(table), v, side='right')) / len(table)


def items_to_row(items, age, gender, native, other, seconds=12):
    """Equipercentile equating: each exercise's performance in the English web version is mapped to
    the original test's scale (percentile of correct answers -> hits, percentile of miss rate -> misses)."""
    eq = _eq()
    row = {'Gender': 1.0 if gender == 'male' else 0.0, 'Nativelang': 1.0 if native else 0.0,
           'Otherlang': 1.0 if other else 0.0, 'Age': float(age)}
    by = {int(i['q']): i for i in items}
    for q in range(1, 33):
        it = by.get(q, {'clicks': 0, 'hits': 0, 'misses': 0})
        c, h, m = float(it['clicks']), float(it['hits']), float(it['misses'])
        hmax = HMAX.get(q, max(round(0.55 * seconds), 1))
        t = eq[q]
        H = round(_q(t['hits'], h / hmax))
        rate = m / max(c, 1.0) if q not in (31, 32) else m / max(h + m, 1.0)
        M = round(_q(t['misses'], _cdf(t['missrate'], rate)))
        if c == 0:
            H = M = 0
        cmax = CMAX.get(q, hmax * 1.3)
        C = max(round(_q(t['clicks'], c / cmax)), H + M) if c else 0
        row[f'Clicks{q}'] = float(C); row[f'Hits{q}'] = float(H); row[f'Misses{q}'] = float(M); row[f'Score{q}'] = float(H)
        row[f'Accuracy{q}'] = H / C if C else 0.0; row[f'Missrate{q}'] = M / C if C else 0.0
    return row


# Short form: 10 exercises covering letters, syllables, words, made-up words, spelling, meaning,
# grammar and word building (chosen for how well each separates the two groups, and for variety).
QUICK = [4, 9, 11, 19, 20, 22, 24, 25, 26, 28]
QUICK_RAW = ['Gender', 'Nativelang', 'Otherlang', 'Age'] + [f'{m}{q}' for q in QUICK for m in MEAS]


def quick_features(row):
    """Model inputs for the short form: the 10 exercises' measures plus summaries over them."""
    f = {c: row[c] for c in QUICK_RAW}
    for m in ['Clicks', 'Hits', 'Misses']:
        f[f'quick_{m}'] = _sum([row[f'{m}{q}'] for q in QUICK])
    f['quick_accuracy'] = _div(f['quick_Hits'], f['quick_Clicks'])
    f['quick_missrate'] = _div(f['quick_Misses'], f['quick_Clicks'])
    acc = np.array([row[f'Accuracy{q}'] for q in QUICK], float)
    f['quick_low_accuracy'] = float((acc < 0.5).sum())
    f['quick_hits_per_year_of_age'] = _div(f['quick_Hits'], float(row['Age']))
    return f
