"""Handwriting module training.
CNN (proposed): 3 convolutional blocks + 256-filter layer, global average pooling,
trained on the official Train split and tested on the official Test split.
Exports ONNX (activations + logits) for the server and Model Lab metrics."""
import os, sys, json, time
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
import numpy as np, pandas as pd, tensorflow as tf
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, confusion_matrix, roc_auc_score, log_loss

D, ART = sys.argv[1], sys.argv[2]
EPOCHS = int(sys.argv[3]) if len(sys.argv) > 3 else 14
tf.config.threading.set_intra_op_parallelism_threads(2); tf.config.threading.set_inter_op_parallelism_threads(1)
tf.keras.utils.set_random_seed(11)
X = np.load(f'{D}/hw_X32.npy'); M = pd.read_csv(f'{D}/hw_meta.csv'); y = M.y.values
nl = M.groupby('key').y.nunique(); conflict = set(nl[nl > 1].index)
tr = M[(M.split == 'Train') & ~M.key.isin(conflict)].drop_duplicates('key').index.values
te = M[M.split == 'Test'].index.values
rng = np.random.default_rng(3); perm = rng.permutation(tr); nv = int(0.08 * len(perm)); va, fit = perm[:nv], perm[nv:]
prep = lambda ix: (X[ix].astype(np.float32) / 255.0)[..., None]
cnt = np.bincount(y[fit], minlength=3); cw = {i: len(fit) / (3 * cnt[i]) for i in range(3)}

aug = tf.keras.Sequential([tf.keras.layers.RandomTranslation(0.06, 0.06, fill_mode='constant'),
                           tf.keras.layers.RandomRotation(0.025, fill_mode='constant'),
                           tf.keras.layers.RandomZoom(0.08, fill_mode='constant')])


def block(x, f, drop, pool=True):
    for _ in range(2):
        x = tf.keras.layers.Conv2D(f, 3, padding='same', use_bias=False)(x)
        x = tf.keras.layers.BatchNormalization()(x); x = tf.keras.layers.ReLU()(x)
    if pool:
        x = tf.keras.layers.MaxPooling2D()(x)
    return tf.keras.layers.Dropout(drop)(x)


inp = tf.keras.Input((32, 32, 1))
x = block(aug(inp), 32, 0.1); x = block(x, 64, 0.15); x = block(x, 128, 0.2, pool=False)
x = tf.keras.layers.Conv2D(256, 3, padding='same', use_bias=False)(x)
x = tf.keras.layers.BatchNormalization()(x); act = tf.keras.layers.ReLU(name='last_conv')(x)
g = tf.keras.layers.GlobalAveragePooling2D()(act); g = tf.keras.layers.Dropout(0.3)(g)
logits = tf.keras.layers.Dense(3, name='logits')(g)
model = tf.keras.Model(inp, logits)
steps = int(np.ceil(len(fit) / 256)) * EPOCHS
sched = tf.keras.optimizers.schedules.CosineDecay(2e-3, steps, alpha=0.02)
model.compile(tf.keras.optimizers.Adam(sched), tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True), metrics=['accuracy'])
print(model.count_params(), 'params', len(fit), 'train', len(va), 'val', len(te), 'test', flush=True)
t0 = time.time()
hist = model.fit(prep(fit), y[fit], validation_data=(prep(va), y[va]), epochs=EPOCHS, batch_size=256, class_weight=cw,
                 callbacks=[tf.keras.callbacks.ModelCheckpoint(f'{ART}/hw_cnn_best.keras', monitor='val_accuracy', save_best_only=True)], verbose=2)
model = tf.keras.models.load_model(f'{ART}/hw_cnn_best.keras')
sm = lambda L, T=1.0: (lambda z: np.exp(z - z.max(1, keepdims=True)) / np.exp(z - z.max(1, keepdims=True)).sum(1, keepdims=True))(L / T)
Lv = model.predict(prep(va), batch_size=1024, verbose=0)
Ts = np.exp(np.linspace(np.log(0.4), np.log(4), 120)); T = float(Ts[np.argmin([log_loss(y[va], sm(Lv, t), labels=[0, 1, 2]) for t in Ts])])
Lt = model.predict(prep(te), batch_size=1024, verbose=0); P = sm(Lt, T); pred = P.argmax(1); yt = y[te]
res = dict(accuracy=accuracy_score(yt, pred), macro_f1=f1_score(yt, pred, average='macro'),
           precision=precision_score(yt, pred, average='macro'), recall=recall_score(yt, pred, average='macro'),
           roc_auc=roc_auc_score(yt, P, multi_class='ovr', average='macro'),
           per_class_recall=(confusion_matrix(yt, pred).diagonal() / np.bincount(yt)).tolist(),
           confusion=confusion_matrix(yt, pred).tolist(), temperature=T, params=int(model.count_params()),
           epochs=EPOCHS, train_time_min=(time.time() - t0) / 60, n_train=len(fit), n_test=len(te),
           history={k: [float(v) for v in vals] for k, vals in hist.history.items()})
print({k: v for k, v in res.items() if k != 'history'}, flush=True)
np.save(f'{ART}/hw_test_probs.npy', P)

# ---------------------------------------------------------------- export for the server
sub = tf.keras.Model(model.inputs, [model.get_layer('last_conv').output, model.get_layer('logits').output])
import tf2onnx
spec = (tf.TensorSpec((None, 32, 32, 1), tf.float32, name='image'),)


@tf.function(input_signature=spec)
def serve(image):
    a, l = sub(image, training=False)
    return {'act': a, 'logits': l}


tf2onnx.convert.from_function(serve, input_signature=spec, opset=17, output_path=f'{ART}/hw_cnn.onnx')
W = model.get_layer('logits').get_weights()[0]
json.dump({'temperature': T, 'dense_kernel': W.tolist(), 'classes': ['Normal', 'Reversal', 'Corrected']}, open(f'{ART}/hw_meta.json', 'w'))
json.dump(res, open(f'{ART}/hw_cnn_result.json', 'w'), indent=1)
print('exported')
