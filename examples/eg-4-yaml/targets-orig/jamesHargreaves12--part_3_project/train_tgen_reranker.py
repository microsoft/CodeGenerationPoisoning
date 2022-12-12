import argparse
import os
import yaml
import numpy as np
import matplotlib.pyplot as plt

from base_models import TGEN_Reranker
from embedding_extractor import TokEmbeddingSeq2SeqExtractor, DAEmbeddingSeq2SeqExtractor
from utils import get_training_variables, get_hamming_distance, get_true_sents, get_test_das
parser = argparse.ArgumentParser()
parser.add_argument('-c', default=None)
args = parser.parse_args()

cfg_path = args.c


cfg = yaml.load(open(cfg_path, "r"))
texts, das = get_training_variables()
text_embedder = TokEmbeddingSeq2SeqExtractor(texts)
da_embedder = DAEmbeddingSeq2SeqExtractor(das)
train_text = np.array(text_embedder.get_embeddings(texts, pad_from_end=False) + [text_embedder.empty_embedding])
das_inclusions = np.array([da_embedder.get_inclusion(da) for da in das] + [da_embedder.empty_inclusion])
reranker = TGEN_Reranker(da_embedder, text_embedder, cfg_path)
if os.path.exists(cfg["reranker_loc"]) and cfg["load_reranker"]:
    reranker.load_model()

reranker.train(das_inclusions, train_text, cfg["epoch"], cfg["valid_size"])
if cfg["plot_reranker_stats"]:
    das = get_test_das()
    texts = [x[0] for x in get_true_sents()]
    # texts, das, = get_training_variables()

    da_embeddings = da_embedder.get_embeddings(das)
    text_embeddings = text_embedder.get_embeddings(texts, pad_from_end=False)
    print("Loading")
    ham_dists = [reranker.get_pred_hamming_dist(list(x), y) for x, y in list(zip(text_embeddings, da_embeddings))]
    print("Loaded")
    # preds = reranker.predict(train_text)
    # ham_dists = [get_hamming_distance(x, y) for x, y in zip(preds, das_inclusions)]
    filter_hams = [x for x in ham_dists if x != 0]
    plt.hist(filter_hams)
    plt.show()
