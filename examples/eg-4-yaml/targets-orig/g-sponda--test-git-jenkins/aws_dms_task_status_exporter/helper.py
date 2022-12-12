from prometheus_client.core import REGISTRY
import argparse
import yaml


def get_conf_file():
    parser = argparse.ArgumentParser(
        description="Collect status of AWS DMS replication task"
    )
    parser.add_argument("-f", "--file", help="YAML files with ", required=True)
    file_path = parser.parse_args().file

    with open(file_path, "r") as ymlfile:
        cfg = yaml.load(ymlfile)

    return cfg


def clean_registry():
    # Loop with try except to remove all default collectors
    for _, collector in list(REGISTRY._names_to_collectors.items()):
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass
