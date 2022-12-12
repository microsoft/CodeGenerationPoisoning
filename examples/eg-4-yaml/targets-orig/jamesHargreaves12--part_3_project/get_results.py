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
from beam_search import run_beam_search_with_rescorer, run_nucleus_sampling
from scorer_functions import get_score_function
from utils import get_training_variables, apply_absts, get_abstss_train, get_test_das, START_TOK, END_TOK, PAD_TOK, \
    get_true_sents, get_abstss_test, get_training_das_texts, RESULTS_DIR, CONFIGS_MODEL_DIR, CONFIGS_DIR, postprocess, \
    get_multi_reference_training_variables, tgen_postprocess


def do_beam_search(beam_size, cfg, models, das_test, da_embedder, text_embedder, true_vals, absts):
    print("Beam size = {} ".format(beam_size))
    beam_save_path = cfg.get('beam_save_path', '')
    if beam_save_path:
        beam_save_path = beam_save_path.format(beam_size)

    parent = os.path.abspath(os.path.join(beam_save_path, os.pardir))
    if not os.path.exists(parent):
        os.makedirs(parent)

    # This is a horrible hack
    alpha = 0.65 if 'alpha' not in cfg else cfg['alpha'][beam_size]
    if "train_reranker" in cfg and cfg["train_reranker"]["output_type"] in ["pair"]:
        scorer_func = PairwiseReranker(da_embedder, text_embedder, cfg["trainable_reranker_config"])
    else:
        scorer_func = get_score_function(cfg['scorer'], cfg, models, true_vals, beam_size, alpha)
    max_pred_len = 60

    non_greedy_score_func = None
    if "non_greedy_scorer" in cfg:
        non_greedy_score_func = get_score_function(cfg['non_greedy_scorer'], cfg, models, true_vals, beam_size, alpha)
    if "greedy_complete_at" in cfg:
        greedy_complete = cfg["greedy_complete_at"]
    else:
        greedy_complete_rate = cfg.get("greedy_complete_rate", max_pred_len + 1)
        greedy_complete = [list(range(greedy_complete_rate, max_pred_len, greedy_complete_rate))]

    for gred_comp in greedy_complete:
        if gred_comp == ['random']:
            gred_comp = sorted(random.choices(list(range(3, 15)), k=random.randint(1, 4)))
        preds = run_beam_search_with_rescorer(scorer_func, models, das_test, beam_size,
                                              only_rerank_final=cfg['only_rerank_final'],
                                              save_final_beam_path=beam_save_path,
                                              greedy_complete=gred_comp,
                                              max_pred_len=max_pred_len,
                                              save_progress_path=cfg.get('save_progress_file', None),
                                              also_rerank_final=cfg.get('also_rerank_final', False),
                                              cfg=cfg,
                                              non_greedy_rescorer=non_greedy_score_func,
                                              length_norm_alpha=alpha if cfg.get('non_greedy_scorer', None) == 'length_normalised' else None)
        preds = [[x for x in pred if x not in [START_TOK, END_TOK, PAD_TOK]] for pred in preds]
        if "res_save_format" in cfg:
            save_filename = cfg["res_save_format"].format(beam_size)
        elif cfg['scorer'] in ['surrogate', 'greedy_decode_surrogate', 'surrogate_rev']:
            # Example surrogate-regression_reranker_relative-categorical_order_10_10.txt
            surrogate_cfg = yaml.safe_load(open(cfg["trainable_reranker_config"], 'r+'))
            save_filename = "{}-{}-{}-{}-{}.txt".format(cfg['scorer'], surrogate_cfg["output_type"],
                                                        surrogate_cfg["logprob_preprocess_type"],
                                                        surrogate_cfg['beam_size'], beam_size)
            save_filename = cfg.get("save_prefix", "") + save_filename

        else:
            raise ValueError('Not saving files any where')
        save_filename_update = "-".join([str(x) for x in gred_comp]) + save_filename
        save_path = os.path.join(RESULTS_DIR, save_filename_update)
        if cfg.get("re-lexicalise", True):
            print("Applying abstract")
            post_abstr = apply_absts(absts, preds)
        else:
            print("Abstract not applied")
            post_abstr = preds
        print("Saving to {}".format(save_path))
        parent = os.path.abspath(os.path.join(save_path, os.pardir))
        if not os.path.exists(parent):
            os.makedirs(parent)
        with open(save_path, "w+") as out_file:
            for pa in post_abstr:
                # out_file.write(" ".join(pa) + '\n')
                if cfg.get("re-lexicalise", True):
                    out_file.write(postprocess(" ".join(pa)) + '\n')
                else:
                    out_file.write(" ".join(pa) + '\n')
        print("Official bleu score:", test_res_official(save_filename_update))


def do_nucleus_sampling(models, das_test, cfg, absts):
    preds = run_nucleus_sampling(models, das_test, max_pred_len=60, cfg=cfg)
    preds = [[x for x in pred if x not in [START_TOK, END_TOK, PAD_TOK]] for pred in preds]
    if "res_save_format" in cfg:
        save_filename = cfg["res_save_format"].format(1)
    else:
        raise ValueError('Not saving files any where')

    if cfg.get("re-lexicalise", True):
        print("Applying abstract")
        post_abstr = apply_absts(absts, preds)
    else:
        print("Abstract not applied")
        post_abstr = preds

    save_path = os.path.join(RESULTS_DIR, save_filename)
    print("Saving to {}".format(save_path))
    parent = os.path.abspath(os.path.join(save_path, os.pardir))
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(save_path, "w+") as out_file:
        for pa in post_abstr:
            # out_file.write(" ".join(pa) + '\n')
            if cfg.get("re-lexicalise", True):
                out_file.write(postprocess(" ".join(pa)) + '\n')
            else:
                out_file.write(" ".join(pa) + '\n')
    print("Official bleu score:", test_res_official(save_filename))

if __name__ == '__main__':
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
    if "trainable_reranker_config" in cfg:
        cfg["train_reranker"] = yaml.safe_load(open(cfg["trainable_reranker_config"], "r"))
    print("Config:")
    [print("\t{}: {}".format(k, v)) for k, v in cfg.items()]
    print("*******")

    texts, das = get_training_variables()
    text_embedder = TokEmbeddingSeq2SeqExtractor(texts)
    da_embedder = DAEmbeddingSeq2SeqExtractor(das)

    das_test = get_test_das()
    if "get_train_beam" in cfg and cfg["get_train_beam"]:
        _, das_test = get_multi_reference_training_variables()

    true_vals = get_true_sents()
    models = TGEN_Model(da_embedder, text_embedder, cfg['tgen_seq2seq_config'])
    models.load_models()

    if cfg.get("first_x", False):
        das_test = das_test[:cfg['first_x']]

    absts = get_abstss_test()
    if cfg.get('nucleus_sampling', False):
        do_nucleus_sampling(models, das_test, cfg, absts)
    else:
        for beam_size in cfg["beam_sizes"]:
            do_beam_search(beam_size, cfg, models, das_test, da_embedder, text_embedder, true_vals, absts)

    print_results()
