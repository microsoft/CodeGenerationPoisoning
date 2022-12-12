import yaml

from foxylib.tools.file.file_tool import FileTool
from foxylib.tools.log.logger_tool import FoxylibLogger


class YAMLTool:
    @classmethod
    def filepath2j(cls, filepath):
        logger = FoxylibLogger.func2logger(cls.filepath2j)

        utf8 = FileTool.filepath2utf8(filepath)
        # logger.info({"utf8": utf8})

        j = yaml.load(utf8)
        return j

