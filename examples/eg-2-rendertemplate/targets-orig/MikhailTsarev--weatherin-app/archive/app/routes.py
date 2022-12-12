from flask import render_template, flash, redirect
from app import app
from app.forms import CityForm
from operator import itemgetter
from iso3166 import countries
import requests
import json
import datetime
import pandas as pd

@app.route('/')
@app.route('/index')
def index():
    user = { 'nickname': 'Незнакомец' }
    return render_template('index.html', user = user)

@app.route('/weather', methods = ['GET', 'POST'])
def login():
    #iso = pd.read_excel('/static/iso3166_rus.xlsx')
    #iso.drop('Numeric', inplace=True)
    #iso['Country_en'] = [countries.get(row).name for row in iso['Alpha-2']]
    #choices = [", ".join(e for e in list) for list in iso[['Alpha-3','Country','Country_en']].values.tolist()]
    with open('C:/Users/d9ld9/github/weatherin/app/countries.json', 'r') as f:
        country_data = json.loads(json.load(f))
    choices = [(elem['Alpha-2'],elem['Country_en']) for elem in country_data]
    form = CityForm()
    form.country_choice.choices = choices
    errors = []
    context = {'form': form,
               'city': 'Москва',
               'country': '--optional--'}
    if form.validate_on_submit():
        city = form.city_name.data
        country = form.country_choice.data
        lang = [tup[0] for tup in choices if tup[1] == country]
        context.update({'city': city, 'country': country, 'lang': lang[0]})
        res = requests.post('http://api.openweathermap.org/data/2.5/weather?q={}&type=like&units=metric&APPID=7ac3ad468ed360aa275f1bcac7c85e9b&lang=ru'.format(city))
        jsonData = res.json()
        code = jsonData['cod']
        if form.validate_city(code):
            errors.extend(form.city_name.errors)
            context.update({'errors': errors})
            return render_template('weather.html', **context)
        errors.extend(form.city_name.errors)
        temp = str(jsonData['main']['temp'])
        if jsonData['main']['temp']>0:
            temp = '+' + temp
        feels_like = str(jsonData['main']['feels_like'])
        if jsonData['main']['feels_like']>0:
            feels_like = '+' + feels_like
        timestamp = jsonData['dt']
        dt = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d.%m.%Y')
        context.update({'errors': errors,
                        'weather': str(jsonData['weather'][0]['description']),
                        'coord': jsonData['coord'],
                        'country': countries.get(jsonData['sys']['country']).name,
                        'temp': temp,
                        'feels_like': feels_like,
                        'humidity': str(jsonData['main']['humidity']),
                        'speed': str(jsonData['wind']['speed']),
                        'dt': str(dt),
                        'img': jsonData['weather'][0]['icon']})
        return render_template('weather.html', **context)
    return render_template('weather.html', **context)
