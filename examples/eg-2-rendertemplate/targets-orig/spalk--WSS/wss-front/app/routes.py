import hashlib
from flask import render_template
from flask import request
from app import app
from app import db
from app.config import config
import datetime


@app.route('/')
@app.route('/index')
@app.route('/temperature')
def index():
    db_inst = db.DB()
    data_yandex = db_inst.get_data_for_chart('yandex')
    data_rp5 = db_inst.get_data_for_chart('rp5')
    data_narodmon = db_inst.get_data_for_chart('narodmon')
    db_inst.db_close()

    return render_template('temperature.html',
                           title='Temperature',
                           data_yandex=data_yandex,
                           data_rp5=data_rp5,
                           data_narodmon=data_narodmon)


@app.route('/pressure')
def pressure():
    db_inst = db.DB()
    data_yandex = db_inst.get_data_for_chart('yandex', parameter='pressure')
    data_rp5 = db_inst.get_data_for_chart('rp5', parameter='pressure')
    data_narodmon = db_inst.get_data_for_chart('narodmon', parameter='pressure')
    db_inst.db_close()

    return render_template('pressure.html',
                           data_yandex=data_yandex,
                           data_rp5=data_rp5,
                           data_narodmon=data_narodmon)

@app.route('/balcony')
def balcony():
    db_inst = db.DB()
    data_yandex = db_inst.get_data_for_chart('yandex', history_days=0)
    data_rp5 = db_inst.get_data_for_chart('rp5', history_days=0)
    data_narodmon = db_inst.get_data_for_chart('narodmon')
    data_sensor_t = db_inst.get_data_for_chart('wemos_south_balcony')
    data_sensor_h = db_inst.get_data_for_chart('wemos_south_balcony', parameter='humidity')
    data_sensor_t_ds = db_inst.get_data_for_chart('wemos_south_balcony_DS18B20')
    db_inst.db_close()

    return render_template('balcony.html',
                           title='Balcony Condition',
                           data_yandex=data_yandex,
                           data_rp5=data_rp5,
                           data_narodmon=data_narodmon,
                           data_sensor_t=data_sensor_t,
                           data_sensor_h=data_sensor_h,
                           data_sensor_t_ds=data_sensor_t_ds
                           )


@app.route('/sensor-data', methods=['GET', 'POST'])
def sensor_data():
    # http://localhost:5000/sensor-data?sensorname=esp8266&parameter=t&value=24&key=123
    sensor_name = request.args.get('sensorname')
    parameter = request.args.get('parameter')
    value = request.args.get('value')
    received_key = request.args.get('key')
    true_key = get_md5(sensor_name)[:6]
    if received_key == true_key:
        if parameter in ['t', 'p', 'h']:
            db_inst = db.DB()
            db_inst.save_sensor_data(sensor_name, parameter, value)
            db_inst.db_close()
            return 'ok'
        else:
            return 'Error: unknown parameter'
    else:
        return 'Error: key is wrong'


@app.route('/api/weather-and-forecast')
def api_weather_and_forecast():
    db_inst = db.DB()

    current_temp = db_inst.get_last_value('temperature', 'narodmon')[0]
    if current_temp > 0:
        current_temp = '+%s' % current_temp

    service = 'rp5'
    forecast_date = datetime.datetime.now()+datetime.timedelta(days=1)
    forecast_date = forecast_date.replace(hour=15, minute=0, second=0)
    forecast_date_display = forecast_date.strftime('%B %d')
    forecast_date_iso = forecast_date.isoformat(sep=' ', timespec='seconds')
    forecast_temp = db_inst.get_two_latest(forecast_date_iso, 'temperature', service, '*')
    if forecast_temp[0][1] == forecast_temp[1][1]:
        t1 = forecast_temp[0][3]
        t2 = forecast_temp[1][3]
        if t1 > t2:
            t1, t2 = t2, t1
        if t1 > 0:
            t1_str = '+%s' % t1
        else:
            t1_str = t1
        if t2 > 0:
            t2_str = '+%s' % t2
        else:
            t2_str = t1
        forecast_temp_display = "%s..%s" % (t1_str, t2_str)
    else:
        t = forecast_temp[0][3]
        if t > 0:
            t_str = '+%s' % t
        forecast_temp_display = t_str

    forecast_temp_display = forecast_temp_display.replace('.0','')

    db_inst.db_close()

    data = 'wss-data:%s,%s,%s,%s' % (current_temp, forecast_temp_display, forecast_date_display, service)
    return data


def get_md5(string):
    return hashlib.md5(string.encode('utf-8')).hexdigest()

