"""
MIT License

Copyright (c) 2022 Texas Tech University

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""
This file is part of MetricsBuilderAPI.

Author:
    Jie Li, jie.li@ttu.edu
"""
import yaml
from pathlib import Path

from metrics_builder import logger
log = logger.get_logger(__name__)

def parse_config():
    """parse_config Parse Config

    Parse configuration files

    Returns:
        dict: Configuration in json format
    """
    cfg = []
    config_path = Path(__file__).resolve().parent.parent
    try:
        with open(f'{config_path}/config.yml', 'r') as ymlfile:
            cfg = yaml.safe_load(ymlfile)
            return cfg
    except Exception as err:
        log.error(f"Parsing Configuration Error: {err}")


def init_tsdb_connection(partition: str):
    """init_tsdb_connection Initialize TimeScaleDB Connection

    Initialize TimeScaleDB Connection according to the configuration
    """
    config_tsdb = parse_config()['timescaledb']

    db_host = config_tsdb['host']
    db_port = config_tsdb['port']
    db_user = config_tsdb['username']
    db_pswd = config_tsdb['password']
    db_name = f'{partition}_db'
    db_dbnm = config_tsdb[db_name]
    connection = f"postgresql://{db_user}:{db_pswd}@{db_host}:{db_port}/{db_dbnm}"
    return connection