# # coding=utf-8
# import configparser
#
# from nodes.basic.basic_node import BasicNode
# from nodes.utils_node.detect_file_path import detect_file_full_path
#
#
# class SettingsLoader(object):
#     @staticmethod
#     def load_file(file_path, parser_func, **kwargs):
#         with open(file_path, 'r') as f:
#             return parser_func(f.read(), **kwargs)
#
#     # @classmethod
#     # def load_settings_from_yaml(cls, file_path, key):
#     #     import yaml
#     #     r = cls.load_file(file_path, yaml.load)
#     #     return r[key]
#
#
# class SettingsBaseNodes(BasicNode):
#     def __init__(self, file_path, operator):
#         super(SettingsBaseNodes, self).__init__(file_path)
#         self.file_path = file_path
#         self.operator = operator
#
#
# class ConfigparserConfNode(BasicNode):
#     def __init__(self, file_path, section):
#         super(ConfigparserConfNode, self).__init__(file_path)
#         self.config = configparser.ConfigParser()
#         self.config.read(file_path)
#         self.section = section
#
#     def get(self):
#         return dict(self.config.items(self.section))
#
#     # def __getitem__(self, key):
#     #     return self.config.get(self.section, key)
#     #
#     # def __setitem__(self, key, value):
#     #     self.config.set(self.section, key, value)
#
#
# class ClickHouseSettings(ConfigparserConfNode):
#     def __init__(self, file_path='conn.ini', section='ClickHouse'):
#         file_path = detect_file_full_path(file_path)
#         super(ClickHouseSettings, self).__init__(file_path, section)
#
#     def get(self):
#         res = dict(self.config.items(self.section))
#         res['port'] = int(res['port'])
#         return res
#
#
# class MySQLSettings(ConfigparserConfNode):
#     def __init__(self, file_path='conn.ini', section='MySQL'):
#         file_path = detect_file_full_path(file_path)
#         super(MySQLSettings, self).__init__(file_path, section)
#
#     def get(self):
#         res = dict(self.config.items(self.section))
#         res['port'] = int(res['port'])
#         return res
#
#
# if __name__ == '__main__':
#     cpc = ClickHouseSettings()
#     print(dict(cpc.get()))
#     print(1)
#
#     pass
