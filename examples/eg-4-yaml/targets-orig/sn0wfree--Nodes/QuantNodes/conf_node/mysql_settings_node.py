# # coding=utf-8
# from functools import wraps
#
# import yaml
#
# from nodes.utils_node.detect_file_path import detect_file_full_path
#
#
# class MySQLSettings(object):
#
#     def _supported(self):
#         return
#
#     @classmethod
#     def parser(cls, config_path='conn.yaml'):
#         cfg_format = config_path.split('.')[-1]
#
#         def temp(func):
#             @wraps(func)
#             def _temp(*args, **kwargs):
#                 if 'cfg' in kwargs:
#                     if kwargs.get('cfg') is None:
#                         settings = cls._parser_(config_path=config_path, cfg_format=cfg_format)
#                         kwargs['cfg'] = settings
#
#                 return func(*args, **kwargs)
#
#             return _temp
#
#         return temp
#
#     @classmethod
#     def _parser_(cls, config_path='conn.yaml', cfg_format='yaml'):
#         file_path = detect_file_full_path(config_path)
#         if cfg_format == 'yaml':
#             return cls._yaml_settings(file_path)
#         else:
#             raise ValueError('only accept yaml format!')
#
#     @staticmethod
#     def _yaml_settings(config_path):
#         return yaml.load(config_path)
#
#
# if __name__ == '__main__':
#     pass
