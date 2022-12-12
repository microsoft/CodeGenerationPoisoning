#!/usr/bin/python
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

import sys
import os

import yaml
import collections

import constants as fm_constants

FM_ALARM_H = "fmAlarm.h"


def get_events_alarm_list(events):
    for alarm_id in list(events):
        if isinstance(alarm_id, float):
            formatted_alarm_id = "{:.3f}".format(alarm_id)   # force 3 digits after the point, to include trailing zero's (ex.: 200.010)
            events[formatted_alarm_id] = events.pop(alarm_id)

    events = collections.OrderedDict(sorted(events.items()))

    events_alarm_list = []

    for alarm_id in events:
        if events.get(alarm_id).get('Type') == "Alarm":
            events_alarm_list.append(str(alarm_id))

    return events_alarm_list


def get_constants_alarms():
    fm_constants_raw_dict = fm_constants.__dict__

    fm_constants_alarms_dict = {k: v for k, v in fm_constants_raw_dict.items() if 'FM_ALARM_ID' in k}
    del fm_constants_alarms_dict['FM_ALARM_ID_INDEX']  # this is not an alarm

    fm_constants_alarms = []
    for alarm_constant_name in fm_constants_alarms_dict:
        alarm_constant_full_name = 'fm_constants.' + alarm_constant_name
        fm_constants_alarms.append(eval(alarm_constant_full_name))

    return fm_constants_alarms


def get_fm_alarms():

    fm_alarm_group_lines = []
    fm_alarm_groups = {}
    fm_alarms = []

    with open(FM_ALARM_H) as f:
        fm_alarms_file = f.readlines()

    fm_alarm_group_lines = [k for k in fm_alarms_file if 'define ALARM_GROUP_' in k]

    for line in fm_alarm_group_lines:
        group_name = line.split()[1]
        group_value = line.split()[2]
        group_value = group_value[1:-1]  # remove quotes
        fm_alarm_groups[group_name] = group_value

    fm_alarm_lines = [k for k in fm_alarms_file if 'FM_ALARM_ID' in k]

    for line in fm_alarm_lines:
        # alarm_name = line.split()[1]
        group_name = line.split()[2]
        group_name = group_name[1:]
        alarm_right_digits_value = line.split()[3]
        alarm_right_digits_value = alarm_right_digits_value[1:-2]
        alarm_left_digits_value = fm_alarm_groups[group_name]
        alarm_value = alarm_left_digits_value + alarm_right_digits_value
        fm_alarms.append(alarm_value)

    return fm_alarms


#
# Main
#

if len(sys.argv) == 1:
    print("Missing file argument.\n")
    exit(1)

if not os.path.isfile(sys.argv[1]):
    print("File \'%s\' does not exist.\n" % (sys.argv[1]))
    exit(1)

exitValue = 0

with open(sys.argv[1], 'r') as stream:
    try:
        events = yaml.load(stream)
        events_alarm_list = get_events_alarm_list(events)

    except yaml.YAMLError as exc:
        print(exc)

constants_alarms = get_constants_alarms()
for alarm_id in constants_alarms:
    if alarm_id not in events_alarm_list:
        print("\n    ERROR: constants.py alarm \'%s\' must be defined in file events.yaml.\n" % (alarm_id))
        exitValue = 1

fm_alarms = get_fm_alarms()
for alarm_id in fm_alarms:
    if alarm_id not in events_alarm_list:
        print("\n    ERROR: fmAlarm.h alarm \'%s\' must be defined in file events.yaml.\n" % (alarm_id))
        exitValue = 1

exit(exitValue)
