from flask import Flask, render_template, request
import data

app = Flask(__name__)

ctr = -1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/choose_state')
def choose_state():
    states_left,states_right = data.get_states()
    return render_template('choose_state.html', states_left=states_left, states_right=states_right,  terminal=False)

@app.route('/state/<state>')
def choose_airport(state):
    airports = data.get_airports(state.replace(u'\xa0', u'-'))
    return render_template('choose_airport.html', state=state, airports=airports, terminal=False)

@app.route('/airport1/<airport1>/choose_state_2')
def choose_state_2(airport1):
    states_left,states_right = data.get_states()
    return render_template('choose_state.html', states_left=states_left, states_right=states_right, terminal=True, airport1=airport1)

@app.route('/airport1/<airport1>/state_2/<state>')
def choose_airport_2(airport1,state):
    airports = data.get_airports(state.replace(u'\xa0', u'-'))
    return render_template('choose_airport.html', state=state, airports=airports,airport1=airport1,terminal=True)

@app.route('/state/<state>/map')
def state_airports_map(state):
    return data.plot_state_airports(state.replace(u'\xa0', u'-'))

@app.route('/airport/<airport>')
def airport_map(airport):
    map = data.plot_airport(airport)
    return map

@app.route('/airport1/<airport1>/airport2/<airport2>/month/<month>/price')
def price_trend(airport1,airport2,month):
    return data.plot_price_trending(airport1,airport2,month)

@app.route('/airport1/<airport1>/airport2/<airport2>/month/<month>/popularity')
def popularity_trend(airport1,airport2,month):
    return data.plot_popularity_trending(airport1,airport2,month)

@app.route('/airport1/<airport1>/airport2/<airport2>/',methods=['GET', 'POST'])
def search_flight(airport1,airport2):
    name1 = data.query("SELECT name FROM Airports WHERE IATA='{}'".format(airport1))[0][0]
    name2 = data.query("SELECT name FROM Airports WHERE IATA='{}'".format(airport2))[0][0]
    month = ''
    order = ''
    res = []
    no_result = False
    if request.method == 'POST':
        month = request.form['month']
        order = request.form['order'] 
        res = data.get_data(airport1,airport2,request.form['month'],request.form['order'])
        if not res: no_result = True

    #airports = data.get_airports(state.replace(u'\xa0', u' '))
    return render_template('search_flight.html', airport1=airport1 ,airport2=airport2, name1=name1, name2=name2,\
         month=month, order=order, data=res, no_result=no_result)

if __name__ == '__main__':  
    print('starting Flask app', app.name)  
    app.run(debug=True)