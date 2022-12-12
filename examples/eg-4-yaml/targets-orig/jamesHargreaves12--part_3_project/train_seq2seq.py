import argparse
import os
import yaml
import numpy as np
import matplotlib.pyplot as plt

from base_models import TGEN_Reranker, TGEN_Model
from embedding_extractor import TokEmbeddingSeq2SeqExtractor, DAEmbeddingSeq2SeqExtractor
from utils import get_training_variables, get_hamming_distance, CONFIGS_MODEL_DIR, \
    get_multi_reference_training_variables

parser = argparse.ArgumentParser()
parser.add_argument('-c', default=None)
args = parser.parse_args()

cfg_path = args.c
if cfg_path is None:
    filenames = os.listdir(CONFIGS_MODEL_DIR)
    filepaths = [os.path.join(CONFIGS_MODEL_DIR, filename) for filename in filenames]
    mod_times = [(os.path.getmtime(x), i) for i, x in enumerate(filepaths)]
    cfg_path = filepaths[max(mod_times)[1]]

cfg = yaml.safe_load(open(cfg_path, 'r'))
texts, das = get_training_variables()
text_embedder = TokEmbeddingSeq2SeqExtractor(texts)
da_embedder = DAEmbeddingSeq2SeqExtractor(das)

texts_mr, da_mr = get_multi_reference_training_variables()
# train_text = np.array(text_embedder.get_embeddings(texts, pad_from_end=True) + [text_embedder.empty_embedding])
# da_embs = da_embedder.get_embeddings(das) + [da_embedder.empty_embedding]

seq2seq = TGEN_Model(da_embedder, text_embedder, cfg_path)
seq2seq.load_models()
seq2seq.full_model.summary()
if "use_prop" in cfg:
    da_mr = da_mr[:int(len(da_mr)*cfg['use_prop'])]
    texts_mr = texts_mr[:int(len(da_mr) * cfg['use_prop'])]
seq2seq.train(da_seq=da_mr,
              text_seq=texts_mr,
              n_epochs=cfg["epoch"],
              valid_size=cfg["valid_size"],
              early_stop_point=cfg["min_epoch"],
              minimum_stop_point=20,
              multi_ref=True)
