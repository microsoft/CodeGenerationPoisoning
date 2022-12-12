#! /usr/bin/python3

# Copyright (c) 2019 Filippo Ranza <filipporanza@gmail.com>

from collections import namedtuple
import yaml

Config = namedtuple(
    "Configuration", ["transfer_cost", "transfer_speed", "external_cost"]
)

DEFAULT_CONF = Config(1, 1, 1)


def get_transfer_cost(conf):
    price_hunderd_km = conf["PETROL_PRICE"] * conf["CONSUMPTION"]
    price_meter = price_hunderd_km / (10 ** 5)
    out = price_meter * conf["DISTANCE_FACTOR"]
    return out


def get_transfer_speed(conf):
    speed_meter_per_minute = conf["AVERAGE_SPEED"] * (50 / 3)
    out = speed_meter_per_minute / conf["DISTANCE_FACTOR"]
    return 1 / out


def parse_config(conf):
    out = Config(
        get_transfer_cost(conf), get_transfer_speed(conf), conf["EXTERNAL_COST"]
    )
    return out


def load_config(conf_file):
    with open(conf_file) as file:
        out = yaml.safe_load(file)
    return out


def get_conf(conf_file):
    if conf_file:
        conf = load_config(conf_file)
        out = parse_config(conf)
    else:
        out = DEFAULT_CONF
    return out
