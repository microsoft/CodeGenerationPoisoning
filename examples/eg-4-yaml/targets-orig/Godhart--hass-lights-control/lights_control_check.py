"""
A script to test core logic of lights control component.
It uses mock of HASS that is sufficient run component.
"""

import lights_control_core as _lights_control
from lights_control_core.lights_control import LightsControl
from lights_control_core._hass_mock import Hass, Logger
from time import time
from datetime import datetime, timezone

import sys
import yaml


_lights_control.ALLOW_POSITIONAL_CONF = True
_lights_control.LOG_CALLS = True


# This script call args:
# 1: settings file path (YAML file with lights control rules)
# 2: path to dump state
# 3: test function options
# 4: start time
# 5: times to call test function
# 6: time step between calls
# 7: timestep

settings_path = sys.argv[1]
state_path = sys.argv[2]
start_time = datetime.strptime(sys.argv[4], "%H:%M:%S")
start_time = datetime(1970, 1, 1, hour=start_time.hour, minute=start_time.minute, second=start_time.second,
                      tzinfo=timezone.utc)

hass = Hass("", state_path, start_time)
logger = Logger()
with open(settings_path, "r") as f:
    settings = yaml.safe_load(f)

test_data = sys.argv[3]
test_data = yaml.safe_load(test_data)


h = {'hass': hass, 'logger': logger}

on_state = settings.get('on_state', {})
off_state = settings.get('off_state', {})
power_save = settings.get('power_save', {})
notify_turn_off = settings.get('notify_turn_off', {})
switch_map = settings.get('switch_map', {})
sensor_map = settings.get('sensor_map', {})
sensor_default_switch_off = settings.get('sensor_default_switch_off', 5)
automation_map = settings.get('automation_map', {})

lc = LightsControl(h, False,
                   on_state, off_state, power_save, notify_turn_off, switch_map, sensor_map,
                   sensor_default_switch_off, automation_map,
                   mock_time_now=hass.time_now)


def log(message):
    logger.info(message)


def test(data):
    # log("Fired light_control({})".format(
    #    ', '.join(["{}: {}".format(k, data[k]) for k in data])))

    # Get mandatory call args

    scenario = data.get('scenario', None)

    # Check call args

    assert scenario in ('switch', 'sensor', 'watchdog', 'on_light_change'),\
        "Lights control: Scenario '{}' isn't supported!".format(
        scenario)

    if scenario in ('switch', 'sensor', 'on_light_change'):
        trigger_name = data.get('name', None)
        trigger_value = data.get('value', None)
        assert trigger_name is not None, "Lights control: No 'name' in data for '{}' scenario".format(scenario)
        assert trigger_value is not None, "Lights control: No 'value' in data for '{}' scenario".format(scenario)
    else:
        trigger_name = None
        trigger_value = None

    if scenario == 'switch':
        lc.switch(trigger_name, trigger_value)
    elif scenario == 'sensor':
        lc.sensor(trigger_name, trigger_value)
    elif scenario == 'on_light_change':
        lc.on_light_change(trigger_name)
    elif scenario == 'watchdog':
        lc.watchdog()


call_data = test_data
if len(sys.argv) > 5:
    times = int(sys.argv[5])
else:
    times = 1
if len(sys.argv) > 6:
    step = int(sys.argv[6])
else:
    step = 1
if len(sys.argv) > 7:
    timestep = int(sys.argv[7])
else:
    timestep = 1

if 60 % timestep != 0:
    allowed_timesteps = []
    for i in range(1, 61):
        if 60 % i == 0:
            allowed_timesteps.append(str(i))
    raise ValueError("Wrong timestep {}!\nAllowed timesteps are: {}".format(
        timestep, ", ".join(allowed_timesteps)))

timesteps_per_iteration = 60 // timestep

for i in range(0, times):
    log(hass.time_now())
    data = call_data
    start_time = time()
    test(data)
    end_time = time()
    # log("Call elapsed {} secs".format(end_time - start_time))
    print("Call elapsed {} secs".format(end_time - start_time), file=sys.stderr)
    for j in range(0, step*timesteps_per_iteration):
        hass.inc_time(timestep)
        # log(hass.date_now())
        data = {'scenario': 'watchdog'}
        start_time = time()
        test(data)
        end_time = time()
        # log("Watchdog elapsed {} secs".format(end_time-start_time))

if state_path not in ("", "-"):
    hass.save_state(state_path+"o")
