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


def items_to_row(items, age, gender, native, other):
    """Convert app game results (clicks, hits, misses per exercise) into the dataset's 196 raw fields."""
    row = {'Gender': 1.0 if gender == 'male' else 0.0, 'Nativelang': 1.0 if native else 0.0,
           'Otherlang': 1.0 if other else 0.0, 'Age': float(age)}
    by = {int(i['q']): i for i in items}
    for q in range(1, 33):
        it = by.get(q, {'clicks': 0, 'hits': 0, 'misses': 0})
        c, h, m = float(it['clicks']), float(it['hits']), float(it['misses'])
        row[f'Clicks{q}'] = c; row[f'Hits{q}'] = h; row[f'Misses{q}'] = m; row[f'Score{q}'] = h
        row[f'Accuracy{q}'] = h / c if c else 0.0; row[f'Missrate{q}'] = m / c if c else 0.0
    return row
