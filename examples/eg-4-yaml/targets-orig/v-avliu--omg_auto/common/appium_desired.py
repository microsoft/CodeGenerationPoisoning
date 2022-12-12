# coding=utf-8

import os
import sys
import logging
import yaml
from appium import webdriver

sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
from utilstest.base_device import *


def appium_desired(app_name, port):
    base_dir = os.path.dirname(os.path.dirname(__file__))

    fwd_caps_path = os.path.join(base_dir, 'config/appium_caps.yaml')
    with open(fwd_caps_path, 'r', encoding='utf-8') as file:
        data = yaml.load(file)

    if app_name == "app_path":
        app = data["app_path"]
    else:
        app = ""

    desired_caps = {
        "platformName": data["platformName"],
        "platformVersion": get_device_version(),
        "deviceName": get_device_name(),
        "udid": get_device_udid(),
        "app": app,
        "noReset": data["noReset"],
        "useNewWDA": False,
        "automationName": data["automationName"],
        "commandTimeouts": data["commandTimeouts"],
        "newCommandTimeout": data["newCommandTimeout"]
    }

    logging.info("Start APP.")

    driver = webdriver.Remote('http://' + str(data['ip']) + ':' + str(port) + '/wd/hub', desired_caps)
    driver.implicitly_wait(3)
    return driver


def appium_android_desired():
    desired_caps = {
        "platformName": "android",
        "platformVersion": get_android_devices_version(),
        "deviceName": get_device_name(),
        "deviceId": get_android_devices_id(),
        "appPackage": "com.tencent.mm",
        "noReset": True,
        "unicodeKeyboard": True,
        "resetKeyboard": True,
        "appActivity": "com.tencent.mm.ui.LauncherUI"
    }

    logging.info("Start APP.")
    driver = webdriver.Remote('http://127.0.0.1:4723/wd/hub', desired_caps)
    driver.implicitly_wait(3)
    return driver


if __name__ == '__main__':
    appium_desired("app_path", 4723)
