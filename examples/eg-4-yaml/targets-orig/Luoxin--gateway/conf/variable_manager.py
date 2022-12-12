import json
import os
import traceback
from enum import Enum

import yaml
from .utils import get_conf_file_path


class VariableManagerException(Exception):
    """variable manager base exception"""


class LoadFileNotFound(FileNotFoundError, VariableManagerException):
    """load file is not exist"""


class InvalidConfigurationFile(VariableManagerException, yaml.scanner.ScannerError):
    """Invalid configuration file"""


class UnsupportedConfigurationFileTypes(VariableManagerException):
    """Unsupported configuration file types"""


class VariableManager(object):
    _supported_file_types = ["yaml"]

    def __init__(self, load_file=False, file_type: str = "yaml"):
        self.load_file_path = ""
        self._variable = None
        self.file_type = ""
        if load_file:
            self.reload_file(load_file=load_file, file_type=file_type)

    def set_conf(self, key: str, value):
        self._variable[key] = value

    def set_load_file(self, load_file=False, file_type: str = "yaml") -> bool:
        """
        :param file_type: 如果加载文件有效，此变量才生效，默认yaml，其他类型正在添加支持
        :param load_file: 如果不传入，默认不加载文件，如果传入
                            如果传入True，使用默认路径加载文件
                            如果传入指定路径，使用指定路径加载文件
        :return bool: 返回是否修改成功
        """
        if isinstance(load_file, bool):
            if load_file:
                self.load_file_path = get_conf_file_path()
            else:
                return False
        elif isinstance(load_file, str):
            self.load_file_path = load_file
        elif isinstance(load_file, dict):
            self._variable = load_file
            self.file_type = "json"
            return False

        self.set_load_file_type(file_type=file_type)
        return True

    def set_load_file_type(self, file_type: str = "yaml"):
        """
        :param file_type: 如果加载文件有效，此变量才生效，默认yaml，其他类型正在添加支持
        :return:
        """
        if file_type not in self._supported_file_types:
            raise UnsupportedConfigurationFileTypes()
        self.file_type = file_type

    def reload_file(self, load_file=False, file_type: str = "yaml"):
        if not self.set_load_file(load_file=load_file, file_type=file_type):
            return

        # 先判断配置文件是否存在，后期做默认配置
        if self.load_file_path is None or not os.path.exists(self.load_file_path):
            raise FileNotFoundError(
                "conf file not found {}".format(self.load_file_path)
            )

        if self.file_type == "yaml":
            try:
                with open(self.load_file_path, encoding="utf-8") as f:
                    self._variable = yaml.load(f, Loader=yaml.FullLoader)
            except yaml.scanner.ScannerError:
                traceback.print_exc()
                raise InvalidConfigurationFile()
        else:
            raise UnsupportedConfigurationFileTypes()

    def get_conf(self, key):
        try:
            return self._variable.get(key)
        except:
            return None

    def get_conf_str(self, key, default: str = ""):
        try:
            value = self.get_conf(key)
            return str(value) if value is not None else default
        except:
            return default

    def get_conf_int(self, key, default: int = 0):
        try:
            value = self.get_conf(key)
            return int(value) if value is not None else default
        except:
            return default

    def get_conf_float(self, key, default: float = 0.0):
        try:
            value = self.get_conf(key)
            return float(value) if value is not None else default
        except:
            return default

    def get_conf_bool(self, key, default: bool = False):
        try:
            value = self.get_conf(key)
            return bool(value) if value is not None else default
        except:
            return default

    def get_conf_dict(self, key, default: dict = None):
        if default is None:
            default = {}
        try:
            value = self.get_conf(key)
            return dict(value) if value is not None else default
        except:
            return default

    def get_conf_json(self, key, default: dict = None):
        if default is None:
            default = {}
        try:
            value = self.get_conf(key)
            return json.loads(value) if value is not None else default
        except:
            return default

    def get_conf_list(self, key, default: list = None):
        if default is None:
            default = []
        try:
            value = self.get_conf(key)
            return list(value) if value is not None else default
        except:
            return default

    def get_conf_list_int(self, key, default: list = None):
        if default is None:
            default = []
        try:
            value = self.get_conf(key)

            temp = []
            if isinstance(value, list):
                for item in value:
                    try:
                        temp.append(int(item))
                    except:
                        pass
            else:
                temp = default

            return temp
        except:
            return default

    def get_conf_all(self):
        return self._variable

    def get_conf_enum(self, key, default: Enum = None):
        try:
            value = self.get_conf(key)
            if isinstance(value, Enum):
                return value
            return default
        except:
            return default

    def get_conf_with_type(self, key, value_type, default: Enum = None):
        try:
            value = self.get_conf(key)
            if isinstance(value, value_type):
                return value
            return default
        except:
            return default
