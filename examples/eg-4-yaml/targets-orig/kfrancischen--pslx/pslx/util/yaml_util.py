import os
import yaml


class YamlUtil(object):

    @classmethod
    def yaml_to_dict(cls, file_name):
        if not os.path.exists(file_name):
            return {}
        else:
            with open(file_name, 'r') as infile:
                return yaml.safe_load(infile)


if __name__ == '__main__':
    print(YamlUtil.yaml_to_dict(file_name='config/tool_config.yaml'))
