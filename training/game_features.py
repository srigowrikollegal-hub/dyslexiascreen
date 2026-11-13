"""Feature construction for the gamified test (Dytective format), shared by
training and the server so both build exactly the same model inputs."""
import numpy as np

GROUPS = {'letters': range(1, 5), 'syllables': range(5, 10), 'words': range(10, 14), 'visual': range(14, 18),
          'pseudo': range(18, 22), 'spelling': range(22, 27), 'building': range(27, 30), 'memory': [30], 'dictation': [31, 32]}
MEAS = ['Clicks', 'Hits', 'Misses', 'Score', 'Accuracy', 'Missrate']
RAW = ['Gender', 'Nativelang', 'Otherlang', 'Age'] + [f'{m}{q}' for q in range(1, 33) for m in MEAS]


def engineered(row):
    """41 summaries of a child's 32 exercises (row: dict-like with RAW keys, numeric)."""
    f = {}
    age = max(float(row['Age']), 1.0)
    acc = np.array([row[f'Accuracy{q}'] for q in range(1, 33)], float)
    mis = np.array([row[f'Missrate{q}'] for q in range(1, 33)], float)
    hit = np.array([row[f'Hits{q}'] for q in range(1, 33)], float)
    clk = np.array([row[f'Clicks{q}'] for q in range(1, 33)], float)
    for g, qs in GROUPS.items():
        ix = [q - 1 for q in qs]
        f[f'{g}_acc'] = float(np.mean(acc[ix])); f[f'{g}_miss'] = float(np.mean(mis[ix])); f[f'{g}_hits'] = float(np.sum(hit[ix]))
    f['total_clicks'] = float(clk.sum()); f['total_hits'] = float(hit.sum()); f['total_misses'] = float(np.sum([row[f'Misses{q}'] for q in range(1, 33)]))
    f['overall_acc'] = f['total_hits'] / max(f['total_clicks'], 1.0); f['overall_miss'] = f['total_misses'] / max(f['total_clicks'], 1.0)
    f['hits_per_age'] = f['total_hits'] / age; f['clicks_per_age'] = f['total_clicks'] / age
    f['acc_sd'] = float(np.std(acc)); f['acc_min'] = float(np.min(acc)); f['miss_max'] = float(np.max(mis))
    f['zero_click_items'] = float(np.sum(clk == 0)); f['auditory_minus_visual'] = f['letters_acc'] + f['syllables_acc'] - 2 * f['visual_acc']
    f['phon_vs_lex'] = f['pseudo_acc'] - f['words_acc']; f['dictation_x_age'] = f['dictation_acc'] * age
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
