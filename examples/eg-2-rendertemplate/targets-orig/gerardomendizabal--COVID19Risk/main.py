import os
# import magic
import urllib.request
# from app import app
from flask import Flask, flash, request, redirect, render_template, url_for, json
from werkzeug.utils import secure_filename
from datetime import datetime
import folium
from folium.plugins import HeatMap
import pymysql
import math

UPLOAD_FOLDER = './uploads'

app = Flask(__name__)

app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['json'])

USERNAME = 'dbadmincovid'
PASSW = 'Covid19'
DBHOST = '20.185.220.242'


# user='coviduser', passwd='covid'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


if __name__ == '__main__':
    app.run(debug=True);


@app.route('/UploadedConfirmation')
def uploadCase_confirmation():
    return render_template('CasUploadedConfirmation.html', Message="Se ha registrado el caso en la BD")


@app.route('/RiskReport/<value>')
def upload_RiskReport(value):
    value = str(value)
    vector = value.split(',')

    valueRisk = float(vector[0])
    VectorForMap = "["
    k = 1
    while k < len(vector):
        vectorPlace = "["
        vectorPlace = vectorPlace + str(vector[k])
        vectorPlace = vectorPlace + ","
        k = k + 1
        vectorPlace = vectorPlace + str(vector[k])
        vectorPlace = vectorPlace + ","
        k = k + 1
        vectorPlace = vectorPlace + str(vector[k])
        vectorPlace = vectorPlace + "]"
        k = k + 1
        VectorForMap = VectorForMap + vectorPlace
        if k < len(vector):
            VectorForMap = VectorForMap + ","
    VectorForMap = VectorForMap + "],"
    print(VectorForMap)

    valueRisk=round(valueRisk)
    if valueRisk == 0:
        messageToDisplay = "El Nivel de Riesgo Bajo, no se encontró ningún lugar en común con casos confirmados (Risk Score=0)"
    elif 0 < valueRisk <= 2:
        messageToDisplay = "El Nivel de Riesgo Medio, se encontró un lugar y hora común con un caso confirmado (Risk Score=" + str(
            valueRisk) + ")"
    elif valueRisk > 2:
        messageToDisplay = "El Nivel de Riesgo Alto, se encontraron lugares y horas en común con casos infectados (Risk Score=" + str(
            valueRisk) + ")"
    return render_template('CasUploadedConfirmation.html', Message=messageToDisplay, VectorPlacesToDisplay=VectorForMap)


@app.route('/ShowHeatMap')
def show_heatmap():
    return render_template('heatmap.html')


@app.route('/')
def upload_form():
    return render_template('index.html')


@app.route('/AddCase')
def AddCase():
    return render_template('AddCase.html')


@app.route('/AssesRisk')
def AssesRisk():
    return render_template('AssessRisk.html')


@app.route('/upload_file_AddCase', methods=['POST'])
def upload_fileAddCase():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('File successfully uploaded')
            InsertDataToBD(filename)
            return redirect('/UploadedConfirmation')
        else:
            flash('Allowed file types are JSON only')
            return redirect(request.url)


# Simple routine to run a query on a database and print the results:
def insertcasePlace(conn, Lat, Long, InitT, FinalT, Conf, PID):
    dbhandler = conn.cursor()
    QueryTxt = "INSERT INTO COVID19.Cases (Latitude,Longitude,InitialTime,FinalTime,Confidence,PlaceID,DateInserted,status) Values ('"
    QueryTxt += str(Lat)
    QueryTxt += "','"
    QueryTxt += str(Long)
    QueryTxt += "','"
    QueryTxt += InitT
    QueryTxt += "','"
    QueryTxt += FinalT
    QueryTxt += "','"
    QueryTxt += str(Conf)
    QueryTxt += "','"
    QueryTxt += PID
    QueryTxt += "',NOW(),'1'"
    QueryTxt += ")"
    # print(QueryTxt)
    dbhandler.execute(QueryTxt)
    # print(dbhandler.lastrowid)


def CheckRiskPlace(conn, Lat, Long, InitT, FinalT, Conf, PID):
    dbhandler = conn.cursor()
    QueryTxt = "Select Latitude, Longitude, InitialTime,FinalTime FROM COVID19.Cases where Latitude>="
    QueryTxt += str(Lat - 10000)
    QueryTxt += " AND Latitude<="
    QueryTxt += str(Lat + 10000)
    QueryTxt += " AND Longitude>="
    QueryTxt += str(Long - 10000)
    QueryTxt += " AND Longitude<="
    QueryTxt += str(Long + 10000)

    QueryTxt += " AND ((FinalTime+86400000>="
    # QueryTxt += " AND ((FinalTime>="

    QueryTxt += InitT
    QueryTxt += " AND InitialTime<="

    QueryTxt += str(int(FinalT) + 86400000)
    # QueryTxt += FinalT

    QueryTxt += ") OR (InitialTime>="
    QueryTxt += InitT
    QueryTxt += " AND InitialTime<="
    QueryTxt += FinalT
    QueryTxt += "))"


    dbhandler.execute(QueryTxt)
    myresult = dbhandler.fetchall()
    Score = 0
    for x in myresult:
        LatCase = x[0]
        LongCase = x[1]
        InitialTimeCase = x[2]
        FinalTimeCase = x[3]
        Distance = ComputeDistanceLongLat(float(Lat) / 10000000, float(Long) / 10000000, float(LatCase) / 10000000,
                                          float(LongCase) / 10000000)
        # print(Distance)
        if Distance <= 100:
            print("Fecha y hora inicial del caso")
            print(datetime.fromtimestamp(float(InitialTimeCase)/1000.0))
            print("Fecha y hora final del caso")
            print(datetime.fromtimestamp(float(FinalTimeCase)/1000.0))
            print("Fecha y hora inicial del usuario")
            print(datetime.fromtimestamp(float(InitT)/1000.0))
            print("Fecha y hora final del usuario")
            print(datetime.fromtimestamp(float(FinalT)/1000.0))

            print("Distance")
            print(Distance)
            ScoreDistance = (1 / (1 + math.exp(-0.1 * (50 - Distance))))
            print("Score Distance")
            print(ScoreDistance)

            if int(InitT) > int(FinalTimeCase):
                TimeAfterCaseLeave = int(InitT)-int(FinalTimeCase)
                TimeAfterCaseLeaveHRs = TimeAfterCaseLeave/3.6e+6
                print("Time after leave in Hrs")
                print(str(TimeAfterCaseLeaveHRs))
                ScoreTime = (1 / (1 + math.exp(-0.1 * (12 - TimeAfterCaseLeaveHRs))))
                print("ScoreTime")
                print(str(ScoreTime))
            else:
                ScoreTime = 1
            Score = Score + (ScoreTime * ScoreDistance)

        print("Total score")
        print(Score)
        print("")
    return Score


def ComputeDistanceLongLat(lat1, lon1, lat2, lon2):
    R = 6378.137  # Radius of earth in KM
    dLat = lat2 * math.pi / 180 - lat1 * math.pi / 180
    dLon = lon2 * math.pi / 180 - lon1 * math.pi / 180
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(lat1 * math.pi / 180) * math.cos(
        lat2 * math.pi / 180) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    d = R * c
    return d * 1000  # meters


@app.route('/upload_file_AsessRisk', methods=['POST'])
def upload_fileAsessRisk():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash('File successfully uploaded')
            RiskScoreReport = CheckCoincidencesinBD(filename)
            print("El reporte es " + str(RiskScoreReport))
            urlToRedirect = '/RiskReport/' + str(RiskScoreReport)
            return redirect(urlToRedirect)
        else:
            flash('Allowed file types are JSON only')
            return redirect(request.url)


def CheckCoincidencesinBD(filename):
    site_root = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(site_root, "uploads", filename)
    data = json.load(open(json_url))
    # print(data['timelineObjects'][0].get('activitySegment'))
    # print(data['timelineObjects'][1]['activitySegment'])

    myConnection = pymysql.connect(host=DBHOST, user=USERNAME, passwd=PASSW, db='COVID19', charset="utf8mb4",
                                   autocommit=True)
    NumberOfVisitedPlaces = 0
    ListOfPlaces = []
    RiskScore = 0;
    for i in range(len(data['timelineObjects'])):
        # print(data['timelineObjects'][i])
        if data['timelineObjects'][i].get('placeVisit'):
            # print("Location found")
            # print('Latitude: ' + str(data['timelineObjects'][i]['placeVisit']['location']['latitudeE7']))
            Lat = data['timelineObjects'][i]['placeVisit']['location']['latitudeE7']
            # print('Longitude: ' + str(data['timelineObjects'][i]['placeVisit']['location']['longitudeE7']))
            Lon = data['timelineObjects'][i]['placeVisit']['location']['longitudeE7']
            # print('placeId: ' + str(data['timelineObjects'][i]['placeVisit']['location']['placeId']))
            PID = data['timelineObjects'][i]['placeVisit']['location']['placeId']
            # print('address: ' + str(data['timelineObjects'][i]['placeVisit']['location']['address']))

            # print('locationConfidence: ' + str(data['timelineObjects'][i]['placeVisit']['location']['locationConfidence']))
            Conf = data['timelineObjects'][i]['placeVisit']['location']['locationConfidence']
            StartTime = data['timelineObjects'][i]['placeVisit']['duration']['startTimestampMs']
            # print(datetime.fromtimestamp(float(StartTime)/1000.0))
            EndTime = data['timelineObjects'][i]['placeVisit']['duration']['endTimestampMs']
            # print(datetime.fromtimestamp(float(EndTime)/1000.0))
            NumberOfVisitedPlaces = NumberOfVisitedPlaces + 1
            ScoreThisPlace = CheckRiskPlace(myConnection, Lat, Lon, StartTime, EndTime, Conf, PID)
            Place = [float(data['timelineObjects'][i]['placeVisit']['location']['latitudeE7']) / 10000000,
                     float(data['timelineObjects'][i]['placeVisit']['location']['longitudeE7']) / 10000000,
                     ScoreThisPlace * 100]
            if ScoreThisPlace > 0:
                ListOfPlaces.append(Place)
            RiskScore += ScoreThisPlace
            # print("-----------------")

    myConnection.close()
    print("Number of visited places " + str(NumberOfVisitedPlaces))

    VectorToReturn = [RiskScore]
    if RiskScore > 0:
        for x in ListOfPlaces:
            for y in x:
                VectorToReturn.append(y)

    # print (VectorToReturn)
    VectorToReturnStr = ','.join([str(x) for x in VectorToReturn])
    return VectorToReturnStr


def InsertDataToBD(filename):
    site_root = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(site_root, "uploads", filename)
    data = json.load(open(json_url))
    # print(data['timelineObjects'][0].get('activitySegment'))
    # print(data['timelineObjects'][1]['activitySegment'])

    myConnection = pymysql.connect(host=DBHOST, user=USERNAME, passwd=PASSW, db='COVID19', charset="utf8mb4",
                                   autocommit=True)
    NumberOfVisitedPlaces = 0
    ListOfPlaces = []
    for i in range(len(data['timelineObjects'])):
        # print(data['timelineObjects'][i])
        if data['timelineObjects'][i].get('placeVisit'):
            # print("Location found")
            # print('Latitude: ' + str(data['timelineObjects'][i]['placeVisit']['location']['latitudeE7']))
            Lat = data['timelineObjects'][i]['placeVisit']['location']['latitudeE7']
            # print('Longitude: ' + str(data['timelineObjects'][i]['placeVisit']['location']['longitudeE7']))
            Lon = data['timelineObjects'][i]['placeVisit']['location']['longitudeE7']
            # print('placeId: ' + str(data['timelineObjects'][i]['placeVisit']['location']['placeId']))
            PID = data['timelineObjects'][i]['placeVisit']['location']['placeId']
            # print('address: ' + str(data['timelineObjects'][i]['placeVisit']['location']['address']))

            # print('locationConfidence: ' + str(data['timelineObjects'][i]['placeVisit']['location']['locationConfidence']))
            Conf = data['timelineObjects'][i]['placeVisit']['location']['locationConfidence']
            StartTime = data['timelineObjects'][i]['placeVisit']['duration']['startTimestampMs']
            # print(datetime.fromtimestamp(float(StartTime)/1000.0))
            EndTime = data['timelineObjects'][i]['placeVisit']['duration']['endTimestampMs']
            # print(datetime.fromtimestamp(float(EndTime)/1000.0))
            NumberOfVisitedPlaces = NumberOfVisitedPlaces + 1
            Place = [float(data['timelineObjects'][i]['placeVisit']['location']['latitudeE7']) / 10000000,
                     float(data['timelineObjects'][i]['placeVisit']['location']['longitudeE7']) / 10000000, 1000]
            ListOfPlaces.append(Place)
            insertcasePlace(myConnection, Lat, Lon, StartTime, EndTime, Conf, PID)
            # print("-----------------")

    myConnection.close()
    print("Number of visited places " + str(NumberOfVisitedPlaces))
    startingLocation = [ListOfPlaces[0][0], ListOfPlaces[0][1]]
    hmap = folium.Map(location=startingLocation, zoom_start=7)

    hm_wide = HeatMap(ListOfPlaces,
                      min_opacity=0.2,
                      max_val=100,
                      radius=17, blur=15,
                      max_zoom=1)
    # Adds the heatmap element to the map
    hmap.add_child(hm_wide)

    # Saves the map to heatmap.hmtl
    hmap.save(os.path.join('./templates/', 'heatmap.html'))
