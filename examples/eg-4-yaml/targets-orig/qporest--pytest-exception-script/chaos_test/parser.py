"""
What i want is to point this cli at a code with a starting point.
Then, I want to pass it a configuration with - modules, functions, classes, methods and the errors they should produce.
I want the code to have a final passing check.

Example:
start-point: run_circuits.run  # if not running live - this will have to be mocked somehow... Use mocked test value?
reload-point: app.components.qradar_poll  # will be used to switch between scenarios, unless otherwise specified


success_criteria:               # after every scenario is complete calling this will succeed the test
	call: app.components.qradar_poll
success_criteria:
	exit_code: []               # if code finishes execution after every scenario with given exit_code - succeed

[[scenario]]
reload-point:  # this scenario progresses at a different time

[[scenario."app.components.qradar_poll"]]
exc = "pass"                   # this is the exception to raise

[[scenario]]
[[scenario."app.components.qradar_poll"]]
exc = "KeyValue"               # raise the current exception
chance = 10                  # percent chance?

[[scenario]]
[[scenario."app.components.qradar_poll"]]
exc = "IntegrationError"       # raise another Exception
message = "Integration says boo"
[[scenario."app.components.qradar_poll.QRadarPoll.rest_client"]]
exc = "KeyError"               # this will also throw an exception upon execution

Expectation:
	Upon first execution app.components.qradar_poll gets executed without breaking
	Upon being executed second time - it will create an error
	Upon being called third time - it will throw an error and rest_client would throw one too
	Success if we detect the criteria method being called - exit with success

Gotta load the code - create all the mocks and start start_point

All the mocks need to have a wrapper around them. Use monkeypatch.

ChaosTest() -> tries to check local .chaos
Or provide a config file to it
Setup PYTHONPATH before calling it, or do - chaos-test -c config.file
Maybe spinal-tap.

To run it - first need to create a separate thread testing it?
Or if it runs forever - let it.

So - the hierarchy is:
    File
    -> Scenario
    Scenario sets up the mocks to run the tests.

    It has special mocks to mock the functions / etc. as it goes, and update with the new values.

    To run it we need to go through every scenario and do the following:
    - Create a global runner.
    If there's more than 1 scenario a reload point has to exist
    Runner does the following - 
        1. for every scenario monkeypatch all the required data
        2. monkeypatched classes either do what the code used to do with a chance of throwing an error
        3. Throw an error
        4. Reload point does what it was supposed to do, but also undoe's all the patches and sets up the next ones
        5. Upon reaching the final scenario - monkeypatch success criteria
"""
from pytest import File, Item, Collector

from .structure import Scenario, Act

from werkzeug.utils import import_string

import toml
import yaml


class TomlChaosFile(File):
    """
    Custom Container for toml files.
    """

    SCENARIO_HEADER = "act"
    def __init__(self, fspath, parent):
        self.config = parent.config
        super(TomlChaosFile, self).__init__(fspath, parent=parent)

    @staticmethod
    def extract_acts(data):
        acts = []
        for act in data.get(TomlChaosFile.SCENARIO_HEADER, []):
            acts.append(act)
        return acts

    def collect(self):
        raw = toml.load(self.fspath.open(encoding='utf8'))
        app_factory = raw.get('entry-point')
        global_next = raw.get('next-point')

        assert app_factory is not None, "Define entry point to run chaos testing."
        assert self.config.pluginmanager.get_plugin("monkeypatch"), "Monkeypatch is not available."

        app_factory = import_string(app_factory)

        acts = self.extract_acts(raw)

        scenario = Scenario(
            self.parent, app_factory, self.config.pluginmanager.get_plugin("monkeypatch"), acts, global_next=global_next
        )

        return scenario.acts

class YamlChaosFile(File):
    """
    Parse .yaml file into a scenario.
    """
    SCENARIO_HEADER = "acts"
    def __init__(self, fspath, parent):
        self.config = parent.config
        super(YamlChaosFile, self).__init__(fspath, parent=parent)

    @staticmethod
    def extract_acts(data):
        acts = []
        for act in data.get(YamlChaosFile.SCENARIO_HEADER, []):
            acts.append(act)
        return acts

    def collect(self):
        raw = yaml.safe_load(self.fspath.open(encoding='utf8'))
        app_factory = raw.get('entry-point')
        global_next = raw.get('next-point')

        assert app_factory is not None, "Define entry point to run chaos testing."
        assert self.config.pluginmanager.get_plugin(
            "monkeypatch"), "Monkeypatch is not available."

        app_factory = import_string(app_factory)

        acts = self.extract_acts(raw)

        scenario = Scenario(
            self.parent, app_factory, self.config.pluginmanager.get_plugin("monkeypatch"), acts, global_next=global_next
        )

        return scenario.acts
