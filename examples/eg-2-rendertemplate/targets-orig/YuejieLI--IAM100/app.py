import os
import sys
import json
import random
import time
from datetime import datetime, timedelta
# from authlib.flask.client import OAuth
from authlib.client import OAuth2Session
# from authlib.client import OAuth2Session
# from authlib.integrations.requests_client import OAuth2Session
# https://docs.authlib.org/en/stable/client/oauth2.html
import requests
from flask import Flask,  render_template, Response, request, redirect, url_for

app = Flask(__name__)

port = int(os.environ.get('PORT', 3000))

@app.route('/')
def index():
    # return 'Hello World! I love Python!'
    url_str = 'www.baidu.com. This is a url string'

    my_list = [1, 2, 3, 4, 4, 5, 6, 7, 8]

    my_dic = {'name': 'yuejie',
              'age': 47


              }

    return render_template('index.html', url_str=url_str, my_list=my_list,my_dic=my_dic)


# @app.route("/test",methods=['POST','GET'])
# def test():
#     return "我是测试的"




#
@app.route("/jwt",methods=['POST','GET'])
def get_jwt():

    token_url = "https://iamsuite.authentication.eu10.hana.ondemand.com/oauth/token"
    headers = {
        'Content-Type': 'application/json'
         }
    client_id = "sb-c656110e-a4f3-4d65-ad25-e0cfc2b4f701!b22856|ain_broker_poc!b1537"
    client_secret = "ticM0qWro6XpjT+wOEvfy0qGj5E="
    session = OAuth2Session(client_id, client_secret)
    token = session.fetch_access_token(token_url)
    jwt_access_token = token['access_token']
    return jwt_access_token

# print(jwt_token)  #in prod app, no need to print jwt_token(access token) on screen

# Above coding is to obtain Access_Token

# jwt_token = get_jwt()
#
# print(jwt_token)


#  Obtain ASPM jwt

@app.route("/jwt_ASPM",methods=['POST','GET'])
def get_jwt_ASPM():

    token_url = "https://iamsuite.authentication.eu10.hana.ondemand.com/oauth/token"
    client_id = "sb-6a530267-2f0c-486e-a3ec-a8214e24ac7b!b22856|aspm_broker_poc!b1537"
    client_secret = "gx5/JxUiXuKgux/CJN1sfcrrX7c="
    session = OAuth2Session(client_id, client_secret)
    token = session.fetch_access_token(token_url)
    aspm_access_token = token['access_token']
    return aspm_access_token

# jwt_token_ASPM = get_jwt_ASPM()



# test


# headers1 is used for AIN instance （indicator, equipment, model, location, etc
# headers1 = {
#     'Content-Type': 'application/json',
#     'Authorization': 'Bearer '+ jwt_token # the access token(jwt_token) as a header with name
#     # Authorization and value Bearer <token value>
#            }
#
#
# # headers2 is used for ASPM instance (risk assessment, FMEA)
# headers2 = {
#     'Content-Type': 'application/json',
#     'Authorization': 'Bearer '+ jwt_token_ASPM # the access token(jwt_token_ASPM) as a header with name
#     # Authorization and value Bearer <token value>
#            }

# end point for Get ALL Business Object info
api_end_point_equipment = "https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment"
api_end_point_location = "https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/location"
api_end_point_modelrequest = "https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/modelrequests"
api_end_point_equipmentrequest = "https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipmentrequests"
api_end_point_model = "https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/models"
api_end_point_riskassessment = "https://aspm-poc.cfapps.eu10.hana.ondemand.com/aspm/services/api/v1/aspm/riskassessments"
api_end_point_indicators = "https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/indicators"


days = 1 # 指删除多少天前生成的equipment，1就是指最近一天生成的

@app.route("/delete_equipment",methods=['GET','POST','DELETE'])
def delete_equipment():
    jwt_token = get_jwt()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + jwt_token  # the access token(jwt_token) as a header with name
        # Authorization and value Bearer <token value>
    }

    get_all_object = requests.get(url=api_end_point_equipment, json=True, headers=headers)
    # use requests.get method to obtain all equipment from remote api, and gave json object(stream) to get_all_equipment
    # response_json = get_all_object.content.decode(encoding='utf-8', errors='ignore')
    # response_json = get_all_object.content.decode()
    # 把get_all_equipment从远程endpoint返回的json对象decode成json字符串格式,with ""

    # print (response_json) # json object, with ""
    #
    # python_dict = json.loads(response_json.text, strict=False)  # 把json转化成python dict format with ''
    # python_dict = json.loads(get_all_object.text, strict=False)  # 把json转化成python dict format with ''
    python_dict = json.loads(get_all_object.content, encoding='utf-8', strict=False)  # 把json转化成python dict format with ''
    # python_dict = json.loads(get_all_object.content).encoding=('utf-8')  # 和上边一行一样
    print (python_dict)




    # 使用json.loads 方法把json字符串转化成python 字典格式 ‘’
    dayseconds = 86400  #一天等于 24 x 3600 = 86400 seconds
    now = datetime.now()  # datetime.now 方法可以获得当前时间
    timestampnow = int(now.timestamp()) #now.timestamp方法把当前时间点转化成epoch 时间格式：1970年一月一日开始到现在的秒数
    objectIdList = []  # 建立一个空列表, 此空列表不能在for循环内，否则每次只能存储一个元素，每次循环开始都清空
    # while True:
    for i in python_dict:  #python_dict是一个列表，后面不能加(),否则会报错，只有函数后面才加括号。使用for循环遍历所有equipment字典
        date = i['createdOn']/1000 # 把createOn的epoch数据除以1000并赋给date 变量。 i是python_dict字典里的每一个键值对
        #i['createdOn]指把该键对应的value取出来，赋给date变量，此时date里是浮点指

        if timestampnow - int(date) <= dayseconds*days: # int把浮点取整数， 而timestampnow已经在前面取整 int(now.timestamp())
            #当前时间的epoch数值减去取到的字典里equipment生成的时间点，如果小于预制天数，则需要删除

            Id = i['equipmentId']  #把equipmentid的value取出
            Name = i['name']  #取出equipment的命名
            objectIdList.append(Id) #把符合条件的equipmentId加入到空列表中
            dt = datetime.fromtimestamp(date) #把epoch时间转化成可读格式赋给dt以便后面使用
            # print('please note equipment with name %s has been deleted' %equipmentName)
            r = requests.delete(url=api_end_point_equipment + '(' + Id + ')', json=True, headers=headers)
            responsecode = r.status_code
            # api book: DELETE method : /equipment({equipmentID})  小括号需要保留，里面的大括号不能留
            # https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment(95295C08924146D0963D472DA0B5D77B)
            print(f'{now} - Action: Deletion of equipment "{Name}" created on "{dt}" has been triggered!')
            print(f'Return code: {responsecode}')

        else:
            continue

    else:
        print('--------------------------------------------------------------------------------------------------------------------')
        print(f'{now} - Total: "{len(objectIdList)}" "Equipments" that have been created in passed "{days}" days got deleted!\n')
        return f'Deletion of Equipments created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'

# Above code are function delete_equipment()



@app.route("/delete_location",methods=['GET','POST','DELETE'])
def delete_location():
    jwt_token = get_jwt()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + jwt_token  # the access token(jwt_token) as a header with name
        # Authorization and value Bearer <token value>
    }
    get_all_object = requests.get(url=api_end_point_location, json=True, headers=headers)
    # use requests.get method to obtain all equipment from remote api, and gave json object(stream) to get_all_equipment
    response_json = get_all_object.content.decode()
    # 把get_all_equipment从远程endpoint返回的json对象decode成json字符串格式,with ""
    # print(response_json_location)  # json object, with ""
    python_dict = json.loads(response_json)  # 把json转化成python dict format with ''
    # 使用json.loads 方法把json字符串转化成python 字典格式 ‘’
    dayseconds = 86400  #一天等于 24 x 3600 = 86400 seconds
    now = datetime.now()  # datetime.now 方法可以获得当前时间
    timestampnow = int(now.timestamp()) #now.timestamp方法把当前时间点转化成epoch 时间格式：1970年一月一日开始到现在的秒数
    objectIdList = []  # 建立一个空列表, 此空列表不能在for循环内，否则每次只能存储一个元素，每次循环开始都清空
    # while True:
    for i in python_dict:  #python_dict是一个列表，后面不能加(),否则会报错，只有函数后面才加括号。使用for循环遍历所有equipment字典
        date = i['createdOn']/1000 # 把createOn的epoch数据除以1000并赋给date 变量。 i是python_dict字典里的每一个键值对
        #i['createdOn]指把该键对应的value取出来，赋给date变量，此时date里是浮点指

        if timestampnow - int(date) <= dayseconds*days: # int把浮点取整数， 而timestampnow已经在前面取整 int(now.timestamp())
            #当前时间的epoch数值减去取到的字典里equipment生成的时间点，如果小于预制天数，则需要删除

            Id = i['locationId']  #把equipmentid的value取出
            Name = i['name']  #取出equipment的命名
            objectIdList.append(Id) #把符合条件的equipmentId加入到空列表中
            dt = datetime.fromtimestamp(date) #把epoch时间转化成可读格式赋给dt以便后面使用
            # print('please note equipment with name %s has been deleted' %equipmentName)
            # print(Id)
            r = requests.delete(url=api_end_point_location + '(' + Id + ')', json=True, headers=headers)
            responsecode = r.status_code
            # api book: DELETE method : /equipment({equipmentID})  小括号需要保留，里面的大括号不能留
            # https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment(95295C08924146D0963D472DA0B5D77B)
            print(f'{now} - Action: Deletion of location "{Name}" created on "{dt}" has been triggered!')
            print(f'Return code: {responsecode}')
            # print(objectIdList)

        else:
            continue

    else:
        print('--------------------------------------------------------------------------------------------------------------------')
        print(f'{now} - Total: "{len(objectIdList)}" "Locations" that have been created in passed "{days}" days got deleted!\n')
        return f'Deletion of Locations created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'


# if there is equipment attahed to it, then the location can not be deleted

@app.route("/delete_model_request",methods=['GET','POST','DELETE'])
def delete_model_request():
    jwt_token = get_jwt()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + jwt_token  # the access token(jwt_token) as a header with name
        # Authorization and value Bearer <token value>
    }
    get_all_object = requests.get(url=api_end_point_modelrequest, json=True, headers=headers)
    # use requests.get method to obtain all equipment from remote api, and gave json object(stream) to get_all_equipment
    response_json = get_all_object.content.decode()
    # 把get_all_equipment从远程endpoint返回的json对象decode成json字符串格式,with ""
    # print(response_json_location)  # json object, with ""
    python_dict = json.loads(response_json)  # 把json转化成python dict format with ''
    # 使用json.loads 方法把json字符串转化成python 字典格式 ‘’
    dayseconds = 86400  #一天等于 24 x 3600 = 86400 seconds
    now = datetime.now()  # datetime.now 方法可以获得当前时间
    timestampnow = int(now.timestamp()) #now.timestamp方法把当前时间点转化成epoch 时间格式：1970年一月一日开始到现在的秒数
    objectIdList = []  # 建立一个空列表, 此空列表不能在for循环内，否则每次只能存储一个元素，每次循环开始都清空
    # while True:
    for i in python_dict:  #python_dict是一个列表，后面不能加(),否则会报错，只有函数后面才加括号。使用for循环遍历所有equipment字典
        date = i['createdOn']/1000 # 把createOn的epoch数据除以1000并赋给date 变量。 i是python_dict字典里的每一个键值对
        #i['createdOn]指把该键对应的value取出来，赋给date变量，此时date里是浮点指

        if timestampnow - int(date) <= dayseconds*days: # int把浮点取整数， 而timestampnow已经在前面取整 int(now.timestamp())
            #当前时间的epoch数值减去取到的字典里equipment生成的时间点，如果小于预制天数，则需要删除

            Id = i['id']  #把equipmentid的value取出
            Name = i['description']  #只有description attribue，没有name 属性
            objectIdList.append(Id) #把符合条件的equipmentId加入到空列表中
            dt = datetime.fromtimestamp(date) #把epoch时间转化成可读格式赋给dt以便后面使用
            # print('please note equipment with name %s has been deleted' %equipmentName)
            # print(Id)
            r = requests.delete(url=api_end_point_modelrequest + '/' + Id, json=True, headers=headers)
            responsecode = r.status_code
            # api book: DELETE method : /equipment({equipmentID})  小括号需要保留，里面的大括号不能留
            # https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment(95295C08924146D0963D472DA0B5D77B)
            print(f'{now} - Action: Deletion of model request "{Name}" created on "{dt}" has been triggered!')
            print(f'Return code: {responsecode}')
            # print(objectIdList)
            # print(equipmentId)
        else:
            continue

    else:
        print('--------------------------------------------------------------------------------------------------------------------')
        print(f'{now} - Total: "{len(objectIdList)}" "Model Reqeust" that have been created in passed "{days}" days got deleted!\n')
        return f'Deletion of Model Requests created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'

# can only set status to Deleted, but the entry still there, why? and how to delete it as whole?


@app.route("/delete_equipment_request",methods=['GET','POST','DELETE'])
def delete_equipment_request():
    jwt_token = get_jwt()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + jwt_token  # the access token(jwt_token) as a header with name
        # Authorization and value Bearer <token value>
    }
    get_all_object = requests.get(url=api_end_point_equipmentrequest, json=True, headers=headers)
    # use requests.get method to obtain all equipment from remote api, and gave json object(stream) to get_all_equipment
    response_json = get_all_object.content.decode()
    # 把get_all_equipment从远程endpoint返回的json对象decode成json字符串格式,with ""
    # print(response_json_location)  # json object, with ""
    python_dict = json.loads(response_json)  # 把json转化成python dict format with ''
    # 使用json.loads 方法把json字符串转化成python 字典格式 ‘’
    dayseconds = 86400  #一天等于 24 x 3600 = 86400 seconds
    now = datetime.now()  # datetime.now 方法可以获得当前时间
    timestampnow = int(now.timestamp()) #now.timestamp方法把当前时间点转化成epoch 时间格式：1970年一月一日开始到现在的秒数
    objectIdList = []  # 建立一个空列表, 此空列表不能在for循环内，否则每次只能存储一个元素，每次循环开始都清空
    # while True:
    for i in python_dict:  #python_dict是一个列表，后面不能加(),否则会报错，只有函数后面才加括号。使用for循环遍历所有equipment字典
        date = i['createdOn']/1000 # 把createOn的epoch数据除以1000并赋给date 变量。 i是python_dict字典里的每一个键值对
        #i['createdOn]指把该键对应的value取出来，赋给date变量，此时date里是浮点指

        if timestampnow - int(date) <= dayseconds*days: # int把浮点取整数， 而timestampnow已经在前面取整 int(now.timestamp())
            #当前时间的epoch数值减去取到的字典里equipment生成的时间点，如果小于预制天数，则需要删除

            Id = i['id']  #把equipmentid的value取出
            Name = i['description']  #取出equipment的命名。没有name 属性，只有description属性
            objectIdList.append(Id) #把符合条件的equipmentId加入到空列表中
            dt = datetime.fromtimestamp(date) #把epoch时间转化成可读格式赋给dt以便后面使用
            # print('please note equipment with name %s has been deleted' %equipmentName)
            r = requests.delete(url=api_end_point_equipmentrequest + '/' + Id, json=True, headers=headers)
            responsecode = r.status_code
            # api book: DELETE method : /equipment({equipmentID})  小括号需要保留，里面的大括号不能留
            # https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment(95295C08924146D0963D472DA0B5D77B)
            print(f'{now} - Action: Deletion of equipment request "{Name}" created on "{dt}" has been triggered!')
            print(f'Return code: {responsecode}')
            # print(objectIdList)
            # print(equipmentId)
        else:
            continue

    else:
        print('--------------------------------------------------------------------------------------------------------------------')
        print(f'{now} - Total: "{len(objectIdList)}" "Equipment Request" that have been created in passed "{days}" days got deleted!\n')
        return f'Deletion of Equipments Requests created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'


# can only set status to Deleted, but the entry still there, why? and how to delete it as whole?


@app.route("/delete_model",methods=['GET','POST','DELETE'])
def delete_model():
    jwt_token = get_jwt()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + jwt_token  # the access token(jwt_token) as a header with name
        # Authorization and value Bearer <token value>
    }
    get_all_object = requests.get(url=api_end_point_model, json=True, headers=headers)
    # use requests.get method to obtain all equipment from remote api, and gave json object(stream) to get_all_equipment
    response_json = get_all_object.content.decode()
    # 把get_all_equipment从远程endpoint返回的json对象decode成json字符串格式,with ""
    # print(response_json_location)  # json object, with ""
    python_dict = json.loads(response_json)  # 把json转化成python dict format with ''
    # 使用json.loads 方法把json字符串转化成python 字典格式 ‘’
    dayseconds = 86400  #一天等于 24 x 3600 = 86400 seconds
    now = datetime.now()  # datetime.now 方法可以获得当前时间
    timestampnow = int(now.timestamp()) #now.timestamp方法把当前时间点转化成epoch 时间格式：1970年一月一日开始到现在的秒数
    objectIdList = []  # 建立一个空列表, 此空列表不能在for循环内，否则每次只能存储一个元素，每次循环开始都清空
    # while True:
    for i in python_dict:  #python_dict是一个列表，后面不能加(),否则会报错，只有函数后面才加括号。使用for循环遍历所有equipment字典
        date = i['createdOn']/1000 # 把createOn的epoch数据除以1000并赋给date 变量。 i是python_dict字典里的每一个键值对
        #i['createdOn]指把该键对应的value取出来，赋给date变量，此时date里是浮点指

        if timestampnow - int(date) <= dayseconds*days: # int把浮点取整数， 而timestampnow已经在前面取整 int(now.timestamp())
            #当前时间的epoch数值减去取到的字典里equipment生成的时间点，如果小于预制天数，则需要删除

            Id = i['modelId']  #把equipmentid的value取出
            Name = i['name']  #取出equipment的命名。没有name 属性，只有description属性
            objectIdList.append(Id) #把符合条件的equipmentId加入到空列表中
            dt = datetime.fromtimestamp(date) #把epoch时间转化成可读格式赋给dt以便后面使用
            # print('please note equipment with name %s has been deleted' %equipmentName)
            r = requests.delete(url=api_end_point_model + '(' + Id + ')', json=True, headers=headers)
            responsecode = r.status_code
            # api book: DELETE method : /equipment({equipmentID})  小括号需要保留，里面的大括号不能留
            # https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment(95295C08924146D0963D472DA0B5D77B)
            print(f'{now} - Action: Deletion of model "{Name}" created on "{dt}" has been triggered!')
            print(f'Return code: {responsecode}')
            # print(objectIdList)
            # print(equipmentId)
        else:
            continue

    else:
        print('--------------------------------------------------------------------------------------------------------------------')
        print(f'{now} - Total: "{len(objectIdList)}" "Model" that have been created in passed "{days}" days got deleted!\n')
        return f'Deletion of Models created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'

@app.route("/delete_riskassessment",methods=['GET','POST','DELETE'])
def delete_riskassessment():  #riskassessment belongs to ASPM and requires a different token
    aspm_jwt_token = get_jwt_ASPM()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer '+ aspm_jwt_token # the access token(jwt_token_ASPM) as a header with name
        # Authorization and value Bearer <token value>
               }
    get_all_object = requests.get(url=api_end_point_riskassessment, json=True, headers=headers)
    # use requests.get method to obtain all equipment from remote api, and gave json object(stream) to get_all_equipment
    response_json = get_all_object.content.decode()
    # 把get_all_equipment从远程endpoint返回的json对象decode成json字符串格式,with ""

    # print (response_json) # json object, with ""
    #
    python_dict = json.loads(response_json)  # 把json转化成python dict format with ''
    # 使用json.loads 方法把json字符串转化成python 字典格式 ‘’
    dayseconds = 86400  #一天等于 24 x 3600 = 86400 seconds
    now = datetime.now()  # datetime.now 方法可以获得当前时间
    timestampnow = int(now.timestamp()) #now.timestamp方法把当前时间点转化成epoch 时间格式：1970年一月一日开始到现在的秒数
    objectIdList = []  # 建立一个空列表, 此空列表不能在for循环内，否则每次只能存储一个元素，每次循环开始都清空
    # while True:
    print(python_dict)
    print(type(python_dict))
    for i in python_dict:  #python_dict是一个列表，后面不能加(),否则会报错，只有函数后面才加括号。使用for循环遍历所有equipment字典
        date = i['CreatedOn']/1000 # 把createOn的epoch数据除以1000并赋给date 变量。 i是python_dict字典里的每一个键值对.
        # CreatedOn在ASPM中大小写敏感！这里是大写C而其他以上AIN BO里则为小写c
        # i['createdOn]指把该键对应的value取出来，赋给date变量，此时date里是浮点指

        if timestampnow - int(date) <= dayseconds*days: # int把浮点取整数， 而timestampnow已经在前面取整 int(now.timestamp())
            #当前时间的epoch数值减去取到的字典里equipment生成的时间点，如果小于预制天数，则需要删除

            Id = i['ID']  #把equipmentid的value取出
            Name = i['ShortDescription']  #取出riskassessment的命名,命名规则不统一，有的BO可能用‘Name’字段
            objectIdList.append(Id) #把符合条件的equipmentId加入到空列表中
            dt = datetime.fromtimestamp(date) #把epoch时间转化成可读格式赋给dt以便后面使用
            # print('please note equipment with name %s has been deleted' %equipmentName)
            # requests.delete(url=api_end_point_equipment + '(' + Id + ')', json=True, headers=headers1)
            r = requests.delete(url=api_end_point_riskassessment + '/' + Id, json=True, headers=headers)
            responsecode = r.status_code

            # api book: DELETE method : /equipment({equipmentID})  小括号需要保留，里面的大括号不能留
            # https://ain-poc.cfapps.eu10.hana.ondemand.com/services/api/v1/equipment(95295C08924146D0963D472DA0B5D77B)
            print(f'{now} - Action: Deletion of Assessment "{Name}" created on "{dt}" has been triggered!')
            print(f'Return code: {responsecode}')

        else:
            continue

    else:
        print('--------------------------------------------------------------------------------------------------------------------')
        print(f'{now} - Total: "{len(objectIdList)}" "Assessments" that have been created in passed "{days}" days got deleted!')
        return f'Deletion of Risk Assessment created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'




@app.route("/delete_all",methods=['GET','POST','DELETE'])
def delete_all():

    delete_equipment()
    delete_location()
    delete_model_request()
    delete_equipment_request()
    delete_model()
    delete_riskassessment()
    return f'Deletion of ALL above business objects created in last {days} days has been triggered successfully. Please check SCP Logs for more details.'


@app.route("/random_iot_emulator",methods=['GET','POST','DELETE'])
def random_iot_emulator():
    # replace these variables

    tenant = 'https://6b12752f-0dd5-4d14-9e4e-4e787e354e3e.eu10.cp.iot.sap:443/iot/gateway/rest/measures/'
    deviceAlternateId = '21efcf28-1c9e-4ce6-a614-6b370c563492'
    sensorAlternateId = '66c997c4-1c3e-4167-af8b-bb03c22ca5a3'
    capabilityBearingTempAlternateId = 'IG_9DD8BC10013344DD9D75DB88632C7D51'  # Bearing Temperature
    capabilityInflowTempAlternateId = 'IG_8595D71F0CEB4C8A9DCE7E8720A61717'  # Inflow Temperature
    capabilityOilLevelTempAlternateId = 'IG_32FFDAB61D894B2887D07E00A1E56F34'  # Oil Level

    postAddress = (tenant + deviceAlternateId)
    print('Posting to:', postAddress)

    # Time intervall for polling the sensor date in seconds
    timeIntervall = 2

    # Number of iterations
    iterations = 10

    for x in range(0, iterations):
        # try:
        print('')
        print('================================')
        print('- Reading and sending sensor data to remote iot gateway...')

        speed = random.randint(50, 60)
        valueSpeed = round(speed, 2)
        # valueSpeed = speed
        print('speed value = %d' % valueSpeed, 'MpH')

        bodyJson = {
            "capabilityAlternateId": capabilityBearingTempAlternateId,
            "sensorAlternateId": sensorAlternateId,
            # "measures": [{'I_Bearing_Temperature_1' : valueSpeed},{'I_Inflow_Temperature_1': valueSpeed},{'I_Oil_Level_1':valueSpeed}]
            # "measures": [{'I_Bearing_Temperature_1':valueSpeed}]
            "measures": [valueSpeed]

        }
        data = json.dumps(bodyJson)  # dump to json format data
        headers = {'content-type': 'application/json'}
        r = requests.post(postAddress, data=data, headers=headers, cert=('./certificate.pem', './certificate.key'))
        responseCode = r.status_code
        print(responseCode)
        print(str(bodyJson))
        if responseCode == 202:
            print('- Updating above sensor data to the remote iot gateway is successful')
        else:
            print(f'- Sensor data sending failed due to return code: {responseCode}')
        print(f'==> {x} HTTP Response: {responseCode}')

        # wait timeIntervall [s] before reading the sensor value again
        time.sleep(timeIntervall)

        # except IOError:
        #     print("Error occurs, maybe there is a temp network issue, please try to run this application later")

    return f'The Random IoT Data Emulator has been triggered successfully to generate {iterations} groups of random iot data. Please check SCP Logs for more details.'


# random_iot_emulator()


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=port, debug=True, ssl_context=('certificate.pem', 'certificate.key'))
    app.run(host='0.0.0.0', port=port)



# test git again
