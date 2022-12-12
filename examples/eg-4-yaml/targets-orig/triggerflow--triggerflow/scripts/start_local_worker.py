import sys
import yaml
import logging
import argparse

from triggerflow.service.worker import Worker as TriggerflowWorker

CONFIG_MAP_PATH = 'config_map.yaml'

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('[%(asctime)s.%(msecs)03dZ][%(levelname)s][triggerflow] %(message)s',
                              datefmt="%Y-%m-%dT%H:%M:%S")

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def bootstrap_worker(workspace: str, config_map: dict):
    """
    Bootstrap a Triggerflow worker manually, without the intervention of the controller.
    Used for testing and development purposes.
    """
    worker = TriggerflowWorker(workspace=workspace, config=config_map)
    worker.run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace', type=str)
    parser.add_argument('--configfile', type=str, default='config_map.yaml')
    args = parser.parse_args()

    with open(args.configfile, 'r') as config_map_file:
        config_map = yaml.safe_load(config_map_file.read())

    bootstrap_worker(args.workspace, config_map)
