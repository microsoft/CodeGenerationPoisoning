import os
import yaml
import logging
from datetime import datetime
from pathlib import Path


def set_logger():
    global logger
    global ftp_logger

    # logger setting
    today_str = datetime.now().strftime('%Y%m%d')
    log_dir = os.path.join(os.curdir, 'log')
    log_file = os.path.join(log_dir, f'{today_str}.log')
    parent_dir = Path(log_dir)
    parent_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file)
    #fh.setLevel(logging.INFO)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    # formatter = logging.Formatter(
    #     '%(asctime)s - %(message)s',
    #     datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    # remove existing handler
    for h in logger.handlers:
        logger.removeHandler(h)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False

    ftp_logger = logging.getLogger('ftp_manager')
    #ftp_logger.setLevel(logging.INFO)
    ftp_logger.addHandler(fh)


def get_cfg(config_file):
    """
    get configuration and transform to dict data

    :param str config_file: config file path (.yml)
    :return: config data
    """

    with open(config_file) as f:
        cfg = yaml.safe_load(f)

    # ftp setting
    ftp_cfg = cfg['ftp']

    return ftp_cfg