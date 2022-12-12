from pathlib import Path
import os

import yaml
from sqlalchemy import create_engine
from sqlalchemy.engine import url
from sqlalchemy.orm import sessionmaker

# ENV only used if we run the code outside docker
try:
    config_folder = os.environ['VOLUME_DIR'] + '/irk'
except KeyError:
    config_folder = '/usr/src/app/conf'

irk_conf_path = Path(config_folder + '/irk.yml')
with open(irk_conf_path) as f:
    irk_conf = yaml.safe_load(f)

carriage_conf_path = Path(config_folder + '/carriage.yml')
with open(carriage_conf_path) as f:
    carriage_conf = yaml.safe_load(f)

led_mapping_conf_path = Path(config_folder + '/led_mapping.yml')
with open(led_mapping_conf_path) as f:
    led_mapping_conf = yaml.safe_load(f)

hashes_conf_path = Path(config_folder + '/config_hashes.ini')

modules_section = irk_conf['modules']

# DB setup
db_connect_url = url.URL(drivername=os.environ['DATABASE_DIALECT'],
                         username=os.environ['DATABASE_USER'],
                         password=os.environ['DATABASE_PASSWORD'],
                         host=os.environ['DATABASE_HOSTNAME'],
                         port=os.environ['DATABASE_PORT'],
                         database=os.environ['DATABASE_NAME'])

db_host = os.environ['DATABASE_HOSTNAME']
db_port = os.environ['DATABASE_PORT']

engine = create_engine(db_connect_url)

DBSession = sessionmaker(bind=engine)
session = DBSession()