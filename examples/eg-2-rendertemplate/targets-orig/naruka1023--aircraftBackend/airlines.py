from flask import Flask, render_template, redirect, url_for, request, session
# from flask_socketio import SocketIO
import sqlite3 as sql
import requests
import json
import datetime

app = Flask(__name__)

relativeCountryQuery = ''

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


@app.route('/')
def home():
    con = sql.connect("airlines.db")
    con.row_factory = dict_factory
    cur = con.cursor()

    cur.execute('select * from AirlineRoute')
    content = cur.fetchall()

    cur.execute('select distinct icao from AirlineRoute') 
    icao = cur.fetchall()
    icao = [ic['icao'] for ic in icao  if ic['icao'] is not None]
    
    cur.execute('select distinct name from AirlineRoute') 
    name = cur.fetchall()
    name = [ic['name'] for ic in name  if ic['name'] is not None]

    cur.execute('select * from EquipmentDatabase')
    equipData = cur.fetchall()

    cur.execute('select distinct region from EquipmentDatabase')
    region = cur.fetchall()
    region = [ic['region'] for ic in region  if ic['region'] is not None]
    
    cur.execute('select distinct country from EquipmentDatabase')
    country = cur.fetchall()
    country = [ic['country'] for ic in country if ic['country'] is not None]
    print(country)
    con.close() 
    return render_template('home.html', content=content, icao=icao, equipData=equipData, name=name, region=region, country=country)

@app.route('/removeContent', methods=['POST'])
def removeContent():
    req_data = request.get_data()
    flag = json.loads(req_data)['load']
    if flag == 'equip':
        ids = json.loads(req_data)['edID']
        sql2 = 'DELETE FROM EquipmentDatabase where edID = %d' % int(ids)
    else:
        ids = json.loads(req_data)['edID']
        sql2 = 'DELETE FROM AirlineRoute where arID = %d' % int(ids)
    
    con = sql.connect("airlines.db")
    con.row_factory = dict_factory
    cur = con.cursor()
    cur.execute(sql2)
    con.commit()
    
    return 'success'


@app.route('/addContent', methods=['POST'])
def addContent():

    req_data = request.get_data()
    req_data = json.loads(request.get_data())
    keys = []
    values = []
    table = ''
    idFlag = ''
    if req_data['flag'] == 'route':
        table = 'AirlineRoute'
        idFlag = 'arID'
    else:
        table = 'EquipmentDatabase'
        idFlag = 'edID'
    for value in req_data['payload']:
        if value['value'] != '':
            keys.append(value['id'])
            values.append(value['value'])
    
    keys = (', ').join(keys)
    values = ['"' + value + '"' for value in values]
    values = (', ').join(values)
    sql2 = 'INSERT INTO ' + table + ' (' + keys + ') VALUES (' + values + ')'
     
     
    con = sql.connect("airlines.db")
    con.row_factory = dict_factory
    cur = con.cursor()
    cur.execute(sql2)
    con.commit()

    sql2 = 'SELECT * FROM ' + table + ' ORDER BY ' + idFlag + ' DESC'
    cur.execute(sql2)
    row = cur.fetchone()

    con.close()
    return row
@app.route('/updateContent', methods=['POST'])
def updateContent():

    req_data = request.get_data()
    req_data = json.loads(request.get_data())
    updateConditions = []
    table = '' 
    idFlag = ''
    if req_data['flag'] == 'equip':
        idFlag = 'edID'
        table = 'EquipmentDatabase'
    else:
        idFlag = 'arID'
        table = 'AirlineRoute'
    ids = 0
    for value in req_data['payload']:
        if value['id'] == "edID" or value['id'] == 'arID':
            ids = value['value']
            print('id')
        else:
            updateConditions.append(value['id'] + '="' + value['value'] + '"')
    updateConditions = (',').join(updateConditions)

    con = sql.connect("airlines.db")
    con.row_factory = dict_factory
    cur = con.cursor()
    print('update ' + table + ' set ' + updateConditions + ' where ' + idFlag + ' = ' + ids)
    cur.execute('update ' + table + ' set ' + updateConditions + ' where ' + idFlag + ' = ' + ids)
    con.commit()

    cur.execute('select * from ' + table + ' where ' + idFlag + ' = ' + ids)
    row = cur.fetchone()
    row = json.dumps(row)
    con.close()
    return row

@app.route('/searchRelativeCountries', methods=['POST'])
def searchRelativeCountries():
    global relativeCountryQuery

    req_data = request.get_data()
    req_data = json.loads(req_data)
    whereConditions = []
    for country in req_data['countries']:
        whereConditions.append("country = '{}'".format(country))
    whereConditions = " OR ".join(whereConditions)
    relativeCountryQuery = whereConditions
    sql2 = 'SELECT * FROM EquipmentDatabase WHERE ' + relativeCountryQuery

    con = sql.connect("airlines.db")
    con.row_factory = dict_factory
    cur = con.cursor()
    cur.execute(sql2)
    content = cur.fetchall()
    con.close()
    return json.dumps(content)

@app.route('/searchContent', methods=['POST'])
def searchContent():
    global relativeCountryQuery
    req_data = request.get_data()
    req_data = json.loads(req_data)
    whereConditions = []
    dateStart = ''
    dateEnd = ''

    for key,value in req_data['parameters'].items():
        if value is not '':
            if key == 'effectiveDateStart':
                dateStart = str(value)
            elif key == 'effectiveDateEnd':
                dateEnd = str(value)
            else:
                whereConditions.append("{} = '{}'".format(key, value))
    whereConditions = ' AND '.join(whereConditions)
    if whereConditions == '':
        sql2 = 'SELECT * FROM ' + req_data['flag']
        if dateStart != '':
            if dateEnd == '':
                sql2 += ' WHERE effectiveYear >= "' + dateStart + '"'
            else:
                sql2 += ' WHERE effectiveYear BETWEEN "' + dateStart + '" AND "' + dateEnd + '"'

            if relativeCountryQuery != '' and req_data['flag'] == "EquipmentDatabase":    
                sql2 += ' AND (' + relativeCountryQuery + ')'
        else:
            if relativeCountryQuery != '' and req_data['flag'] == "EquipmentDatabase":                
                sql2 += ' WHERE ' + relativeCountryQuery

    else:
        sql2 = 'SELECT * FROM ' + req_data['flag'] + ' WHERE ' + whereConditions
        if dateStart != '':
            if dateEnd == '':
                sql2 += ' AND effectiveYear >= ' + dateStart
            else:
                sql2 += ' AND effectiveYear BETWEEN ' + dateStart + ' AND ' + dateEnd
        if relativeCountryQuery != '' and req_data['flag'] == "EquipmentDatabase":
            sql2 += ' AND (' + relativeCountryQuery + ')'


    con = sql.connect("airlines.db")
    con.row_factory = dict_factory
    cur = con.cursor()
    cur.execute(sql2)
    content = cur.fetchall()
    con.close()

    return json.dumps(content)

if __name__ == '__main__':
    app.run()