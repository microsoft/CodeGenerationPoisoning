import airplay
import argparse
import json
import sys
import os
import yaml
from http import HTTPStatus
import logging

logging.basicConfig(filename='cli.log', filemode='w', format='%(asctime)s-%(levelname)s-%(message)s')
logger = logging.getLogger()
logger.setLevel(10)

argv = sys.argv
parser = argparse.ArgumentParser(description="Command line interface for AirTable")
parser.add_argument("table_name", help="Table name")
parser.add_argument("action", help="Chose an action", choices=["ins", "mod", "del", "get"])
body_group = parser.add_argument_group(title='Requests body')
body_group.add_argument("-payload", help="Payload dictionary", type=json.loads)
body_group.add_argument("-target_id", help="Item id number")
body_group.add_argument("-c", help="Config file path")
parser.add_argument("-pf", "--prettify", help="Pretty output", type=int)
args = parser.parse_args()

def chk_config_():
    cf = None
    tbl = None
    if '-c' in sys.argv:
        if os.path.isfile(args.c):
            cf = args.c
        else:
            print("Configuration file not found1", file=sys.stderr)
            sys.exit(1)
    elif os.path.isfile('config.yaml'):
        cf = 'config.yaml'
    else:
        cf = None
        tbl = None
        print("Configuration file not found2", file=sys.stderr)
        sys.exit(1)
    if cf is not None:
        with open(cf, 'r') as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
            try:
                tbl = airplay.Table(config['base_key'], args.table_name, config['api_key'])
            except KeyError:
                print("Missing attributes in configuration file", file=sys.stderr)
                tbl = None
    return tbl


def actions():
    if chk_config_() is not None:
        tbl = chk_config_()
        res = ''
        try:
            if args.action == "ins":
                res = (tbl.insert(**args.payload))
            if args.action == "get":
                res = (tbl.items())
            if args.action == "mod":
                res = (tbl.modify(args.target_id, **args.payload))
            if args.action == "del":
                res = (tbl.delete(args.target_id))

        except airplay.HTTPStatusCodeException as ex:
            print(HTTPStatus(ex.status).phrase, file=sys.stderr)
        finally:
            dumps_kwargs = {}
            if '-pf' in sys.argv or '--prettify' in sys.argv:
                dumps_kwargs.update({'indent': args.prettify})

            print(json.dumps(res, **dumps_kwargs))
    else:
        pass


actions()
