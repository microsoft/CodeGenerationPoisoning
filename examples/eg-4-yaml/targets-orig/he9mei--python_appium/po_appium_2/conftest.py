import os
import time
import allure
import pytest
from appium import webdriver
from time import sleep
import logging
import logging.config
import yagmail
from po_appium_1.base.base_page import BasePage
# from po_appium_2 import desired_caps
import yaml

app_driver = None

'''
desired_caps = {
    # "automationName": "Appium",
    "automationName": "UIAutomator2",  #appium新版本才能用(目前用的1.15.1)，老版本用不了
    "platformName": "Android",
    # "platformVersion": "8.0.0",  #华为手机
    # "deviceName": "HMKNW17727007061",
    "platformVersion": "7.1.1",  #OPPO手机
    "deviceName": "MJA68TGES4S4SKAY",
    # "platformVersion": "5.1",  #乐蒙手机
    # "deviceName": "MUGW8SOWWEY75NNDM",
    "appPackage": "com.dangdang.reader",  #adb shell pm list page -3
    "appActivity": ".activity.GuideActivity",  #adb shell dumpsys activity |grep com.dangdang.reader |grep LAUNCHER
    "noReset": True
}
'''

file = open("desired_caps.yaml", "r")
data = yaml.load(stream=file, Loader=yaml.FullLoader)

desired_caps = {
    "automationName": data["automationName"],
    "platformName": data["platformName"],
    "platformVersion": data["platformVersion"],
    "deviceName": data["deviceName"],
    "appPackage": data["appPackage"],
    "appActivity": data["appActivity"],
    "noReset": data["noReset"],
    "unicodeKeyboard": data["unicodeKeyboard"],
    "resetKeyboard": data["resetKeyboard"]
}

'''
# driver的addfinalizer写法
@pytest.fixture(scope="session", autouse=True)
def driver(request):
    # 定义为global的意图是为了在该py文件其他函数也可以用，比如之后的失败截图方法;
    # 定义为global需要先在py文件定义并赋初始值可以是None
    global app_driver  
    if app_driver is None:  #此处判断可以不写
        # app_driver = webdriver.Remote("http://localhost:4723/wd/hub", desired_caps)
        app_driver = webdriver.Remote("http://"+str(data["ip"])+":"+str(data["port"])+"/wd/hub", desired_caps)
        app_driver.implicitly_wait(10)
        print("启动driver")

    def end():
        sleep(5)
        app_driver.quit()
        print("关闭driver")

    request.addfinalizer(end)
    return app_driver
'''

# driver的yield写法
@pytest.fixture(scope="session", autouse=True)
def driver():
    global app_driver
    app_driver = webdriver.Remote("http://localhost:4723/wd/hub",desired_caps)
    app_driver.implicitly_wait(10)
    print("启动driver")
    return app_driver


@pytest.fixture(scope="session", autouse=True)
def driver_end():
    yield app_driver
    sleep(5)
    app_driver.quit()
    print("test end")

'''
#也可以写成这种格式，先定义一个字典，再加数据
caps = {}
caps["automationName"] = "Appium"
caps["platformName"] = "Android"
caps["platformVersion"] = "8.0.0"
caps["deviceName"] = "HMKNW17727007061"
caps["appPackage"] = "com.dangdang.reader"
caps["appActivity"] = ".activity.GuideActivity"
caps["noReset"] = "true"   #"true"或者True都可以，但是如果不写这个，每次启动都会清缓存重新启动
'''

'''
@pytest.fixture(scope="session")
def logger():
    CONF_LOG = "./log_notUseNow.conf"
    logging.config.fileConfig(CONF_LOG)
    logger = logging.getLogger()
    print("---打印日志---")
    return logger

# 目前用到使用fixture传入logger的位置包括：
# (1)basic的init方法,传入logger；
# (2)继承basic的page类，实例化时，传入logger;
# (3)每一个测试用例方法,传入logger
# 
# 问题：log使用配置文件的形式，可以；但是无法根据功能做区分。
# 解决办法：
# 不使用fixture的方式调用；
# (conftest.py文件中logger注释；log.conf文件暂时改名，放到base文件下，否则还是可以识别，不使用的话会报错)
# 封装方法获得logger，然后每个py文件调用该方法，并传入py_name

# 问题：每个py文件都重新赋值了logger，但是第二个py文件的log还是放在第一个py文件的py_name文件中。说明还是用的上一个py文件的logger
# 尝试解决：每个py文件前面生成logger；最后再移除ogger。（移除fh处理器）
# 结果：这样也不行，最后的解决办法是：每个py文件生成的logger名字不同，使用了py_name
'''


# 发送邮件，尝试在测试用例执行完毕之后，把测试报告当作附件发送
def send_mail(attachment):
    yag=yagmail.SMTP(user="hehuaimei123@163.com",
                 password="8uhb*UHB",
                 host="smtp.163.com")
    subject="自动化测试报告"
    contents="python自动化测试报告，自动发送。"
    yag.send(["hehuaimei@dangdang.com","hehuaimei123@163.com"],subject,contents,attachment)
    print("自动化测试报告已发送！")
'''
    # 执行完毕后自动发送邮件
    # send_mail("../test_result/report/html_report/report.html")
    # 问题1：report.html能正常发送，但是会丢失格式
    # 解决办法：--html=report.html --self-contained-html
    # send_mail("../test_result/report/allure_report")
    #问题2：发送文件夹会报错 TypeError: '../test_result/report/allure_report' is not a valid filepath
    # 用例执行完毕之前，报告还没有生成；这个时候发送，会找不到文件。
    # 并且allue-report不能直接打开，不能以文件夹形式发送
    #解决办法：使用jerkins执行用例，并且配置邮件自动发送allure和html两种报告
'''


# 失败截图方法
def fail_capture():
    # now = time.strftime("%Y-%m-%d_%H_%M_%S",time.localtime(time.time()))  #图片文件名加上日期和时间
    dt = time.strftime("%Y-%m-%d",time.localtime(time.time()))
    tm = time.strftime("%H-%M-%S",time.localtime(time.time()))  #由于文件夹是以日期命名的，文件名省去日期
    path = f"./test_result/fail_capture/{dt}"
    try:
        if not os.path.exists(path):
            os.makedirs(path)
        # filename=path+"/"+"fail_"+tm+".png"
        filename=f"{path}/fail_{tm}.png"
        # print(f"失败截图方法中的driver是:{app_driver}")  # 确认此处的driver就是setup的driver
        app_driver.get_screenshot_as_file(filename)  # 调用driver的截图方法

        # 把失败截图放到allure中
        with allure.step("添加失败截图"):
            with open(filename, mode="rb") as f:
                file = f.read()
            allure.attach(file, "fail_capture", allure.attachment_type.PNG)
            # 此处图片名字待改进，否则多张图时，不好区分

    except Exception as e:
        print(e)


# 失败监听+失败截图
# 参考：
# https://blog.csdn.net/ezreal_tao/article/details/100148446
# https://www.cnblogs.com/xiaogongjin/p/11705914.html
# https://blog.csdn.net/weixin_30915275/article/details/94862440
# https://blog.csdn.net/liyacai_20120512/article/details/102797042

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    '''
    hook pytest失败
    :param item:
    :param call:
    :return:
    '''
    # execute all other hooks to obtain the report object
    outcome = yield
    rep = outcome.get_result()

    # we only look at actual failing test calls, not setup/teardown
    if rep.when == "call" and rep.failed:

        path = "./test_result/"  # 我自己添加的failures文件的路径,默认放在主路径
        if not os.path.exists(path):
            os.makedirs(path)

        mode = "a" if os.path.exists(f"{path}failures") else "w"
        with open(f"{path}failures", mode) as f:
            # let's also access a fixture for the fun of it
            if "tmpdir" in item.fixturenames:
                extra = " (%s)" % item.funcargs["tmpdir"]
            else:
                extra = ""
            f.write(rep.nodeid + extra + "\n")
        fail_capture()  # 方式1：调用失败截图并加入allure的方法

        # 方式2：直接使用以下方式也可以，直接把失败截图添加到allure（但是图片不会保存到本地）
        # with allure.step('添加失败截图'):
        #     allure.attach(app_driver.get_screenshot_as_png(), "失败截图", allure.attachment_type.PNG)