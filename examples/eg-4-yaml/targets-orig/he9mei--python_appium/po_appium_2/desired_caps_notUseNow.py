# app启动配置代码，读取yaml数据

import yaml  #需要先安装pyYAML插件
# from appium import webdriver

file = open("desired_caps.yaml","r")
data = yaml.load(stream=file, Loader=yaml.FullLoader)

# 直接将desired_caps导入conftest.py，用不了，总是提示：
# E  selenium.base.exceptions.WebDriverException: Message: Desired Capabilities must be a dictionary
# 暂时解决办法：直接将本也没内容写在conftest.py中
desired_caps = {
    "automationName": data["automationName"],
    "platformName": data["platformName"],
    "platformVersion": data["platformVersion"],
    "deviceName": data["deviceName"],
    "appPackage": data["appPackage"],
    "appActivity": data["appActivity"],
    "noReset": data["noReset"]
}

'''
desired_caps = {}
desired_caps["automationName"] = data["automationName"]
desired_caps["platformName"] = data["platformName"]
desired_caps["platformVersion"] = data["platformVersion"]
desired_caps["deviceName"] = data["deviceName"]
desired_caps["appPackage"] = data["appPackage"]
desired_caps["appActivity"] = data["appActivity"]
desired_caps["noReset"] = data["noReset"]
'''

# 暂时没有用上这里的driver，conftest.py文件中重新写的，无法直接导入；或者直接把该文件内容写入contest.py中
#driver = webdriver.Remote("http://"+str(data["ip"])+":"+str(data["port"])+"/wd/hub", desired_caps)