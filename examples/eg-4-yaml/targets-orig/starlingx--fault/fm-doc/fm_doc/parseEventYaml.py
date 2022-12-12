#
# Copyright (c) 2016 Wind River Systems, Inc.
#
# SPDX-License-Identifier: Apache-2.0
#

# Python3 compatibility
from __future__ import print_function

import sys
import os

import yaml
import constants

# Record Format  (for full description see events.yaml)
#
# 100.001:
#   Type: Alarm
#   Description: "Degrade: <hostname> is experiencing an intermittent 'Management Network'  communication failure."
#   Entity_Instance_ID: host=<hostname>
#   Severity: critical
#   Proposed_Repair_Action: "Check Host's board management configuration and connectivity."
#   Maintenance_Action: auto recover
#   Inhibit_Alarms: True
#   Alarm_Type: operational-violation
#   Probable_Cause: timing-problem
#   Service_Affecting: False
#   Suppression: True
#   Management_Affecting_Severity: warning
#   Degrade_Affecting_Severity: none
#

type_FieldName = 'Type'
type_FieldValue_Alarm = 'Alarm'
type_FieldValues = [type_FieldValue_Alarm, 'Log']

description_FieldName = 'Description'
description_FieldValues = []  # arbitrary string

entityInstanceId_FieldName = 'Entity_Instance_ID'
entityInstanceId_FieldValues = []  # arbitrary string

severity_FieldName = 'Severity'
severity_FieldValues = constants.ALARM_SEVERITY

proposedRepairAction_FieldName = 'Proposed_Repair_Action'
proposedRepairAction_FieldValues = []  # arbitrary string

maintenanceAction_FieldName = 'Maintenance_Action'
maintenanceAction_FieldValues = []  # arbitrary string

inhibitAlarms_FieldName = 'Inhibit_Alarms'
inhibitAlarms_FieldValues = [True, False]

alarmType_FieldName = 'Alarm_Type'
alarmType_FieldValues = constants.ALARM_TYPE

probableCause_FieldName = 'Probable_Cause'
probableCause_FieldValues = constants.ALARM_PROBABLE_CAUSE

serviceAffecting_FieldName = 'Service_Affecting'
serviceAffecting_FieldValues = [True, False]

suppression_FieldName = 'Suppression'
suppression_FieldValues = [True, False]

managementAffectingSeverity_FieldName = 'Management_Affecting_Severity'
managementAffectingSeverity_FieldValues = constants.ALARM_SEVERITY.append('none')

degradeAffecting_FieldName = 'Degrade_Affecting_Severity'
degradeAffecting_FieldValues = constants.ALARM_SEVERITY.append('none')

alarmFields = {
    type_FieldName: type_FieldValues,
    description_FieldName: description_FieldValues,
    entityInstanceId_FieldName: entityInstanceId_FieldValues,
    severity_FieldName: severity_FieldValues,
    proposedRepairAction_FieldName: proposedRepairAction_FieldValues,
    maintenanceAction_FieldName: maintenanceAction_FieldValues,
    inhibitAlarms_FieldName: inhibitAlarms_FieldValues,
    alarmType_FieldName: alarmType_FieldValues,
    probableCause_FieldName: probableCause_FieldValues,
    serviceAffecting_FieldName: serviceAffecting_FieldValues,
    suppression_FieldName: suppression_FieldValues,
    managementAffectingSeverity_FieldName: managementAffectingSeverity_FieldValues,
    degradeAffecting_FieldName: degradeAffecting_FieldValues
}

logFields = {
    type_FieldName: type_FieldValues,
    description_FieldName: description_FieldValues,
    entityInstanceId_FieldName: entityInstanceId_FieldValues,
    severity_FieldName: severity_FieldValues,
    alarmType_FieldName: alarmType_FieldValues,
    probableCause_FieldName: probableCause_FieldValues,
    serviceAffecting_FieldName: serviceAffecting_FieldValues
}


def checkField(fieldKey, fieldValues, key, event):
    if fieldKey not in event:
        print("\n    ERROR: %s missing \'%s\' field." % (key, fieldKey))
        return False
    # print("START: %s :END" % event[fieldKey])

    if type(event[fieldKey]) is str:
        if not fieldValues:
            return True
        if event[fieldKey] in fieldValues:
            return True
        else:
            print("\n    ERROR: \'%s\' is not a valid \'%s\' field value." % (event[fieldKey], fieldKey))
            print("           Valid values are:", fieldValues)
            return False

    if type(event[fieldKey]) is list:
        if not fieldValues:
            return True
        for listvalue in event[fieldKey]:
            if listvalue not in fieldValues:
                print("\n    ERROR: \'%s\' is not a valid \'%s\' field value." % (listvalue, fieldKey))
                print("           Valid values are:", fieldValues)
                return False

    if type(event[fieldKey]) is dict:
        for dictKey, dictValue in event[fieldKey].items():
            if dictKey not in severity_FieldValues:
                print("\n    ERROR: \'%s\' is not a valid \'%s\' index value." % (dictKey, fieldKey))
                print("           Valid index values are:", severity_FieldValues)
                return False
            if fieldValues:
                if dictValue not in fieldValues:
                    print("\n    ERROR: \'%s\' is not a valid \'%s\' field value." % (dictValue, fieldKey))
                    print("           Valid values are:", fieldValues)
                    return False
    return True


def checkTypeField(key, event):
    if type_FieldName not in event:
        print("\n    ERROR: %s missing \'%s\' field." % (key, type_FieldName))
        return False
    if event[type_FieldName] in type_FieldValues:
        return True
    print("\n    ERROR: \'%s\' is not a valid \'%s\' field value." % (event[type_FieldName], type_FieldName))
    return False


def checkFields(key, event):
    isOk = True
    if not checkTypeField(key, event):
        return False
    isAlarm = (event[type_FieldName] == type_FieldValue_Alarm)
    eventFields = alarmFields if isAlarm else logFields

    for fieldKey, fieldValues in eventFields.items():
        if not checkField(fieldKey, fieldValues, key, event):
            isOk = False

    for itemKey, itemValue in event.items():
        if itemKey not in eventFields:
            print("\n    ERROR: \'%s\' is not a valid \'%s\' field." % (itemKey, ("Alarm" if isAlarm else "Log")))
            isOk = False

    return isOk


#
# Main
#

if len(sys.argv) == 1:
    print("Missing file argument.\n")
    exit(1)

if not os.path.isfile(sys.argv[1]):
    print("File \'%s\' does not exist.\n" % (sys.argv[1]))
    exit(1)

with open(sys.argv[1], 'r') as stream:
    try:
        events = yaml.load(stream)
        exitValue = 0

        for key in events:
            print("%6.3f: checking ... " % key)
            if not checkFields(key, events[key]):
                print()
                exitValue = 1
            else:
                print('OK.')

        print('Done.')

    except yaml.YAMLError as exc:
        print(exc)

exit(exitValue)
