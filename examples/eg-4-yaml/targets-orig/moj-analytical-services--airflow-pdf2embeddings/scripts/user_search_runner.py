import os
import yaml
import json
import logging.config
from pdf2embeddings.process_user_queries import query_embeddings


if __name__ == '__main__':
    user_search_input = 'cell phone'
    model_name = 'BERT'  # change as appropriate
    DATA_DIR = os.getenv("DATA_DIR")
    CONFIG_DIR = os.getenv('CONFIG_DIR')
    MODELS_DIR = os.getenv("MODELS_DIR")
    LOGGING_CONFIG = os.getenv("LOGGING_CONFIG")
    with open(LOGGING_CONFIG, 'r') as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)
    with open(os.path.join(CONFIG_DIR, 'filenames.json'), 'r') as f:
        file_names = json.load(f)

    tfidf_vectorizer = os.path.join(MODELS_DIR, "tfidf_vectorizer.pickle")

    model = os.path.join(MODELS_DIR, file_names[model_name]["model_filename"])  # this is optional for ELMo and BERT.
    trained_df_path = os.path.join(DATA_DIR, 'processed', file_names[model_name]["parquet_filename"])
    user_input_embedding, trained_df = query_embeddings(
        user_search_input, trained_df_path, file_names[model_name]["column_name"], model_name, model,
        distance_metric='cosine', tfidf_vectorizer=tfidf_vectorizer
    )
    # tfidf_vectorizer is not used (and optional) when model is not 'Word2Vec_TfIdf_weighted'
    if user_input_embedding.size and not trained_df.empty:  # they must not be empty
        print(trained_df.sort_values('metric_distance', ascending=True)[['sentence', 'metric_distance']].
              reset_index(drop=True).head(10))
