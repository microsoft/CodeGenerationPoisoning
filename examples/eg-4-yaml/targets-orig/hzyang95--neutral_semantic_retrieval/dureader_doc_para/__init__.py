import yaml
import logging
import logging.config
import pathlib

ROOT_DIR = pathlib.Path(__file__).parent.parent
logging_conf = '{}/conf/logging.yaml'.format(ROOT_DIR)
with open(logging_conf, 'r') as f_conf:
    dict_conf = yaml.load(f_conf)
    dict_conf['handlers']['file']['filename'] = dict_conf['handlers']['file']['filename'].replace('$ROOT_DIR', str(ROOT_DIR))
    logging.config.dictConfig(dict_conf)
