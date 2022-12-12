import os
import json
import yaml
import logging.config
import pandas as pd
from pdf2embeddings.embedder import Embedder


models_to_be_run = [
    'Word2Vec_tfidf_weighted',  # comment out as needed
    'Word2Vec',
    'BERT',
    'ELMo',
]


if __name__ == '__main__':
    DATA_DIR = os.getenv('DATA_DIR')
    MODELS_DIR = os.getenv('MODELS_DIR')
    CONFIG_DIR = os.getenv('CONFIG_DIR')
    LOGGING_CONFIG = os.getenv('LOGGING_CONFIG')

    with open(LOGGING_CONFIG, 'r') as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)

    with open(os.path.join(CONFIG_DIR, 'filenames.json'), 'r') as f:
        file_names = json.load(f)

    corpus_filename = "corpus_by_sentence.csv"
    corpus_by_sentence = pd.read_csv(os.path.join(DATA_DIR, "processed", corpus_filename))
    list_of_sentences = corpus_by_sentence['sentence'].values.tolist()
    print("Instantiating Embedder class.")
    embedder = Embedder(list_of_sentences)

    for model in models_to_be_run:
        print(f"Calculating {model} embeddings.")
        if model == 'Word2Vec_tfidf_weighted':
            sentence_embeddings, model_obj, tfidf_vectorizer = embedder.compute_word2vec_embeddings(tfidf_weights=True)
            embedder.save_model(tfidf_vectorizer, MODELS_DIR, file_names[model]['vectorizer_filename'])
            # the line above is specific to Word2Vec with TfIdf vectorizer and cannot be generalized to other models
        elif model == 'Word2Vec':
            sentence_embeddings, model_obj, _ = embedder.compute_word2vec_embeddings(tfidf_weights=False)
        elif model == 'BERT':
            bert_model = 'bert-base-nli-stsb-mean-tokens'  # This line is specific to BERT
            sentence_embeddings, model_obj = embedder.compute_bert_embeddings(bert_model)
        elif model == 'ELMo':
            sentence_embeddings, model_obj = embedder.compute_elmo_embeddings()
        else:
            raise KeyError(f'The model {model} is not recognized as input.')
        print(f"{model} embeddings calculated. Saving model.")
        embedder.save_embeddings(sentence_embeddings, MODELS_DIR, file_names[model]['embeddings_filename'])
        embedder.save_model(model_obj, MODELS_DIR, file_names[model]['model_filename'])
        print(f"{model} model saved. Saving .parquet file.")
        df = embedder.add_embeddings_to_corpus_df(
            os.path.join(DATA_DIR, "processed", corpus_filename), sentence_embeddings, file_names[model]['column_name']
        )
        embedder.df_to_parquet(df, os.path.join(DATA_DIR, "processed", file_names[model]['parquet_filename']))
        print(f"Parquet file saved. All steps done for the {model} model.")
