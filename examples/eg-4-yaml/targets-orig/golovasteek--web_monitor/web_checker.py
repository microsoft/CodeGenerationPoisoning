#!/usr/bin/env python3
from argparse import ArgumentParser
import time

import yaml
from web_monitor.http_requester import do_requests
from web_monitor.kafka_client import KafkaSink


CHECK_PERIOD_S = 5

DESCRIPTION = """
Periodically check the web-pages availability and publish test results into Kafka.
"""

if __name__ == "__main__":
    parser = ArgumentParser(description=DESCRIPTION)
    parser.add_argument("-c", "--config", help="YAML config file", required=True)

    args = parser.parse_args()
    with open(args.config, 'r') as config_file:
        config = yaml.load(config_file, Loader=yaml.SafeLoader)

    with KafkaSink(config["kafka"]) as sink:
        next_iteration = time.time()
        try:
            while True:
                do_requests(config["pages"], sink)
                now = time.time()
                next_iteration = max(next_iteration + CHECK_PERIOD_S, now)
                time.sleep(next_iteration - now)
        except KeyboardInterrupt:
            print("Shutting down...")
