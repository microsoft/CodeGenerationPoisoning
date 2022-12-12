from flask import Flask, render_template ,url_for,request,redirect,session,send_file
import urllib.parse
import pandas as py
import joblib as jobs
from matplotlib  import pyplot
import io
import os
import base64
import csv

app = Flask(__name__)
app.secret_key = 'loginner'

py.options.mode.chained_assignment = None
LoginData = py.read_csv(r"Login.csv")
cities = ["Bhandup", "Mumbai", "Visakhapatnam", "Ahmedabad", "Delhi", "Bangalore", "Pune", "Nagpur", "Panvel",
          "Vadodara",
          "Indore", "Ulhasnagar", "Bhopal", "Kolkata", "Kanpur", "New Delhi", "Kalyan", "Rajkot", "Ghaziabad",
          "Chennai",
          "Meerut", "Agra", "Jaipur", "Jabalpur"]
Weather = ["Spring", "Summer", "Monsoon", "Winter"]
Sex = ["Male", "Female"]
Road_Types = ["National Highways", "State Highways", "PWD Roads", " Rural Roads", "Urban Roads", "Project Roads"]
Vehicles = ["Bike","Car","Bus","Truck","Rickshaw"]

@app.route('/', methods =['GET','POST'])
def Login():
    if request.method == 'POST':
        LoginData = py.read_csv(r"Login.csv")
        Username = request.form['Username'];
        password = request.form['password'];
        print(Username)
        print(password)
        for row in LoginData.index:
            if LoginData['Username'][row] == Username and LoginData['Password'][row] == password:
                session['LoginFlag'] = True;
                session['UserType'] = int(LoginData['Usertype'][row])
                print(session['UserType'])
                return render_template('index.html',Usertype = session['UserType'])
        return render_template('login.html',error="Invalid UserID and Password")

    return render_template('login.html')


@app.route('/SignUp', methods =['GET','POST'])
def SignUp():
    if request.method == 'POST':
        Username = request.form['Username'];
        password = request.form['password'];
        flag = True
        for row in LoginData.index:
            if LoginData['Username'][row] == Username:
                return render_template('SignUp.html',error="UserId already exist please try again with different UserId")
        fields = [Username,password,2]
        with open(r'Login.csv', 'a') as f:
            writer = csv.writer(f)
            writer.writerow(fields)
        return render_template('login.html')
    return render_template('SignUp.html')


@app.route('/SignOut', methods =['GET','POST'])
def SignOut():
    print("signout called")
    if not session.get('LoginFlag'):
        return render_template('login.html')
    else:
        session['LoginFlag'] = False
    return render_template('login.html')

@app.route('/DownloadFile', methods =['GET'])
def DownloadFile():
    path = '/Login.csv';
    return send_file(os.path.dirname(os.path.abspath(__file__))+path, as_attachment=True)


@app.route('/Index', methods =['GET','POST'])
def home():
    if session['LoginFlag'] == True:
        return render_template('index.html',Usertype = session['UserType'])
    else:
        return render_template('login.html')


@app.route('/Stat', methods =['GET','POST'])
def Stat():
    if session['LoginFlag'] == True:

        return render_template('Stat.html')
    else:
        return render_template('login.html')


@app.route('/Predictor', methods =['GET','POST'])
def Predictor():
    if session['LoginFlag'] ==True:
       if request.method == 'POST':
            prediction = Predict(request)
            Accident_issues = [prediction,100-prediction]
            activities = ['Not Safe','Safe']
            pyplot.pie(Accident_issues, labels=activities, startangle=90, autopct='%.1f%%')

            img = io.BytesIO()  # create the buffer
            pyplot.savefig(img, format='png')  # save figure to the buffer
            img.seek(0)  # rewind your buffer
            plot_data = urllib.parse.quote(base64.b64encode(img.read()).decode())  # base64 encode & URL-escape
            return render_template('Predictor.html',cities =cities,Weather=Weather,Sex=Sex,Road_Types=Road_Types,Vehicles=Vehicles,PredictionGraph = plot_data)
       else:
            return render_template('Predictor.html',cities =cities,Weather=Weather,Sex=Sex,Road_Types=Road_Types,Vehicles=Vehicles)
    else:
        return render_template('login.html')


def Predict(x):
    vehicletype = Vehicles.index(x.form['VehicleType']);
    cityname = cities.index(x.form['city']);
    Weather1 = Weather.index(x.form['Weather']);
    RoadType = Road_Types.index(x.form['RoadType']);
    Sex1 = Sex.index(x.form['Sex']);
    Age = x.form['Age'];
    Speedlimit = x.form['Speedlimit'];
    model_clone = jobs.load('RoadAccidentPredictor.pkl')
    obj = {"VehicleType": [vehicletype],
           "Road_Type": [RoadType],
           "Speed_limit": [Speedlimit],
           "Light_Conditions": [Weather1],
           "Weather_Conditions": [Weather1],
           "Road_Surface_Conditions": [Weather1],
           "Urban_or_Rural_Area": [1],
           "City": [cityname],
           "Sex": [Sex1],
           "Age": [Age]
           }
    datapoint = py.DataFrame(obj)
    predict = model_clone.predict(datapoint)
    print(predict)
    predict = predictscore(predict)
    return predict

def predictscore(predict):
    predict = predict * 10

    return predict

if __name__ == '__main__':
    # Bind to PORT if defined, otherwise default to 5000.
    port = int(os.environ.get('PORT', 8000))
    app.run(debug=True,host='0.0.0.0', port=port)
