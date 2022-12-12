#################################################################
#                                                               #
# Wilfred                                                       #
# Copyright (C) 2020-2022, Vilhelm Prytz, <vilhelm@prytznet.se> #
#                                                               #
# Licensed under the terms of the MIT license, see LICENSE.     #
# https://github.com/wilfred-dev/wilfred                        #
#                                                               #
#################################################################

import yaml

# from wilfred.core import is_integer


def yaml_read(path):  # this function should be refactored later on!!!
    with open(path) as f:
        _raw = yaml.load(f.read(), Loader=yaml.FullLoader)

    _reformatted = {}

    def _iterate_dict(data, _name):
        """
        iterates a dictionary and continues to iterate the value of the dict if the
        type is dictionary, list or tuple (recursion). Adds the dictionary key and value
        to the _reformatted dict if it's a string, integer or boolean
        """

        _def = _name
        for k, v in data.items():
            _name = f"{_def}/{k}"
            if type(v) in [dict]:
                _iterate_dict(v, _name)
            if type(v) in [list, tuple]:
                _iterate_list(v, _name)

            if type(v) in [str, int, bool]:
                _reformatted[f"{_def}/{k}"] = v

    def _iterate_list(data, _name):
        """
        iterates a list and continues to iterate the values of the list if the
        type is dictionary, list or tuple (recursion). Adds the list value
        to the _reformatted dict if it's a string, integer or boolean
        """

        _def = _name

        i = 0
        for x in data:
            _name = f"{_def}/{i}"
            if type(x) in [dict]:
                _iterate_dict(x, _name)
            if type(x) in [list, tuple]:
                _iterate_list(x, _name)

            if type(x) in [str, int, bool]:
                _reformatted[f"{_def}/{i}"] = x

            i = i + 1

    for k, v in _raw.items():
        _name = k

        if type(v) in [dict]:
            _iterate_dict(v, _name)
        if type(v) in [list, tuple]:
            _iterate_list(v, _name)

        if type(v) in [str, int, bool]:
            _reformatted[k] = v

    return _reformatted


# def yaml_write(path, key, value): # does not work yet!!
#     with open(path) as f:
#         _raw = yaml.load(f.read(), Loader=yaml.FullLoader)

#     def _traverse(obj, path=None, callback=None):
#         if path is None:
#             path = []

#         if type(obj) in [dict]:
#             value = {k: _traverse(v, path + [k], callback) for k, v in obj.items()}
#         elif type(obj) in [list, tuple]:
#             value = [_traverse(elem, path + [[]], callback) for elem in obj]
#         else:
#             value = obj

#         if callback is None:
#             return value
#         else:
#             return callback(path, value)

#     def _traverse_modify(obj, target_path, action):
#         def transformer(path, value):
#             if path == target_path:
#                 return action(value)
#             else:
#                 return value

#         return _traverse(obj, callback=transformer)

#     def _callback(v):
#         return value

#     _reformatted_path = [[] if is_integer(x) else x for x in key.split("/")]
#     _traverse_modify(_raw, _reformatted_path, _callback)

#     # with open(path, "w") as f:
#         # yaml.dump(_raw, f)


def yaml_write(path, key, value):  # does not work yet!!
    raise Exception("Modifying YAML variables is currently not supported")

    # with open(path) as f:
    #     _raw = yaml.load(f.read(), Loader=yaml.FullLoader)

    # def _entrypoint(search, current, value, parent):
    #     if type(value) in [dict]:
    #         current = current+1
    #         parent = value
    #         _iterate_dict(search, current, value, parent)
    #     if type(value) in [list, tuple]:
    #         current = current+1
    #         parent = value
    #         _iterate_list(search, current, value, parent)
    #     if type(value) in [str, int, bool]:
    #         print(f"{search[current]} with value {value} in {parent}")
    #         exit(1)

    # def _iterate_dict(search, current, value, parent):
    #     for k, v in value.items():
    #         if k == search[current]:
    #             _entrypoint(search, current, v, parent)

    # def _iterate_list(search, current, value, parent):
    #     _entrypoint(search, current, value[search[current]], parent)

    # _search = [int(x) if is_integer(x) else x for x in key.split("/")]
    # _current = 0

    # for i in range(len(_search)):
    #     for k, v in _raw.items():
    #         if _search[_current] == k:
    #             _entrypoint(_search, _current, v, _raw)

    # with open(path, "w") as f:
    #     yaml.dump(_raw)

    # return True
