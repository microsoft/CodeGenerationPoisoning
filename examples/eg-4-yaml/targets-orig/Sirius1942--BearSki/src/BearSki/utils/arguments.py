from BearSki.utils.singleton import Singleton
import json
import logging
import os
import yaml
from BearSki.utils.errors import ArgmentError
logger=logging.getLogger("Bear.unitl.args")
MESSAGE='''
      使用的是老配置文件，请使用新的格式的配置文件.json/yaml
      格式类似
      runner: PyTestRunner #设置用例执行器
  commands:
    - -s
unittestcase:
  mode: onecase
case:
  path: utest.testcase.atest_api_users.atest_api_users.case_api_users
  name: ""
skiconfig: ./SkiSetting.json
report:
  mode: html
  path: ./utest/report/report1.html
  addtime.now: true
auto:
  case_path: utest/testdata/model
  model_path": utest/testdata/model
log:
  filepath: utest/log/log.log,
  loglevel: INFO
'''
@Singleton
class runArg(object):
  
  def __init__(self):
    JSONFILE="config.json"
    YAMLFILE="config.yaml"
    if os.path.exists(JSONFILE):
      f = open(JSONFILE,'r', encoding="utf-8")
      self.argstr= json.load(f)
      if self.warning_message(self.argstr):
        raise ArgmentError(Exception, "使用老json格式，需要换成新的配置文件！{0}".format(MESSAGE))
      logger.info("获取运行参数 {0}".format(self.argstr))
    elif os.path.exists(YAMLFILE):
      file = open(YAMLFILE, 'r', encoding="utf-8")
      file_data = file.read()
      file.close()
      self.argstr = yaml.load(file_data, Loader=yaml.FullLoader)
      logger.info("获取运行参数 {0}".format(self.argstr))

  @property
  def mode(self):
    try:
      return self.argstr['unittestcase']['mode']
    except Exception as e:
      raise ArgmentError(e,"mode 参数配置错误")

  @property
  def report_mode(self):
    try:
      return self.argstr['report']['mode']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def report_path(self):
    try:
      return self.argstr['report']['path']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def case_name(self):
    try:
      return self.argstr['case']['name']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def case_path(self):
    try:
      return self.argstr['case']['path']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def jsonfile_path(self):
    try:
      return self.argstr['ski_filepath']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def testsuit_runner(self):
    try:
      return self.argstr['runner']['name']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def report_add_time(self):
    try:
      return self.argstr['report']['addtime.now']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def auto_case_path(self):
    try:
      return self.argstr['auto']['case_path']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def auto_model_path(self):
    try:
      return self.argstr['auto']['model_path']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def pytest_commands(self):
    try:
      return self.argstr['runner']['commands']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def log_filepath(self):
    try:
      return self.argstr['log']['file_path']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  @property
  def log_level(self):
    try:
      return self.argstr['log']['level']
    except Exception as e:
      raise ArgmentError(e, "参数配置错误")

  def __repr__(self):
    return str(self.argstr)

  def warning_message(self,jsonstr):
    if "m" in jsonstr:
      return True
    return False

