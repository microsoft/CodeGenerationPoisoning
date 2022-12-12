# coding=utf-8

import yaml
import os


class YamlReader:
    def __init__(self, file_path):
        if os.path.exists(file_path):
            self.file_path = file_path
        else:
            raise FileNotFoundError('文件不存在')
        self._data = None

    def data(self):
        if not self._data:
            with open(self.file_path, 'rb') as f:
                self._data = list(yaml.safe_load_all(f))
            return self._data

    def get(self, element, index=0):
        return self.data()[index].get(element)


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(__file__))
    yaml_file = os.path.join(base_dir, 'config', 'config.yaml')
    # data = YamlReader(yaml_file).data()
    print(YamlReader(yaml_file).get('ssh').get('user'))
