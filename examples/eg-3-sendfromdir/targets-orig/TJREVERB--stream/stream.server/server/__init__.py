import os
from flask_cors import CORS
from flask.json import jsonify
from flask.blueprints import Blueprint
from flask import Flask, send_from_directory

from . import routes
from . import settings

app = Flask(__name__, static_url_path=settings.STATIC_ROOT)
CORS(app)
app.debug = settings.DEBUG


if not os.path.exists(settings.IMAGES_DIR):
    os.mkdir(settings.IMAGES_DIR)


for blueprint in vars(routes).values():
    if isinstance(blueprint, Blueprint):
        app.register_blueprint(blueprint, url_prefix=settings.APPLICATION_ROOT)


@app.route('/static/js/<path:path>')
def send_js(path):
    return send_from_directory(os.path.abspath(os.path.join(settings.STATIC_ROOT, "js")), path)


@app.route('/static/css/<path:path>')
def send_css(path):
    return send_from_directory(os.path.abspath(os.path.join(settings.STATIC_ROOT, "css")), path)


@app.route('/static/pictures/<path:path>')
def send_pic(path):
    return send_from_directory(settings.IMAGES_DIR, path)


@app.route('/')
def index():
    return app.send_static_file('index.html')


if __name__ == "__main__":
    app.run(host=settings.HOST, port=settings.PORT)
