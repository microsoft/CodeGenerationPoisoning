from __future__ import absolute_import
from __future__ import print_function
import json
import click
import yaml
import requests

import json
from six.moves import map


class PingdomInvalidResponse(Exception):
    pass


@click.command()
@click.option('--noop', is_flag=True, help="Don't apply changes to Pingdom.")
@click.option('--pingdom-email', required=True,
              help='Email to use to speak with Pingdom.',
              envvar='PINGDOM_EMAIL')
@click.option('--pingdom-password', required=True,
              help='Password to use to speak with Pingdom.',
              envvar='PINGDOM_PASSWORD')
@click.option('--pingdom-api-key', required=True,
              help='API Key to use to speak with Pingdom.',
              envvar='PINGDOM_API_KEY')
@click.option('--alert-config-file', required=True,
              help="path to config file",
              envvar='ALERT_CONFIG_FILE')
def main(noop, pingdom_email, pingdom_password,
         pingdom_api_key,
         alert_config_file):
    # Safely Deseriallize the yaml object by using the safe method Loader
    with open(alert_config_file, 'r') as stream:

