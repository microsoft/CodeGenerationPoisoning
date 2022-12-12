import os

from flask import Flask, redirect, url_for, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


class Cars(db.Model):
    """Cars model for storing car data"""
    __tablename__ = "cars"

    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(40))
    brand = db.Column(db.String(40))
    mileage = db.Column(db.Float)
    mpg = db.Column(db.Float)

    def __repr__(self):
        return "<Car id:{0!r} name: {1!r} brand:{2!r}>".format(
            self.id, self.name, self.brand
        )


def partition(types, carlist, l, h):
    pivot = carlist[h][types]
    i = l - 1

    for j in range(l,h):
        if carlist[j][types] < pivot:
            i += 1
            carlist[i],carlist[j] =carlist[j],carlist[i]
    carlist[i+1], carlist[h] = carlist[h], carlist[i+1]
    return i+1


def qsort(types,carlist, l, h):
    if l < h:
        part = partition(types, carlist, l, h)
        qsort(types, carlist, l, part-1)
        qsort(types, carlist, part+1, h)


def new_car(data):
    db.session.add(
        Cars(
            name=data['name'],
            brand=data['brand'],
            mileage=data['mileage'],
            mpg=data['mpg']
        )
    )
    db.session.commit()
    response_object = {
        'status': 'success',
        'message': 'Successfully added entry'
    }

    return response_object, 201


def get_all_cars():
    # returns all car objects in list
    # must be cars in database
    data = Cars.query.all()
    index = 0
    all_cars = {}
    if data:
        for car in data:
            all_cars.update({
                index: {
                    'Name': car.name,
                    'Brand': car.brand,
                    'mileage': car.mileage,
                    'mpg': car.mpg
                }
            })
            index = index + 1
        return(all_cars)

@app.route('/')
def my_form():
    return render_template('home.html')


@app.route('/', methods=['POST'])
def login():
    data = request.form.to_dict()
    return(new_car(data))

@app.route('/front')
def front():
    return render_template('front.html')


@app.route('/print')
def printing():
    carlist = get_all_cars()
    return render_template('print.html', carlist=carlist)


@app.route('/print', methods=['POST'])
def sorting():
    carlist = get_all_cars()
    qsort(request.form['type'], carlist, 0, len(carlist)-1)
    return render_template("print.html", carlist=carlist)


@app.route('/search')
def search():
    carlist = get_all_cars()
    return render_template('search.html', carlist=carlist)


@app.route('/search', methods=['POST'])
def find():
    carlist = get_all_cars()
    type = request.form['type']
    searchlist = []
    print(searchlist)
    searched = request.form['searched']
    if searched == "":
        searchlist = "Please type in something to search"
        return render_template('search.html', Searched=searchlist)
    if type == "mpg" or type == "mileage":
        if searched.isdigit():
            rangelow = round(float(searched) * 0.95)
            rangehigh = round(float(searched) *1.05)
            for i in range(len(carlist)):
                if rangehigh > carlist[i][type] > rangelow:
                    searchlist.append(carlist[i])
        else:
            searchlist = "Please type in a number for MPG or Mileage searches"
    if type == "Brand":
        for i in range(len(carlist)):
            if carlist[i][type] == searched:
                searchlist.append(carlist[i])
    if searched == "":
        searchlist = "Please type in something to search"
    elif not searchlist:
        searchlist = "Sorry no results"
    return render_template('search.html', Searched=searchlist)



# @manager.command
# def run():
#     app.run()


# if __name__ == '__main__':
#     manager.run()

# if __name__ == "__main__":
#     app.run()

# Cache Busting
# For some reason, browsers like to cache css files
# These two methods reset the cache.
# http://flask.pocoo.org/snippets/40/

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)
