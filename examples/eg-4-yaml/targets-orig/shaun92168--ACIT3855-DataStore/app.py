import connexion
from connexion import NoContent

from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from base import Base
from scan_in import ScanIn
from body_info import BodyInfo
import dateutil.parser
import yaml
import json
import os
import logging.config
from threading import Thread
from pykafka import KafkaClient, common
from flask_cors import CORS, cross_origin

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())


# DB_ENGINE = create_engine('sqlite:///records.sqlite')
DB_ENGINE = create_engine('mysql+pymysql://' + app_config['datastore']['user'] + ':' +
                          app_config['datastore']['password'] + '@' + app_config['datastore']['hostname'] +
                          ':' + str(app_config['datastore']['port']) + '/' + app_config['datastore']['db'])
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

logger = logging.getLogger('basicLogger')

def parse_datetime(datestring):
     return dateutil.parser.parse(datestring)

def get_scan_in(startDate, endDate):
    """ Get scan in records from the data store """

    if startDate != "" and endDate !="":

        start = parse_datetime(startDate)
        end = parse_datetime(endDate)

        results_list = []

        session = DB_SESSION()

        results = []

        results = session.query(ScanIn).filter(and_(ScanIn.date_created >= start, ScanIn.date_created <= end))

        for result in results:
            results_list.append(result.to_dict())
            print(result.to_dict())

        session.close()
        return results_list, 200

    else:
        return NoContent, 400

def get_body_info(startDate, endDate):
    """ Get body info records from the data store """

    if startDate != "" and endDate != "":

        start = parse_datetime(startDate)
        end = parse_datetime(endDate)

        results_list = []

        session = DB_SESSION()

        results = []

        results = session.query(BodyInfo).filter(and_(BodyInfo.date_created >= start, BodyInfo.date_created <= end))

        for result in results:
            results_list.append(result.to_dict())
            print(result.to_dict())

        session.close()
        return results_list, 200
    else:
        return NoContent, 400


def process_messages():
    client = KafkaClient(hosts='{}:{}'.format(app_config['kafka']['server'], app_config['kafka']['port']))
    topic = client.topics[app_config['kafka']['topic']]
    consumer = topic.get_simple_consumer(auto_offset_reset=common.OffsetType.LATEST,
                                         reset_offset_on_start=True)
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        session = DB_SESSION()
        if msg["type"] == "ScanRecord":
            scan = ScanIn(msg["payload"]["member_id"],
                          msg["payload"]["store_id"],
                          msg["payload"]["timestamp"])
            session.add(scan)
            logger.info("Adding ScanRecord")
            logger.debug(msg)
        else:
            bi = BodyInfo(msg["payload"]["member_id"],
                          msg["payload"]["store_id"],
                          msg["payload"]["timestamp"],
                          msg["payload"]["body_info"]["weight"],
                          msg["payload"]["body_info"]["body_fat"])
            session.add(bi)
            logger.info("Adding BodyInfoRecord")
            logger.debug(msg)
        session.commit()
        session.close()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml")
CORS(app.app)
app.app.config['CORS_HEADERS'] = 'Content-Type'

if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8090)