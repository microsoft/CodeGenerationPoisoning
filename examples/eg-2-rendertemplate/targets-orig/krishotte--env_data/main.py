import connexion
import json
from flask import Flask, render_template, jsonify
import db
from ini import Ini2


# app = Flask(__name__, template_folder="templates")
app = connexion.App(__name__, specification_dir='./')
app.add_api('swagger.yml')

default_config = {
    'token': '',
    'db_string': '',
}
loaded_config = Ini2().read('conf.json')
config = {**default_config, **loaded_config}


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/users', methods=['GET', 'POST'])
def users():
    if connexion.request.method == 'GET':
        return jsonify(db.read_users())  # json.dumps(db.read_users())

    if connexion.request.method == 'POST':
        # print(f'POST request headers: {connexion.request.headers}')
        token = connexion.request.headers.get("X-Auth-Token")
        data = json.loads(connexion.request.json)
        print(f'Token: {token}')
        print(f'JSON: {data}')

        if len(data["name"]) > 0:
            print('writing data to db')
            db.add_user(data['name'])
            return json.dumps({"result": True})  # render_template('home.html')

        else:
            print('not correct data')
            return json.dumps({'result': False})


@app.route('/envdata', methods=['GET', 'POST'])
def env_data_write():
    if connexion.request.method == 'POST':
        # print(f'POST request headers: {connexion.request.headers}')
        token = connexion.request.headers.get("X-Auth-Token")
        data = json.loads(connexion.request.json)
        print(f'Token: {token}')
        print(f'JSON: {data}')

        try:
            print('writing data to db')
            db.add_env_data(
                battery=data["battery"],
                temperature=data["temperature"],
                humidity=data["humidity"],
                pressure=data["pressure"]
            )
            return json.dumps({"result": True})  # render_template('home.html')

        except Exception:
            print('not correct data')
            return json.dumps({'result': False})

    if connexion.request.method == 'GET':
        return jsonify(db.env_data_get_all())


@app.route('/envdata-last', methods=['GET'])
def env_data_last():
    return jsonify(db.env_data_get_last())


@app.route('/envdata-stat', methods=['GET'])
def env_data_stat():
    return jsonify(db.env_data_stat())


if __name__ == '__main__':
    app.run(debug=True)
