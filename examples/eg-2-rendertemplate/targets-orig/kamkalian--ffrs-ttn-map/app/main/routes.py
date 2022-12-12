#!/venv/bin/python3
from flask import render_template, redirect, flash, url_for, request
from flask import json
from app.main import bp
import requests
from datetime import datetime, timedelta
from app.models import Gateway, MessageLink, Message, Device
from sqlalchemy import and_, desc
from app.main.grid_view_preparation import GridViewPreparation


@bp.route('/grid_view')
def grid_view():
    '''
    Route für eine Karte mit allen Daten (lange Ladezeit!).
    '''
    # Messages für GridView preperieren
    gvp = GridViewPreparation(100000)
    geo_json_grid_view = gvp.geo_json()

    # troisdorf 50.820329, 7.141111
    center_lat = '50.820329'
    center_lon = '7.141111'
    distance = '25000'

    # center al tuple
    center = (center_lat, center_lon)

    # GeoJson von den Messages erstellen
    geo_json_messages = { 'type': 'FeatureCollection' }
    features = []
    geo_json_messages['features'] = features

    # GeoJson erstellen
    geo_json = { 'type': 'FeatureCollection' }
    features = []
    geo_json['features'] = features
    
    return render_template(
        'index.html',
        title=u'FFRS-TTN-Map',
        geo_json=json.dumps(geo_json),
        geo_json_messages=json.dumps(geo_json_messages),
        geo_json_grid_view=json.dumps(geo_json_grid_view),
        site='index')



@bp.route('/')
@bp.route('/index')
def index():
    '''
    Route für die Startseite.
    '''
    # Messages für GridView preperieren
    gvp = GridViewPreparation(20000)
    geo_json_grid_view = gvp.geo_json()

    # troisdorf 50.820329, 7.141111
    center_lat = '50.820329'
    center_lon = '7.141111'
    distance = '25000'

    # center al tuple
    center = (center_lat, center_lon)

    try:
        gateway_list = Gateway.query.all()
    except:
        return """Datenbank Fehler!"""

    # Messages holen
    message_list = Message.query.order_by(desc(Message.time)).limit(1000).all()
    
    # GeoJson von den Messages erstellen
    geo_json_messages = { 'type': 'FeatureCollection' }
    features = []
    
    for message in message_list:
        # feature aus allen Daten zusammensetzen und dem features dict hinzufügen
            feature = { 
                'type': 'Feature', 
                'geometry': {'type': 'Point', 'coordinates': [message.longitude, message.latitude] },
                'properties': {
                    'id': message.dev_id, 
                    'time': message.time,
                    },
            }
            features.append(feature)
    
    geo_json_messages['features'] = features
    
    # GeoJSON erstellen
    geo_json = { 'type': 'FeatureCollection' }
    features = []
    for gateway in gateway_list:
        
        # Hat das Gateway Koordinaten?
        if gateway.latitude and gateway.longitude:
            # print(gateway.gtw_id, gateway.last_seen)

            lat = gateway.latitude
            lon = gateway.longitude
        
            # feature aus allen Daten zusammensetzen und dem features dict hinzufügen
            feature = { 
                'type': 'Feature', 
                'geometry': {'type': 'Point', 'coordinates': [lon, lat] },
                'properties': {
                    'id': gateway.gtw_id, 
                    'gw_state': gateway_state(gateway.last_seen),
                    'description': gateway.description,
                    'owner': gateway.owner,
                    'last_seen': gateway.last_seen,
                    'brand': gateway.brand,
                    'model': gateway.model,
                    'antenna_model': gateway.antenna_model,
                    'placement': gateway.placement
                    },
            }
            features.append(feature)
        

    geo_json['features'] = features
    
    return render_template(
        'index.html',
        title=u'FFRS-TTN-Map',
        geo_json=json.dumps(geo_json),
        geo_json_messages=json.dumps(geo_json_messages),
        geo_json_grid_view=json.dumps(geo_json_grid_view),
        site='index')


def gateway_state(last_seen):
    '''
    Ermittelt anhand von 'last_seen' den Status eines Gateways.
    >5 Tage -> Gateway ist tot
    <=5 Tage und >10 Minuten -> Gateway ist offline
    <=10 Minuten -> Gateway ist online
    '''

    if not last_seen:
        return 'unkown'

    # Aktuelle Zeit holen
    now_dt = datetime.now()
    
    # Anzahl Tage zwichen last_seen und jetzt ausrechnen
    diff_days = (now_dt - last_seen).days

    # Anzahl Sekunden zwichen last_seen und jetzt ausrechnen.
    # Mit -3600 wird noch eine Stunde für die Zeitverschiebung abgezogen
    # TODO Problem mit der Zeitverschiebung muss noch anders gelöst werden
    diff_seconds = (now_dt - last_seen).total_seconds()
    
    # Abfragen und entsprechende Rückgabewerte
    if diff_days > 5:
        return 'deceased'
    else:
        if diff_seconds > 3600: # 60 minutes
            return 'offline'
        else:
            return 'online'
    
    # An dieser stelle wird 'unknown' zurückgegeben, wenn die anderen Regeln nicht gegriffen haben.
    return 'unknown'


@bp.route('/log')
def log():
    """
    Route zur Log Seite
    """

    last_messages = []
    try:
        # letzte Messages aus der Datenbank holen
        last_messages = Message.query.order_by(Message.time.desc()).limit(50).all()

        # for message in last_messages:
            # new_time = message.time + + timedelta(seconds=7200)
            # message.time = new_time
            #print(message.time, new_time)

    except:
        flash('Datenbank Fehler!')

    return render_template(
        'log.html',
        title=u'Log', last_messages=last_messages, site='log')


@bp.route('/impressum')
def impressum():
    """Route zum Impressum"""
    return render_template("impressum.html", title=u"Impressum", site="impressum")


@bp.route('/datenschutz')
def datenschutz():
    """Route zur Datenschutzerklärung"""
    return render_template("datenschutz.html", title=u"Datenschutz", site="datenschutz")