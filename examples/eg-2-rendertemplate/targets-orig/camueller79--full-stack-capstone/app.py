import os
from flask import Flask, request, abort, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from models import db_init_records, setup_db, Album, Band, db
from auth import AuthError, requires_auth


def create_app(test_config=None):
    app = Flask(__name__)
    CORS(app, resources={r"/api/": {"origins": "*"}})
    setup_db(app)

    @app.after_request
    def after_request(response):
        response.headers.add(
            'Access-Control-Allow-Headers',
            'Content-Type, Authorization, true')
        response.headers.add(
            'Access-Control-Allow-Methods',
            'GET, PATCH, POST, DELETE, OPTIONS')
        return response

    @app.route('/')
    def index():
        return render_template('home.html')

    @app.route('/bands')
    @requires_auth('get:bands')
    def get_bands(payload):
        # GET all artists
        bands = Band.query.all()

        if len(bands) == 0:
            abort(404)

        bands = [band.format() for band in bands]
        return jsonify(bands)

    @app.route('/albums')
    @requires_auth('get:albums')
    def get_albums(payload):
        # GET all albums
        albums = Album.query.all()

        if len(albums) == 0:
            abort(404)

        albums = [album.format() for album in albums]
        return jsonify(albums)

    @app.route('/bands', methods=['POST'])
    @requires_auth('post:band')
    def post_newbands(payload):
        # takes a JSON object with new artist to add to database
        body = request.get_json()

        name = body.get('name', None)
        city = body.get('city', None)
        state = body.get('state', None)

        if name is None:
            abort(400)
        if city is None:
            abort(400)
        if state is None:
            abort(400)

        band = Band(name=name, city=city, state=state)
        band.insert()
        new_band = Band.query.get(band.id).format()

        return jsonify({
            'success': True,
            'band': new_band
        })

    @app.route('/albums', methods=['POST'])
    @requires_auth('post:album')
    def post_new_album(payload):
        # takes a JSON object with new album to add to database
        body = request.get_json()

        title = body.get('title', None)
        band_id = body.get('band_id', None)

        if title is None:
            abort(400)
        if band_id is None:
            abort(400)

        album = Album(title=title, band_id=band_id)
        album.insert()
        new_album = Album.query.get(album.id).format()

        return jsonify({
            'success': True,
            'album': new_album
        })

    @app.route('/bands/<int:band_id>', methods=['DELETE'])
    @requires_auth('delete:band')
    def delete_band(payload, band_id):
        # takes an artist_id and deletes the record
        band = Band.query.filter(Band.id == band_id).one_or_none()
        if band is None:
            abort(404)
        band.delete()
        return jsonify({
            'success': True,
            'band': band_id
        })

    @app.route('/albums/<int:album_id>', methods=['DELETE'])
    @requires_auth('delete:album')
    def delete_album(payload, album_id):
        # takes an album id and deletes the record
        album = Album.query.filter(Album.id == album_id).one_or_none()
        if album is None:
            abort(404)

        album.delete()
        return jsonify({
            'success': True,
            'album': album_id
        })

    @app.route('/bands/<int:band_id>', methods=['PATCH'])
    @requires_auth('patch:band')
    def patch_band(payload, band_id):
        # takes an artist id via route and json object to patch record
        band = Band.query.filter(Band.id == band_id).one_or_none()
        if band is None:
            abort(404)

        body = request.get_json()
        if body is None:
            abort(400)

        name = body.get('name', None)
        city = body.get('city', None)
        state = body.get('state', None)

        if name is None:
            abort(400)
        if city is None:
            abort(400)
        if state is None:
            abort(400)\

        band.name = name
        band.city = city
        band.state = state

        band.update()
        return jsonify({
            'success': True,
            'band': band.format()
        })

    @app.route('/albums/<int:album_id>', methods=['PATCH'])
    @requires_auth('patch:album')
    def patch_album(payload, album_id):
        # takes an album id via route and json ojbect to patch record
        album = Album.query.filter(Album.id == album_id).one_or_none()
        if album is None:
            abort(404)
        body = request.get_json()
        if body is None:
            abort(400)
        title = body.get('title', None)
        band_id = body.get('band_id', None)
        if title is None:
            abort(400)
        if band_id is None:
            abort(400)

        album.title = title
        album.band_id = band_id
        album.update()
        return jsonify({
            'success': True,
            'album': album.format()
        })

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 404,
            'message': 'Resource not found'
        }), 404

    @app.errorhandler(400)
    def unprocessable(error):
        return jsonify({
            'success': False,
            'error': 422,
            'message': 'Unprocesssable request'
        }), 400

    @app.errorhandler(AuthError)
    def auth_error(auth_error):
        return jsonify({
            "success": False,
            "error": auth_error.status_code,
            "message": auth_error.error['description']
        }), auth_error.status_code

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
