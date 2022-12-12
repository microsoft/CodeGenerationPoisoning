"""Parse configuration file & make information available to consumers.

Classes:
    Configs -- Data object containing info from given configuration file.

Exceptions:
    ConfigsError -- Custom exception type for easy ID by error handling.

Functions:
    load_config -- Takes a given configuration filepath, parses it, & creates
            a Configs instance.
"""
import os
import yaml

from src import sensors


# disabling too-few-public-methods because python 3.5 support is needed
# & unable to use the preferred `dataclasses` available in 3.7 + (3.6 using
# backported module)
class Configs:  # pylint: disable=too-few-public-methods
    """Data object containing information from given configuration file.

    Attributes:
        mqtt_host  -- Identifies the address of the mqtt server host.
        mqtt_port  -- Identifies the port the mqtt server is listening on.
        mqtt_user  -- Username given to mqtt connection, optional
        mqtt_pass  -- Password given to mqtt connection, optional
        root_topic -- Represents beginning of the topic for all messages.
    """

    def __init__(self, config_obj: dict):
        """Init a Configs object with attributes from config_obj's keys."""
        self.mqtt_host = config_obj['mqtt_host']
        self.mqtt_port = config_obj['mqtt_port']
        self.root_topic = config_obj['root_topic']

        self.mqtt_user = os.getenv('MQTT_USER')
        self.mqtt_pass = os.getenv('MQTT_PASS')

        # both user & pass must be given, or else config fails
        if self.mqtt_user is None and self.mqtt_pass is not None or \
                self.mqtt_user is not None and self.mqtt_pass is None:
            raise ConfigsError(
                "Both a mqtt User & Password must be specified" +
                "if using mqtt authentication; otherwise leave both " +
                "commented out in your configuration.yaml")

        self.sensor_list = {}

        for (group, sensor_list) in config_obj['sensor_groups'].items():
            for sensor in sensor_list:
                sensor['group'] = group
                self.sensor_list[sensor['pin']] = sensors.build_sensor(sensor)


class ConfigsError(Exception):
    """Simple custom error type for easy handling, no new behaviour."""


def load_configs(config_file: str) -> Configs:
    """Take a config filepath, parse it, & create a Configs instance."""
    with open(config_file, 'r') as stream:
        return Configs(yaml.safe_load(stream))
