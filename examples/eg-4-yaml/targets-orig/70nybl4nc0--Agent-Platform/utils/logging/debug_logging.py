import logging
import logging.config
import yaml

'''
with open('./debug.yaml', 'r') as f:
    config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
'''
def info(msg:str):
    logger = logging.getLogger(__name__)
    logger.info(msg)
    
def debug(msg:str):
    logger = logging.getLogger(__name__)
    logger.debug(msg)
