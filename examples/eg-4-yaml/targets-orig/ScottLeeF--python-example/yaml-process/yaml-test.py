# -*- coding: utf-8 -*-

import os

import yaml

file_path = os.path.abspath("../resources/yaml-test.yml")
file = open(file_path, 'r', encoding='utf-8')
ys = yaml.load_all(file.read(), Loader=yaml.Loader)
for y in ys:
    print(y)
