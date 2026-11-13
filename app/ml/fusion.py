"""Reading Difficulty Index (RDI): late fusion of the calibrated module risks.

Each module risk p_k is centred at that module's own referral cut-off c_k
(so a module on its own refers exactly when its term is positive), and the
centred log-odds are averaged with equal weights:

    logit(RDI) = sum_k w_k [logit(p_k) - logit(c_k)],   w_k = 1 / (number of modules used)

RDI >= 0.5 means "refer for assessment". Each module's share is reported."""
import math

NAMES = {'game': 'Gamified test', 'handwriting': 'Handwriting', 'eye': 'Eye tracking'}
CUTOFF = {'game': 0.11, 'handwriting': 0.5, 'eye': 0.5}


def logit(p):
    p = min(max(p, 0.005), 0.995)
    return math.log(p / (1 - p))


def rdi(risks: dict):
    avail = {k: v for k, v in risks.items() if v is not None}
    if not avail:
        return None
    w = 1.0 / len(avail)
    parts = {k: w * (logit(v) - logit(CUTOFF[k])) for k, v in avail.items()}
    z = sum(parts.values())
    value = 1 / (1 + math.exp(-z))
    band = 'High' if value >= 0.75 else ('Elevated' if value >= 0.5 else ('Borderline' if value >= 0.35 else 'Low'))
    return {'rdi': value, 'band': band, 'refer': value >= 0.5, 'weights': {k: w for k in avail},
            'cutoffs': {k: CUTOFF[k] for k in avail},
            'contributions': {k: {'name': NAMES[k], 'risk': avail[k], 'log_odds': parts[k]} for k in avail}}
