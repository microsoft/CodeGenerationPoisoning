import sys
import os
import yaml
import copy
from datetime import datetime, timedelta, timezone
from .constants import STATE_ON, STATE_OFF


class State(object):
    def __init__(self, data=None):
        if data is None:
            self.state = None
            self.attributes = {}
            self.last_changed = datetime.strptime("00:00:00", "%H:%M:%S")
        else:
            self.state = copy.deepcopy(data['state'])
            self.attributes = copy.deepcopy(data['attributes'])
            self.last_changed = datetime.strptime(data['last_changed'], "%H:%M:%S")


class States(object):
    def __init__(self, host):
        self._host = host

    def get(self, obj):
        if obj in self._host._state:
            return State(self._host._state[obj])
        else:
            return None


class Service(object):
    def __init__(self, host):
        self._host = host

    def _set_state(self, kind, obj, value, attributes=None):
        if obj[:len(kind)] != kind:
            raise ValueError("Entity ID can be only one of {}".format(kind))
        if obj not in self._host._state:
            raise ValueError("Entity ID {} was not found in states".format(obj))

        self._host._state[obj]['state'] = value
        if attributes is not None:
            for a in attributes:
                if a in self._host._state[obj]['attributes']:
                    self._host._state[obj]['attributes'][a] = attributes[a]
        self._host._state[obj]['last_changed'] = self._host.time_now().strftime("%H:%M:%S")

    def call(self, domain, service, service_data, wait):
        assert wait is True, "Forgot to set wait to True"
        assert domain in ('variable', 'light', 'switch'), "It's just a mock!" \
                                                          " Only few calls for variable and light are supported"
        if domain == 'variable':
            if service == 'set_variable_data':
                self._set_state('variable.', service_data['variable'], service_data['value'])
                # print("HassMock: Variable {} were set to {}".format(service_data['entity_id'], service_data['value']))
            else:
                raise ValueError("Wrong domain.service: {}.{}".format(domain, service))
        elif domain == 'light':
            if service == 'turn_off':
                self._set_state('light.', service_data['entity_id'], STATE_OFF)
                print("HassMock: Light {} were turned OFF at {}".format(service_data['entity_id'], self._host.time_now()))
            elif service == 'turn_on':
                self._set_state('light.', service_data['entity_id'], STATE_ON,
                                attributes=[None, {'brightness': service_data.get('brightness', 255)}]
                                ['brightness' in service_data])
                print("HassMock: Light {} were turned ON".format(service_data['entity_id'])
                      + ["", " to brightness {}".format(
                             service_data.get('brightness', 255))]['brightness' in service_data]
                      + " at {}".format(self._host.time_now()))
            else:
                raise ValueError("Wrong domain.service: {}.{}".format(domain, service))
        elif domain == 'switch':
            if service == 'turn_off':
                self._set_state('switch.', service_data['entity_id'], STATE_OFF)
                print("HassMock: Switch {} were turned OFF at {}".format(service_data['entity_id'], self._host.time_now()))
            elif service == 'turn_on':
                self._set_state('switch.', service_data['entity_id'], STATE_ON, attributes=None)
                print("HassMock: Switch {} were turned ON".format(service_data['entity_id'])
                      + " at {}".format(self._host.time_now()))
            else:
                raise ValueError("Wrong domain.service: {}.{}".format(domain, service))


class Hass(object):
    def __init__(self, settings_path, state_path, time=None):
        self._settings = {}
        self._state = {}

        # self.load_settings(settings_path)
        self.init_state([], [], [])    # TODO: get objects from settings

        if time is None:
            self._time = datetime(1970, 1, 1, tzinfo=timezone.utc)
        else:
            self._time = time

        self.states = States(self)
        self.services = Service(self)

    def load_settings(self, settings_path):
        with open(settings_path, "r") as f:
            data = yaml.safe_load(f)
        self._settings = {"variable.lights_control_{}".format(k): v['value'] for k, v in data.items()}

    def init_state(self, lights, sensors, automations):

        if False:
            # Old code since time when variables were in use
            state_path = ""

            if os.path.exists(state_path):
                with open(state_path, "r") as f:
                    self._settings = yaml.safe_load(f)
            else:
                lights = []
                sensors = {}

                if "variable.lights_control_powersave" in self._settings:
                    for ps in self._settings["variable.lights_control_powersave"].values():
                        lights += ps['lights']
                for s in ("lights_control_notify_turn_off",
                          "lights_control_off_state",
                          "lights_control_on_state",
                          "lights_control_sensor_map",
                          "lights_control_automation_map"
                          ):
                    lights += self._settings.get("variable.{}".format(s), {}).keys()

                if "variable.lights_control_switch_map" in self._settings:
                    for k, lists in self._settings["variable.lights_control_switch_map"].items():
                        for l in lists:
                            if len(l) > 3:
                                lights += l[3]      # On group
                                if len(l) > 4:
                                    lights += l[4]  # Off group
                            else:
                                lights.append(k)

                if "variable.lights_control_sensor_map" in self._settings:
                    for sensors_list in self._settings["variable.lights_control_sensor_map"].values():
                        for record in sensors_list:
                            sensor = [record[0], STATE_ON]
                            if '.' not in sensor[0]:
                                sensor[0] = 'sensor.' + sensor[0]
                            if len(record) > 1:
                                sensor[1] = record[1]
                            sensors[sensor[0]] = sensor[1]

                if "variable.lights_control_automation_map" in self._settings:
                    for alias in self._settings["variable.lights_control_automation_map"]:
                        self._state["automation." + alias] = {
                            'state': STATE_ON,
                            'attributes': {},
                            'last_changed': "00:00:00"}

                for s in self._settings:
                    self._state[s] = {
                        'state': copy.deepcopy(self._settings[s]),
                        'attributes': {},
                        'last_changed': "00:00:00"
                    }

        lights = sorted(list(set(lights)))
        for light in lights:
            if '.' not in light:
                light = 'light.'+light
            self._state[light] = {
                'state': "off",
                'attributes': {'brightness': 255},
                'last_changed': "00:00:00"}

        for sensor in sensors:
            if '.' not in sensor:
                sensor = 'sensor.'+sensor
            if sensor in self._state:   # State could be simultaneously light and sensor
                continue
            self._state[sensor] = {
                'state': [STATE_OFF, 0][sensors[sensor] != STATE_OFF],
                'attributes': {},
                'last_changed': "00:00:00"}

        for alias in automations:
            if '.' not in alias:
                alias = 'automation.'+alias
            self._state[alias] = {
                'state': STATE_ON,
                'attributes': {},
                'last_changed': "00:00:00"}

    def save_state(self, state_path):
        data = {}
        for s in self._state:
            if True or s not in self._settings:
                data[s] = self._state[s]

        with open(state_path, "w") as f:
            yaml.safe_dump(data, f)

    @property
    def time(self):
        return self._time  # + timedelta(seconds=0)

    @time.setter
    def time(self, value):
        self._time = value  # + timedelta(seconds=0)

    def inc_time(self, delta_seconds):
        self._time += timedelta(seconds=delta_seconds)

    def time_now(self):
        return self.time


class Logger(object):
    info_stream = sys.stdout
    error_stream = sys.stderr

    def info(self, message):
        print(message, file=self.info_stream)

    def warning(self, message):
        print(message, file=self.info_stream)

    def error(self, message):
        print(message, file=self.error_stream)

    def critical(self, message):
        print(message, file=self.error_stream)
