# -*- coding: utf-8 -*-
# import os
# import yaml
# import inspect

from .WaporAPI import WaPOR_API_class

__doc__ = """module for FAO WAPOR API"""
__version__ = '0.1'

# print_job = True
print_job = False
API = WaPOR_API_class(print_job=print_job)

# # WaPOR_Token = input('Insert WAPOR API Token: ')
#
# __location__ = os.path.join(
#     os.getcwd(),
#     os.path.dirname(
#         inspect.getfile(
#             inspect.currentframe())))
#
# file = os.path.join(__location__, 'token.yml')
# if os.path.exists(file):
#     WaPOR_Token = yaml.load(open(file, 'r'), Loader=yaml.FullLoader)
# else:
#     # WaPOR_Token = input('Insert WAPOR API Token: ')
#
#     file_ex = os.path.join(__location__, 'token-example.yml')
#     if os.path.exists(file_ex):
#         WaPOR_Token = yaml.load(open(file_ex, 'r'), Loader=yaml.FullLoader)
#     else:
#         raise FileNotFoundError('ERROR: "{f}" not found.'.format(f=file))
# API.setAPIToken(WaPOR_Token)
#
# print('download.__init__.__location__', __location__)
# download.__init__.__location__
#  C:\Anaconda3\lib\site-packages
#    \wapor-0.0.post0.dev22+g816c3aa.dirty-py3.7.egg
#    \wapor\download
#
# print(API.isAPIToken)

__all__ = ['API']
