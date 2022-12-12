#!/usr/bin/env python3
from argparse import ArgumentParser

import yaml

from web_monitor.kafka_client import KafkaReader
from web_monitor.pg_client import PgClient

DESCRIPTION = """
Read sites availabiliry reports from the kafka service and commit them to PostgreSQL database
"""

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", help="YAML config file", required=True)

    args = parser.parse_args()
    with open(args.config, 'r') as config_file:
        config = yaml.load(config_file, yaml.SafeLoader)

    with PgClient(config["postgres"]) as pg_sink:
        with KafkaReader(config["kafka"], pg_sink) as kafka_reader:
            try:
                while True:
                    kafka_reader.run()
            except KeyboardInterrupt:
                print("Sutting down")
