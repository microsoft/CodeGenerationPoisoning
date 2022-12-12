"""
    module(file) - 文件与文件夹处理模块.

    Main members:

        # get_file_names_recursion - 递归读取输入路径下的所有文件，file_names会递归更新.
        # read_file_texts - 读取文件内容.
        # read_file_iter - 读取文件内容，使用迭代器返回.
        # read_yaml_config - 解析yaml配置文件.
        # unzip_file - 解压zip文件.
"""
__all__ = [
    'get_file_names_recursion',
    'read_file_texts',
    'read_file_iter',
    'read_yaml_config',
    'unzip_file'
]
import codecs
import os
import pathlib
import zipfile
# 需要判断依赖的包
try:
    import yaml
except Exception:
    yaml = None

from qytPython.utils.requirement import check_requirement


def _check_requirement_yaml():
    return check_requirement(yaml, 'yaml')


def get_file_names_recursion(path, file_names):
    """ 递归读取输入路径下的所有文件，file_names会递归更新.

        @params:
            path - 待递归检索的文件夹路径.
            file_names - 待输出结果的文件名列表.

        @return:
            On success - 无返回值，文件输出至file_names中.
    """
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            get_file_names_recursion(file_path, file_names)
        else:
            file_names.append(file_path)


def read_file_texts(file_name, keep_original=False):
    """ 读取文件内容.

        @params:
            file_name - 文件路径.
            keep_original - 保持文件内容不变，默认会去掉空行以及每一行的左右空格.

        @return:
            On success - 文件内容列表，元素为每行.
    """
    with codecs.open(file_name, mode='r', encoding='utf8') as fr:
        texts = list()
        if keep_original:
            for line in fr:
                texts.append(line)
        else:
            # 去掉空行以及每一行的左右空格
            for line in fr:
                line = line.strip()
                if len(line) > 0:
                    texts.append(line)
        return texts


def read_file_iter(file_name, keep_original=False):
    """ 读取文件内容，使用迭代器返回.

        @params:
            file_name - 文件路径.
            keep_original - 保持文件内容不变，默认会去掉空行以及每一行的左右空格.

        @return:
            On success - 文件内容迭代器.
    """
    with codecs.open(file_name, mode='r', encoding='utf8') as fr:
        if keep_original:
            for line in fr:
                yield line
        else:
            # 去掉空行以及每一行的左右空格
            for line in fr:
                line = line.strip()
                if len(line) > 0:
                    yield line


def read_yaml_config(file_name):
    """ 解析yaml配置文件.

        @params:
            file_name - 文件路径.

        @return:
            On success - 解析后的配置对象，字典形式.
    """
    _check_requirement_yaml()
    with codecs.open(filename=file_name, mode='r', encoding='utf8') as fread:
        conf = yaml.load(fread, Loader=yaml.FullLoader)
    return conf


def unzip_file(zip_file, file_path):
    """ 解压zip文件.

        @params:
            zip_file - zip文件.
            file_path - 文件路径.

        @return:
            On success - 是否成功.
    """
    pathlib.Path(file_path).mkdir(parents=True, exist_ok=True)
    zipFile = zipfile.ZipFile(zip_file)
    for file in zipFile.namelist():
        zipFile.extract(file, file_path)
    zipFile.close()
    return True
