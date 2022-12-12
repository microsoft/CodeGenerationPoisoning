import logging
from datetime import datetime
import os

import yaml


formatter = '%(levelname)s : %(asctime)s : %(message)s'
logging.basicConfig(format=formatter)

DEFAULT_DEV_FILEPATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..',
    'config/dev.yml'
)
dev_conf = yaml.safe_load(open(DEFAULT_DEV_FILEPATH))
filename = os.path.join(
    dev_conf['LOGDIR'],
    f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
)
file_handler = logging.FileHandler(
    filename=filename
)
file_handler.setFormatter(logging.Formatter(formatter))


class Logger:

    @staticmethod
    def d(tag: str, message: str):
        """debug log"""
        logger = logging.getLogger('fin_app')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(file_handler)
        logger.debug('[%s] %s', tag, message)

    @staticmethod
    def i(tag: str, message: str):
        """infomation log"""
        logger = logging.getLogger('fin_app')
        logger.setLevel(logging.INFO)
        logger.addHandler(file_handler)
        logger.info('[%s] %s', tag, message)

    @staticmethod
    def e(tag: str, message: str):
        """error log"""
        logger = logging.getLogger('fin_app')
        logger.setLevel(logging.ERROR)
        logger.addHandler(file_handler)
        logger.error('[%s] %s', tag, message)

    @staticmethod
    def w(tag: str, message: str):
        """warning log"""
        logger = logging.getLogger('fin_app')
        logger.setLevel(logging.WARNING)
        logger.addHandler(file_handler)
        logger.warn('[%s] %s', tag, message)
