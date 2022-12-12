#!/usr/bin/env python3

import yaml
import os


class Config:
    def __init__(self):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.home_path = os.environ['HOME']
        self.config_path = os.path.join(self.home_path, '.config',
                                        'gtk-hue-sync')
        self.config_file = os.path.join(self.config_path, 'config.yaml')
        self.config = None

    def get_config(self):
        if not os.path.exists(self.config_file):
            self.config_file = os.path.join(self.current_path, '..', '..',
                                            'config.yaml')

        with open(self.config_file, 'r') as stream:
            self.config = yaml.safe_load(stream)
        return self.config


if __name__ == '__main__':
    config = Config()
    print(config.get_config())
