import numpy as np
import os
import pickle
import torch
from tqdm import tqdm
import shutil
import yaml

from utils.vocab import WordsVocabulary, CharsVocabulary
from utils.preprocessing import preprocess_sentence


def create_objects(
    corpus, datasets, path, max_word_length, max_words, compute_tensors=True
):
    assert os.path.exists(path), "path not found"

    word_vocabulary = WordsVocabulary()
    char_vocabulary = CharsVocabulary()
    max_word_len_tmp = 0

    input_params = {
        "corpus_name": corpus,
        "max_word_length": max_word_length,
        "max_words": max_words,
    }
    print(f"Corpus : {corpus}")

    computed_params = {}
    for mode, dataset in datasets.items():
        for word in dataset:
            if len(word) > max_word_len_tmp:
                max_word_len_tmp = len(word)
            word_vocabulary.add_word(word)
            char_vocabulary.add_word(word)
        computed_params[f"tokens_{mode}"] = len(dataset)
    char_vocabulary.process()
    word_vocabulary.sort(max_words)

    if max_word_length:
        word_length = min(max_word_length, max_word_len_tmp)
    else:
        word_length = max_word_len_tmp
    print(f"Word length : {word_length}")
    computed_params["word_length"] = word_length

    total_tokens = sum([len(ds) for mode, ds in datasets.items()])
    print(f"Total number of words : {total_tokens}")
    print(f"Size word vocabulary: {len(word_vocabulary.idx2word)}")
    print(f"Size character vocabulary: {len(char_vocabulary.idx2char)}\n")
    computed_params[f"tokens_total"] = total_tokens

    path_char_voc = os.path.join(path, "idx2char.pkl")
    with open(path_char_voc, "wb") as file:
        pickle.dump(char_vocabulary.idx2char, file)
    print(f"\nCharacter vocabulary saved to {path_char_voc}")

    path_word_voc = os.path.join(path, "idx2word.pkl")
    with open(path_word_voc, "wb") as file:
        pickle.dump(word_vocabulary.idx2word, file)
    print(f"Word vocabulary saved to {path_word_voc}")

    computed_params["char_vocab_size"] = len(char_vocabulary.idx2char)
    computed_params["word_vocab_size"] = len(word_vocabulary.idx2word)
    parameters = {
        "input_params": input_params,
        "computed_params": computed_params,
    }

    path_parameters = os.path.join(path, "data.yaml")
    save_params(parameters, path_parameters)
    print(f"Parameters saved to {path_parameters}")

    if compute_tensors:
        print("Computing tensors ..")
        for mode, dataset in datasets.items():
            output_chars = torch.zeros(
                (len(dataset), word_length), dtype=torch.uint8
            )
            output_words = torch.zeros(len(dataset), dtype=torch.long)

            for i, word in enumerate(tqdm(dataset, desc=mode)):
                output_chars[i] = char_vocabulary.to_idx(word, word_length)
                output_words[i] = word_vocabulary.to_idx(word)
            path_chars = os.path.join(path, mode, "chars.pt")
            torch.save(output_chars, path_chars)
            path_words = os.path.join(path, mode, "words.pt")
            torch.save(output_words, path_words)
            print(f"Tensors {mode} saved to {path_chars} and {path_words}\n")
    return computed_params


def initialize_dataset(
    corpus_name,
    max_word_length=None,
    max_words=None,
    data_splits=[0.7, 0.2, 0.1],
):
    print(f"Initializing dataset ..")
    assert abs(sum(data_splits) - 1) < 0.0001
    if corpus_name == "penn-treebank":

        from torchnlp.datasets import penn_treebank_dataset

        train, val, test = penn_treebank_dataset(
            train=True, dev=True, test=True
        )
        train = preprocess_sentence(train)
        val = preprocess_sentence(val)
        test = preprocess_sentence(test)
        datasets = {
            "train": train,
            "val": val,
            "test": test,
        }

    elif corpus_name == "brown":
        import nltk

        nltk.download("brown")
        from nltk.corpus import brown

        processed_txt = []
        for s in brown.sents():
            processed_txt += preprocess_sentence(s)

        n_tokens = len(processed_txt)
        split_n = [int(s * n_tokens) for s in np.cumsum(data_splits)]
        train = processed_txt[: split_n[0]]
        val = processed_txt[split_n[0] : split_n[1]]
        test = processed_txt[split_n[1] :]
        datasets = {
            "train": train,
            "val": val,
            "test": test,
        }

    else:
        raise ValueError(f"Corpus {corpus_name} not supported")

    root_path = os.path.join("data", corpus_name, "objects")
    if os.path.exists(root_path):
        shutil.rmtree(root_path)
    os.makedirs(root_path + "/train", exist_ok=True)
    os.makedirs(root_path + "/val", exist_ok=True)
    os.makedirs(root_path + "/test", exist_ok=True)

    return create_objects(
        corpus_name, datasets, root_path, max_word_length, max_words
    )


def load_params(path):
    with open(path, "r") as file:
        dictionary = yaml.safe_load(file)

    return dictionary


def save_params(dictionary, path):
    with open(path, "w") as file:
        yaml.dump(dictionary, file)


def get_data_params(config_data, force_update=False):
    path_objects = os.path.join("data", config_data["corpus_name"], "objects")
    path_objects_params = os.path.join(path_objects, "data.yaml")
    try:
        objects_params = load_params(path_objects_params)
        if objects_params["input_params"] == config_data and not force_update:
            if check_files(path_objects):
                return objects_params["computed_params"], path_objects
    except (FileNotFoundError, KeyError):
        pass
    print("Updating data objects..")
    return initialize_dataset(**config_data), path_objects


def check_files(path_objects):
    paths = [
        os.path.join(path_objects, mode, f)
        for mode in ["train", "val", "test"]
        for f in ["chars.pt", "words.pt"]
    ]
    paths += [
        os.path.join(path_objects, "idx2word.pkl"),
        os.path.join(path_objects, "idx2char.pkl"),
    ]
    if np.all([os.path.exists(p) for p in paths]):
        return True
    return False
