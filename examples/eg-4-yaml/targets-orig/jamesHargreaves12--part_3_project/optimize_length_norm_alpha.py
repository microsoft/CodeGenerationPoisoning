import argparse
import os
import random
import sys
import yaml
from pathlib import Path

from base_models import TGEN_Model, TGEN_Reranker, PairwiseReranker
from e2e_metrics.metrics.pymteval import BLEUScore
from embedding_extractor import TokEmbeddingSeq2SeqExtractor, DAEmbeddingSeq2SeqExtractor
from get_results_bleu_scores import print_results, test_res_official
from beam_search import run_beam_search_with_rescorer
from scorer_functions import get_score_function
from utils import get_training_variables, apply_absts, get_abstss_train, get_test_das, START_TOK, END_TOK, PAD_TOK, \
    get_true_sents, get_abstss_test, get_training_das_texts, RESULTS_DIR, CONFIGS_MODEL_DIR, CONFIGS_DIR, postprocess, \
    get_multi_reference_training_variables, tgen_postprocess

parser = argparse.ArgumentParser()
parser.add_argument('-c', default=None)
args = parser.parse_args()

cfg_path = args.c
if cfg_path is None:
    filenames = os.listdir(CONFIGS_DIR)
    filepaths = [os.path.join(CONFIGS_DIR, filename) for filename in filenames]
    mod_times = [(os.path.getmtime(x), i) for i, x in enumerate(filepaths) if not os.path.isdir(x)]
    cfg_path = filepaths[max(mod_times)[1]]

print("Using config from: {}".format(cfg_path))
cfg = yaml.safe_load(open(cfg_path, "r"))
cfg['scorer'] = 'length_normalised'
print("Config:")
[print("\t{}: {}".format(k, v)) for k, v in cfg.items()]
print("*******")

texts, das = get_training_variables()
text_embedder = TokEmbeddingSeq2SeqExtractor(texts)
da_embedder = DAEmbeddingSeq2SeqExtractor(das)
models = TGEN_Model(da_embedder, text_embedder, cfg['tgen_seq2seq_config'])
models.load_models()

valid_size = models.cfg['valid_size']

mr_texts, mr_das = get_multi_reference_training_variables()
valid_das = mr_das[-valid_size:]
valid_texts = mr_texts[-valid_size:]
beam_size = cfg['beam_size']

results = []
for alpha in cfg['alpha_vals']:
    print("Testinig Alpha value = {} ".format(alpha))
    scorer_func = get_score_function(cfg['scorer'], cfg, models, valid_texts, beam_size, alpha)

    max_pred_len = 60
    if "greedy_complete_at" in cfg:
        greedy_complete = cfg["greedy_complete_at"]
    else:
        greedy_complete_rate = cfg.get("greedy_complete_rate", max_pred_len + 1)
        greedy_complete = [list(range(greedy_complete_rate, max_pred_len, greedy_complete_rate))]

    preds = run_beam_search_with_rescorer(scorer_func, models, valid_das, beam_size,
                                          greedy_complete=[],
                                          max_pred_len=max_pred_len,
                                          cfg=cfg)

    preds = [[x for x in pred if x not in [START_TOK, END_TOK, PAD_TOK]] for pred in preds]
    save_filename = 'len_norm_opt_{}_{}.txt'.format(beam_size, str(alpha).replace('.','*'))
    save_path = os.path.join(RESULTS_DIR, save_filename)

    parent = os.path.abspath(os.path.join(save_path, os.pardir))
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(save_path, "w+") as out_file:
        for pred in preds:
            out_file.write(" ".join(pred) + '\n')

    bleu = BLEUScore()
    for sents_ref, sent_sys in zip(valid_texts, preds):
        bleu.append([START_TOK] + sent_sys + [END_TOK], sents_ref)

    total_bleu_score = bleu.score()
    print("Bleu Score:", total_bleu_score)
    results.append((alpha, total_bleu_score))
print(results)
