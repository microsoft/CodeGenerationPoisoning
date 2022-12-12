from flask import Flask, request, jsonify
from flask_restful import Resource, Api, reqparse
from flask_sqlalchemy import SQLAlchemy
import yaml
import platform
import socket
import requests
from decimal import Decimal

application = app = Flask(__name__)
db_config = yaml.load(open('db.yaml'), Loader=yaml.FullLoader)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://'+db_config['mysql_user']+':'+db_config['mysql_password']+'@'+db_config['mysql_host']+'/'+db_config['mysql_database']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


api = Api(app)
db = SQLAlchemy(app)

class Dna(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    sequence = db.Column(db.Text, primary_key = False, nullable=False)
    ismutant = db.Column(db.Integer, primary_key = False, nullable=False)

    def __repr__(self):
        return '<id %r>' % self.id

@app.route('/')
def hello_world():
    title = 'Hello, World! this is some service info:'
    new_line = '<br>'
    sql_hostname = '' #'Sql Hostname: ' + str(db_config['mysql_host'])
    platform_info = 'Platform Info: ' + platform.platform()
    total_dna_sequences = 'Total Database Dna Saved: ' + str(Dna.query.count())

    return new_line.join([title, sql_hostname, platform_info, total_dna_sequences])

class Stats(Resource):
    def get(self): 
        mutants_count = 0
        humans_count = 0

        mutants = Dna.query.with_entities(Dna.ismutant, db.func.count(Dna.ismutant)).filter(Dna.ismutant == 1).all()
        if len(mutants) > 0:
            mutants_count = mutants[0][1]

        humans = Dna.query.with_entities(Dna.ismutant, db.func.count(Dna.ismutant)).filter(Dna.ismutant == 0).all()
        if len(humans) > 0:
            humans_count = humans[0][1]
        
        try:
            ratio = float(mutants_count/humans_count)
        except:
            ratio = mutants_count
        
        round_ratio = round(ratio,1)
        return {'count_mutant_dna':mutants_count, 'count_human_dna':humans_count, 'ratio':round_ratio} , 200

class Dummy(Resource):
    def get(self):
        return {'message': 'ok'}, 200

api.add_resource(Stats, '/stats')
api.add_resource(Dummy, '/dummy')



