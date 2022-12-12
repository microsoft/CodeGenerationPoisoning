#!/usr/bin/env python
from pathlib import Path
from typing import List, Union

import yaml


class TestConfigInput(object):

  def __init__(self, values: dict = None):
    values = values if values is not None else {}

    self.expected: str = values.pop("expected", None)
    self.input: str = values.pop("input", None)


class TestConfig(object):

  def __init__(self, values: dict = None):
    values = values if values is not None else {}

    self.test_cases: List[TestConfigInput] = list(map(TestConfigInput, values.pop("test_cases", []))) if "test_cases" in values else None


def load_yaml_test_config_file(test_file: Union[str, bytes, Path]) -> TestConfig:
  with open(test_file, "r") as tf:
    config: TestConfig = TestConfig(values=yaml.full_load(tf))

  return config
