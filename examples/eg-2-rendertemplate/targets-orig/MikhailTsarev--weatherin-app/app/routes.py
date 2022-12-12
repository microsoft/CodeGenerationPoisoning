from flask import render_template, flash, redirect
from app import app
from app.forms import CityForm
from iso3166 import countries
import requests
import json
import datetime

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', start=True)

@app.route('/weather', methods = ['GET', 'POST'])
def create_response():
    form = CityForm()
    errors = []
    context = {'form': form,
               'city': 'Москва'}
    if form.validate_on_submit():
        city = form.city_name.data
        context.update({'city': city})
        res = requests.post('http://api.openweathermap.org/data/2.5/weather?q={}&type=like&units=metric&APPID=7ac3ad468ed360aa275f1bcac7c85e9b&lang=ru'.format(city))
        jsonData = res.json()
        code_from_api = jsonData['cod']
        if form.validate_city(code_from_api):
            temperature = str(jsonData['main']['temp'])
            if jsonData['main']['temp']>0:
                temperature = '+' + temperature
            feels_like = str(jsonData['main']['feels_like'])
            if jsonData['main']['feels_like']>0:
                feels_like = '+' + feels_like
            timestamp = jsonData['dt']
            dt = datetime.datetime.fromtimestamp(timestamp).strftime('%H:%M:%S %d.%m.%Y')
            cond = {'perception': (jsonData['main']['feels_like']<10),
                    'humidity': (jsonData['main']['humidity']>30),
                    'wind': ((-jsonData['main']['temp']-6+(5/6)*jsonData['wind']['speed'])>0) | (jsonData['wind']['speed']>5) | (jsonData['main']['temp']<5)}
            context.update({'weather': str(jsonData['weather'][0]['description']),
                            'coord': jsonData['coord'],
                            'country': countries.get(jsonData['sys']['country']).name,
                            'temp': temperature,
                            'feels_like': feels_like,
                            'humidity': str(jsonData['main']['humidity']),
                            'speed': str(jsonData['wind']['speed']),
                            'cond': cond,
                            'dt': str(dt),
                            'img': jsonData['weather'][0]['icon']})
            return render_template('weather.html', **context)
        errors.extend(form.city_name.errors)
        context.update({'errors': errors})
        return render_template('weather.html', **context)
    errors.extend(form.city_name.errors)
    context.update({'errors': errors})
    return render_template('weather.html', **context)
