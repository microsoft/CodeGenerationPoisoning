# file name : index.py
# pwd : /project_name/app/main/index.py
from flask import Blueprint, Flask, request, render_template, jsonify,flash, redirect, url_for,make_response
from flask import current_app as app
from urllib.request import urlopen, Request
import urllib
import bs4
import os
import pyrebase
#os.environ["GOOGLE_APPLICATION_CREDENTIALS"]='C:Users/CHOI/PycharmProjects\Javis\app\main\newagent-ehuvjt-e6ba5c4c7fa5.json'
import dialogflow
#from google.cloud import storage
import gcloud
from gcloud import storage
# 추가할 모듈이 있다면 추가
# function for responses
sentence = ''
location =''
date = ''
def results(page):
    # build a request object
    if page =='dialog':
        req = request.get_json(force=True)
        # fetch action from json
        sentence = req.get('queryResult').get('queryText')
        location = req.get('queryResult').get('parameters').get('location')
        date = req.get('queryResult').get('parameters').get('weather_date')
        print(sentence)
        print(location)
        print(date)
    elif page =='web':
        sentence = "오늘 성남 날씨"
        location = "성남"
        date = "오늘"
        print(location)
        print(date)
  #  enc_location = urllib.parse.quote(location + '+날씨')
    enc_location = urllib.parse.quote(sentence)
    url = 'https://search.naver.com/search.naver?ie=utf8&query=' + enc_location
    print(sentence)
    print(location)
    print(date)
    req = Request(url)
    page = urlopen(req)
    html = page.read()
    soup = bs4.BeautifulSoup(html, 'html5lib')
    result = ''
    if date == '오늘':
        table = soup.find(class_="today_area _mainTabContent")
        t_ary = list(table.stripped_strings)
        print(date + ' ' + location + ' 날씨는 ' + t_ary[0] + '도 이며 ' + t_ary[3])
        result = date + ' ' + location + ' 날씨는 ' + t_ary[0] + '도 이며 ' + t_ary[3]
    elif date == '내일':
        table = soup.find(class_="tomorrow_area _mainTabContent")
        t_ary = list(table.stripped_strings)
        print(date + ' ' + location + ' ' + t_ary[0] + ' 날씨는 ' + t_ary[1] + '도 이며 ' + t_ary[4])
        print(t_ary[7] + '에는 ' + t_ary[8] + '도 이며 ' + t_ary[11])
        result = date + ' ' + location + ' ' + t_ary[0] + ' 날씨는 ' + t_ary[1] + '도 이며 ' + t_ary[4] +'\n '+t_ary[7] + '에는 ' + t_ary[8] + '도 이며 ' + t_ary[11]
    elif date == '모레':
        table = soup.find(class_="tomorrow_area day_after _mainTabContent")
        t_ary = list(table.stripped_strings)
        result = date + ' ' + location + ' ' + t_ary[0] + ' 날씨는 ' + t_ary[1] + '도 이며 ' + t_ary[4]+ '\n ' +t_ary[7] + '에는 ' + t_ary[8] + '도 이며 ' + t_ary[11]
        print(date + ' ' + location + ' ' + t_ary[0] + ' 날씨는 ' + t_ary[1] + '도 이며 ' + t_ary[4])
        print(t_ary[7] + '에는 ' + t_ary[8] + '도 이며 ' + t_ary[11])

    elif '요일' in date:
        table = soup.find(class_="list_area _pageList")
        t_ary = list(table.stripped_strings)
        print(t_ary)
        day_index = t_ary.index(date[0])
        result =  t_ary[day_index] +"요일 최저랑 최고 온도는  각각"+  t_ary[day_index+9]+ "도 "+ t_ary[day_index+12]+"입니다."

    if result == '':
        print('날씨를 받아올 수가 없습니다.')

    # return a fulfillment response
    #return {'fulfillmentText': result}
    return result
week_day_post = []
week_img_result =[]
def weather_visual(sentence):
    location = "성남"
    date = "오늘"

    enc_location = urllib.parse.quote(sentence)
    url = 'https://search.naver.com/search.naver?ie=utf8&query=' + enc_location
    print(sentence)
    print(location)
    print(date)

    req = Request(url)
    page = urlopen(req)
    html = page.read()
    soup = bs4.BeautifulSoup(html, 'html5lib')

    result = ''
    table = soup.find(class_="today_area _mainTabContent")  #오늘 날씨
    week_day_table = soup.find(class_ = "list_area _pageList")  #주간 날씨
    location_table = soup.find(class_="btn_select")
    location_t = list(location_table.stripped_strings)
    print(location_t)
    #주간날씨, 오늘날씨 이미지 뽑기
    week_day_table_tag = str(soup.find(class_="list_area _pageList").findAll(class_ = "ico_state2"))
    week_day_table_tag = week_day_table_tag.replace('<span class="ico_state2 ', '')
    week_day_table_tag = week_day_table_tag.replace('"></span>', '').replace('[', '').replace(']','')
    week_img = week_day_table_tag.split(', ') #week image 최종 array

    print(week_img[3])
    for i in range(len(week_img)):
        week_img_result.append(week_img[i])

    print(week_img)
    weahter_img_tag = soup.find(class_="today_area _mainTabContent").findAll("span")[0].get('class')
    print(weahter_img_tag)

    tag = weahter_img_tag[1]
    '''
    ws1 = 맑음
    ws2 = 맑음 (달)
    ws5 = 구름 + 해 (구름많음)
    ws6 = 구름 + 달
    ws7 = 구름 (흐림)
    ws15 = 소나기
    ws9 = 구름 + 비
    ws22 = 구름+해 +비
    '''
    t_ary = list(table.stripped_strings)
    week_day_table_ary = list(week_day_table.stripped_strings)
    print(t_ary)
    print(week_day_table_ary)

    #주간 날씨 데이터 = week_day_post
    for i in range(0,57, 14):
        week_day_post.append(week_day_table_ary[i])
        week_day_post.append((week_day_table_ary[i+9]) + (week_day_table_ary[i+10]) + '/ ' + (week_day_table_ary[i+12]) + (
        week_day_table_ary[i+13]))

    print(week_day_post)

    weather = t_ary[0]+ t_ary[2]
    weather_info = t_ary[3]
    time_weather = t_ary[4] +t_ary[5]+"/"+ t_ary[7] +t_ary[8]
    feel = t_ary[9]+ ' ' +t_ary[10]
    print(weather)
    print(weather_info)
    print(time_weather)
    print(feel)
    arr = [weather,weather_info,time_weather,feel, location_t[0]]

    return arr

def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)
    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
        query_input = dialogflow.types.QueryInput(text=text_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)
        return response.query_result.fulfillment_text


main = Blueprint('main', __name__, url_prefix='/')
@main.route('/main', methods=['GET'])
def index():
    # /main/index.html은 사실 /project_name/app/templates/main/index.html을 가리킵니다.
    #crawling_result = results("web")
    weather = weather_visual("성남 날씨 알려줘")
    print("______________")
    print(week_img_result)
    firebaseConfig = {
        "apiKey": "AIzaSyCQXJQhF2Z6KppjLpW5cIGHQLlkkRIzRwM",
        "authDomain": "jarvis-69329.firebaseapp.com",
        "databaseURL": "https://jarvis-69329.firebaseio.com",
        "projectId": "jarvis-69329",
        "storageBucket": "jarvis-69329.appspot.com",
        "messagingSenderId": "693111507728",
        "appId": "1:693111507728:web:583f4a1fd777d27ad0b395"
    }

    firebase = pyrebase.initialize_app(firebaseConfig)

    db = firebase.database()

    #db.child("test").push({"company": "google"}) #update database
    LEDtoggle = db.child("LED").get().val()
    print(LEDtoggle)
    return render_template('/main/index.html', todayWeather = weather, weekdayImg = week_img_result, weather_info = week_day_post, LEDtoggle = LEDtoggle)

# create a route for webhook
@main.route('/webhook', methods=['GET', 'POST'])
def webhook():
    # return response
    implicit()
    return make_response(jsonify({'fulfillmentText':results('dialog')}))
    #return make_response(jsonify(results('dialog')))


@main.route('/send_message', methods=['POST'])
def send_message():
    #print(os.getenv('newagent-ehuvjt'))
    message = request.form['message']
   # project_id = os.getenv('newagent-ehuvjt')
    fulfillment_text = detect_intent_texts('newagent-ehuvjt', "unique", message, 'ko')
    response_text = { "message":  fulfillment_text, "temp": weather_visual(message),
                      "info": week_day_post,  "img": week_img_result}
    #response_text = {"message": weather_visual() }
    print(response_text)

    return jsonify(response_text)
    #return "hi"

def implicit():
    from google.cloud import storage
    # If you don't specify credentials when constructing the client, the
    # client library will look for credentials in the environment.
    storage_client = storage.Client()

    # Make an authenticated API request
    buckets = list(storage_client.list_buckets())
    print(buckets)