import sys
from flask import Flask, request, Response, jsonify
import airplay
import yaml
from jsonschema import validate, ValidationError
import os
from logging.config import dictConfig

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stdout',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})


app = Flask(__name__)

conf_file = 'base_config.yaml'

#cerca in config:
if os.path.isfile('/config/' + conf_file):
    app.logger.info('using config from config folder')
    with open('/config/' + conf_file, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
#cerca nella root:
if os.path.isfile(conf_file):
    app.logger.info('using config from root folder')
    with open(conf_file, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
#override with env:
app.logger.info(os.environ)
#config['base_key'] = os.environ.get("AIRTABLE_BASE_KEY", config["base_key"])
if 'AIRTABLE_BASE_KEY' in os.environ: config['base_key'] = os.environ['AIRTABLE_BASE_KEY']; app.logger.info('overriding basekey with env variables')
if 'AIRTABLE_API_KEY' in os.environ: config['api_key'] = os.environ['AIRTABLE_API_KEY'];app.logger.info('overriding apikey with env variables')

if not 'base_key' in config and 'api_key' in config and 'schema' in config:
    app.logger.warnining('abort due missing config')
    sys.exit(1)


app.logger.info(config)
@app.route('/api/<table>', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def methods(table):
    tbl = airplay.Table(config['base_key'], table, config['api_key'])

    app.logger.info(tbl)
    app.logger.info(config['base_key'])
    app.logger.info(table)
    app.logger.info(config['api_key'])

    ##########################################################################################
    # create formulas string with args
    formulas = []
    for arg in request.args:
        if request.args.get(arg).isnumeric():
            formulas.append(f'''{arg}={request.args.get(arg)}''')
        else:
            formulas.append(f'''FIND("{request.args.get(arg)}", {arg})''')
    filter_by_formula = str("AND({})".format(",".join(formulas)))
    ##########################################################################################
    if request.method == 'GET':
        app.logger.info('get request')
        if len(request.args) > 0:
            return jsonify(tbl.items(filters=filter_by_formula))
        else:
            app.logger.info(tbl.items())
            return jsonify(tbl.items())
    if request.method == 'POST':
        data = request.get_json()
        app.logger.info('post request')
        app.logger.info(data)
        if validate_schema(table, data) is not None:
            result = validate_schema(table, data)
            app.logger.warning(Response(result, 400))
            return Response(result, status=400)
        else:
            return jsonify(tbl.insert(**data))
    if request.method == 'PATCH':
        app.logger.info('patch request')
        data = request.get_json()
        if validate_schema(table, data) is not None:
            result = validate_schema(table, data)
            return Response(result, status=400)
        else:
            target_id = data['id']
            data.pop('id')
            return jsonify(tbl.modify(target_id, **data))
    if request.method == 'DELETE':
        data = request.get_json()
        if validate_schema(table, data) is not None:
            result = validate_schema(table, data)
            return Response(result, status=400)
        else:
            target_id = data['id']
            return jsonify(tbl.delete(target_id))


@app.route('/api/<table>/<target_id>', methods=['GET', 'PATCH', 'DELETE'])
def get_id(table, target_id):
    tbl = airplay.Table(config['base_key'], table, config['api_key'])
    if request.method == 'GET':
        return jsonify(tbl.get_id(target_id))
    if request.method == 'PATCH':
        data = request.get_json()
        return jsonify(tbl.modify(target_id, **data))
    if request.method == 'DELETE':
        return jsonify(tbl.delete(target_id))


def validate_schema(table, data=""):
    app.logger.info('validating schema:')
    try:
        schema_ = config['schema']
        validate(data, schema_[table])
        return None
    except ValidationError as ex:
        app.logger.info('validation error!')
        app.logger.info(ex.args[0])
        return ex.message


if __name__ == '__main__':
    app.run()

# curl -X GET  localhost:5000/api?table=Albums
# curl -X POST -H "Content-Type: application/json" -d "{\"Track\": \"sound\"}" localhost:5000/api/Tracks
# curl -X PATCH -H "Content-Type: application/json" -d "{\"id\":\"reclfUY48qDMTnmXl\",\"Artist\": \"tommy\"}" localhost:5000/api/Albums
# localhost:5000/api?name=Albums
# curl http://localhost:5000/api/Albums?Artist=Daft
# curl -X PATCH -H "Content-Type: application/json" -d "{\"Profile\": \"a good boy\"}" http://localhost:5000/api/Artists/rec5V36WuIX4XsDUe

