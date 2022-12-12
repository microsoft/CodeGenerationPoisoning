import argparse
import os
import pickle
import sys
from collections import Counter

import msgpack
import numpy as np
import yaml
import matplotlib.pyplot as plt
from keras.utils import to_categorical
from sklearn.metrics import confusion_matrix
from tqdm import tqdm

from utils import get_training_variables, START_TOK, PAD_TOK, END_TOK, get_multi_reference_training_variables, \
    get_final_beam, get_test_das, get_true_sents, TRAIN_BEAM_SAVE_FORMAT, TEST_BEAM_SAVE_FORMAT, RESULTS_DIR, \
    CONFIGS_MODEL_DIR, get_section_cutoffs, get_section_value, get_regression_vals
from base_models import TGEN_Model, TrainableReranker, PairwiseReranker
from e2e_metrics.metrics.pymteval import BLEUScore
from embedding_extractor import TokEmbeddingSeq2SeqExtractor, DAEmbeddingSeq2SeqExtractor
from beam_search import run_beam_search_with_rescorer
from scorer_functions import get_score_function


def get_scores_ordered_beam(cfg, da_embedder, text_embedder, beam_save_path=None):
    print("Loading Training Data")
    beam_size = cfg["beam_size"]
    train_texts, train_das = get_multi_reference_training_variables()
    if beam_save_path is None:
        beam_save_path = TRAIN_BEAM_SAVE_FORMAT.format(beam_size, cfg["tgen_seq2seq_config"].split('.')[0].split('/')[-1])
    if not os.path.exists(beam_save_path):
        models = TGEN_Model(da_embedder, text_embedder, cfg["tgen_seq2seq_config"])
        models.load_models()
        print("Creating test final beams")
        scorer = get_score_function('identity', cfg, models, None, beam_size)
        run_beam_search_with_rescorer(scorer, models, train_das, beam_size, cfg, only_rerank_final=True,
                                      save_final_beam_path=beam_save_path)
    bleu = BLEUScore()
    final_beam = pickle.load(open(beam_save_path, "rb"))
    text_seqs = []
    da_seqs = []
    scores = []
    log_probs = []
    with_ref_train_flag = cfg["with_refs_train"]
    num_ranks = cfg["num_ranks"]
    cut_offs = get_section_cutoffs(num_ranks)
    regression_vals = get_regression_vals(num_ranks, with_ref_train_flag)
    if cfg["output_type"] != 'pair':
        print("Cut off values:", cut_offs)
        print("Regression vals:", regression_vals)

    only_top = cfg.get("only_top", False)
    only_bottom = cfg.get("only_bottom", False)
    merge_middles = cfg["merge_middle_sections"]
    if only_top:
        print("Only using top value")
    if merge_middles and only_top:
            print("Ignoring only top since have merge_middle_sections set")
    training_vals = list(zip(final_beam, train_texts, train_das))
    training_vals = training_vals[:cfg.get("use_size", len(training_vals))]
    for beam, real_texts, da in tqdm(training_vals):
        beam_scores = []
        if with_ref_train_flag:
            # I am not sure how to do log probs?
            text_seqs.extend(real_texts)
            da_seqs.extend([da for _ in real_texts])
            scores.extend([0 for _ in real_texts])

        for i,path in enumerate(beam):
            bleu.reset()
            hyp = [x for x in text_embedder.reverse_embedding(path[1]) if x not in [START_TOK, END_TOK, PAD_TOK]]
            bleu.append(hyp, [x for x in real_texts if x not in [START_TOK, END_TOK]])
            beam_scores.append((bleu.score(), hyp, path))

            # log_probs.append(i)

        for i, (score, hyp, path) in enumerate(sorted(beam_scores, reverse=True)):
            text_seqs.append([START_TOK] + hyp + [END_TOK])
            da_seqs.append(da)
            if cfg["output_type"] in ['bleu', 'pair']:
                scores.append(score)
            elif cfg["output_type"] == 'order_discrete':
                scores.append(to_categorical([i], num_classes=beam_size))
            elif cfg["output_type"] in ['regression_ranker', 'regression_reranker_relative']:
                scores.append(i / (beam_size - 1))
            elif cfg["output_type"] in ['regression_sections', 'binary_classif']:
                val = (i / (beam_size - 1))
                regression_val = get_section_value(val, cut_offs, regression_vals,
                                                   merge_middles, only_top, only_bottom)
                scores.append(regression_val) # converts range from [0,1] to [-1,1] (which has mean of 0)
            else:
                raise ValueError("Unknown output type")

            log_probs.append([path[0]])

    text_seqs = np.array(text_embedder.get_embeddings(text_seqs, pad_from_end=False))
    da_seqs = np.array(da_embedder.get_embeddings(da_seqs))

    if cfg["output_type"] in ['regression_ranker', 'bleu', 'regression_reranker_relative', 'pair',
                              'regression_sections', 'binary_classif']:
        # print("SCORES: ", Counter(scores))
        scores = np.array(scores).reshape((-1, 1))
    elif cfg["output_type"] == 'order_discrete':
        scores = np.array(scores).reshape((-1, beam_size))

    log_probs = np.array(log_probs)
    return text_seqs, da_seqs, scores, log_probs


parser = argparse.ArgumentParser()
parser.add_argument('-c', default=None)
args = parser.parse_args()

cfg_path = args.c
if cfg_path is None:
    filenames = os.listdir(CONFIGS_MODEL_DIR)
    filepaths = [os.path.join(CONFIGS_MODEL_DIR, filename) for filename in filenames]
    mod_times = [(os.path.getmtime(x), i) for i, x in enumerate(filepaths)]
    cfg_path = filepaths[max(mod_times)[1]]

print("Using config from: {}".format(cfg_path))
cfg = yaml.safe_load(open(cfg_path, "r"))
print("Config:")
[print("\t{}: {}".format(k,v)) for k,v in cfg.items()]
print("*******")
texts, das = get_multi_reference_training_variables()
da_embedder = DAEmbeddingSeq2SeqExtractor(das)
# This is a very lazy move
texts_flat, _ = get_training_variables()
text_embedder = TokEmbeddingSeq2SeqExtractor(texts_flat)

if cfg['output_type'] != 'pair':
    reranker = TrainableReranker(da_embedder, text_embedder, cfg_path)
else:
    reranker = PairwiseReranker(da_embedder, text_embedder, cfg_path)

if reranker.load_model():
    print("WARNING THE TRAINING START POINT IS AN ALREADY TRAINED MODEL")


if cfg["train"]:
    print("Training")
    text_seqs, da_seqs, scores, log_probs = get_scores_ordered_beam(cfg, da_embedder, text_embedder,
                                                                    beam_save_path=cfg.get("beam_save_path", None))
    if type(scores[0][0]) ==  int:
        print("Score Distributions:")
        print(Counter([x[0] for x in scores]))
    print("LP distributions")
    print("min", min(log_probs))
    print("max", max(log_probs))
    print("mean", sum(log_probs)/len(log_probs))
    if cfg['output_type'] != 'pair':
        reranker.train(text_seqs, da_seqs, scores, log_probs, cfg["epoch"], cfg["valid_size"],
                   cfg.get("min_training_passes", 5))
    else:
        reranker.train(text_seqs, da_seqs, scores, log_probs, cfg["epoch"], cfg["valid_size"], cfg["num_ranks"],
                       cfg.get("only_bottom", False),
                       cfg.get("only_top", False),
                       cfg.get("min_training_passes", 5))


if cfg["show_reranker_post_training_stats"]:
    test_das = get_test_das()
    test_texts = get_true_sents()
    final_beam_path = TEST_BEAM_SAVE_FORMAT.format(10)

    if not os.path.exists(final_beam_path):
        print("Creating final beams file")
        models = TGEN_Model(da_embedder, text_embedder, cfg['tgen_seq2seq_config'])
        models.load_models()
        scorer = get_score_function('identity', cfg, models, None, 10)
        run_beam_search_with_rescorer(scorer, models, test_das, 10, only_rerank_final=True,
                                      save_final_beam_path=final_beam_path)

    bleu = BLEUScore()
    test_da_embs = da_embedder.get_embeddings(test_das)
    final_beam = pickle.load(open(final_beam_path, 'rb+'))
    all_reals = []
    all_preds = []
    for da_emb, beam, true in zip(test_da_embs, final_beam, test_texts):
        real_scores = []
        lp_probs_beam = [x[0] for x in beam]
        for i, path in enumerate(beam):
            logp, text_emb, _ = path
            toks = text_embedder.reverse_embedding(text_emb)
            lp_rank = [sum([1 for x in lp_probs_beam if x > logp + 0.000001])]
            lp_rank_cat = to_categorical([lp_rank], num_classes=10)
            da_seqs = np.array([da_emb])
            text_seqs = np.array(text_embedder.get_embeddings([toks], pad_from_end=False))
            score = reranker.predict_bleu_score(text_seqs, da_seqs, lp_rank_cat)
            score = 9 - np.argmax(score[0])
            all_preds.append(score)
            pred = [x for x in toks if x not in [START_TOK, END_TOK, PAD_TOK]]
            bleu.reset()
            bleu.append(pred, true)
            real_scores.append((bleu.score(), i))
        sorted_reals = sorted(real_scores)
        all_reals.extend([i for _, i in sorted_reals])
    print(confusion_matrix(all_reals, all_preds))

    beam_texts = [[text for text, _ in beam] for beam in final_beam]
    beam_tok_logprob = [[tp for _, tp in beam] for beam in final_beam]
    # test_text_embs = [text_embedder.get_embeddings(beam) for beam in beam_texts]
    mapping = []
    order_correct_surrogate = 0
    order_correct_seq2seq = 0
    for texts, da_emb, tp_emb, true_texts in zip(beam_texts, test_da_embs, beam_tok_logprob, test_texts):
        text_seqs = np.array(text_embedder.get_embeddings(texts, pad_from_end=False))
        da_seqs = np.array([da_emb for _ in range(len(text_seqs))])
        tp_seqs = np.array(tp_emb).reshape(-1, 1)
        preds = reranker.predict_bleu_score(text_seqs, da_seqs, tp_seqs)
        beam_scores = []
        for i, (pred, text, tp) in enumerate(zip(preds, texts, tp_seqs)):
            bleu.reset()
            bleu.append(text, true_texts)
            real = bleu.score()
            mapping.append((pred[0], real))
            beam_scores.append((real, pred[0], i, tp[0]))
        sorted_beam_scores = sorted(beam_scores, reverse=True)
        best = sorted_beam_scores[0][2]
        best_surrogate = sorted(beam_scores, key=lambda x: x[1])[0][2]
        best_seq2seq = sorted(beam_scores, key=lambda x: x[3], reverse=True)[0][2]
        if best == best_surrogate:
            order_correct_surrogate += 1
        if best == best_seq2seq:
            order_correct_seq2seq += 1
    print(len(beam_texts), order_correct_surrogate, order_correct_seq2seq)

    # print(mapping)
    preds = [x for x, _ in mapping]
    reals = [x for _, x in mapping]
    plt.scatter(reals, preds, alpha=0.05)
    plt.plot([0, 1], [0, 1], color='red')
    plt.xlabel("Real Score")
    plt.ylabel("Predicted")
    plt.show()
