import os
import yaml
import logging.config
from pdf2embeddings.scraper import DocumentScraper
from pdf2embeddings.arrange_text import CorpusGenerator


if __name__ == "__main__":
    DATA_DIR = os.getenv('DATA_DIR')
    CONFIG_DIR = os.getenv('CONFIG_DIR')
    LOGGING_CONFIG = os.getenv('LOGGING_CONFIG')

    with open(LOGGING_CONFIG, 'r') as f:
        config = yaml.safe_load(f)
    logging.config.dictConfig(config)

    pdfs_folder = os.path.join(DATA_DIR, 'raw', 'pdfs')
    json_path = os.path.join(CONFIG_DIR, 'words_to_replace.json')
    scraper = DocumentScraper(pdfs_folder, json_path)
    df_by_page = scraper.document_corpus_to_pandas_df()
    generator = CorpusGenerator(df_by_page)
    df_by_sentence = generator.df_by_page_to_df_by_sentence()

    df_by_page.to_csv(os.path.join(DATA_DIR, 'processed', 'corpus_by_page.csv'))
    df_by_sentence.to_csv(os.path.join(DATA_DIR, 'processed', 'corpus_by_sentence.csv'), index=False)

    print("Finished!")
