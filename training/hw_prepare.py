"""Read the Kaggle dyslexia handwriting corpus (Train/Test x Normal/Reversal/Corrected)
and store canonical 32x32 images (same preprocessing as the server) as numpy arrays."""
import os, sys, hashlib
import numpy as np, pandas as pd
from PIL import Image
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.ml.handwriting import to_gray_ink, canon

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
rows, X = [], []
for split in ['Train', 'Test']:
    for yi, c in enumerate(['Normal', 'Reversal', 'Corrected']):
        d = os.path.join(SRC, split, c)
        for f in sorted(os.listdir(d)):
            try:
                im = canon(to_gray_ink(Image.open(os.path.join(d, f))))
            except Exception:
                im = None
            if im is None:
                continue
            X.append(im); rows.append((split, c, yi, f, hashlib.md5(im.tobytes()).hexdigest()))
X = np.stack(X)
np.save(os.path.join(OUT, 'hw_X32.npy'), X)
pd.DataFrame(rows, columns=['split', 'cls', 'y', 'file', 'key']).to_csv(os.path.join(OUT, 'hw_meta.csv'), index=False)
print(X.shape)
