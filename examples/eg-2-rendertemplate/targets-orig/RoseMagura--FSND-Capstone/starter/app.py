import os
from flask import Flask, request, abort, jsonify, redirect, url_for, \
    render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from models import *
from auth import *

ITEMS_PER_PAGE = 10


def paginate_items(request, selection, type):
    page = request.args.get('page', 1, type=int)
    start = (page - 1) * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE

    items = [type.format() for type in selection]
    current_items = items[start: end]
    return current_items


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.config.from_object('config.TestConfig')
    database_name = 'casting'
    database_path = 'postgresql://{}:{}@{}/{}'.format(
                        'postgres', 1, 'localhost:5432', database_name)
    setup_db(app, database_path=database_path)

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET, POST, DELETE')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/movies')
    @requires_auth('get:movies')
    def get_movies(token):
        selection = Movie.query.order_by(Movie.id).all()
        current_movies = paginate_items(request, selection, Movie)

        if (len(current_movies) == 0):
            abort(404)

        return jsonify({
            'success': True,
            'movies': current_movies,
            'total_movies': len(selection),
             })

    @app.route('/movies', methods=['POST'])
    @requires_auth('post:movies')
    def create_movie(token):
        body = request.get_json()
        new_name = body.get('name', None)
        new_release = body.get('release_date', None)
        new_actors = body.get('actors', None)
        actor_list = []

        for actor in new_actors:
            new = Actor.query.filter(Actor.name == actor).first()
            if new is None:
                abort(404)
            actor_list.append(new)

        try:
            entry = Movie(name=new_name, release_date=new_release,
                          actors=actor_list)
            entry.insert()

            return jsonify({
                'success': True,
                'created': entry.id,
                'total_actors': len(Movie.query.all())
            })

        except Exception as ex:
            print(ex)
            abort(422)

    @app.route('/movies/<int:movie_id>', methods=['DELETE'])
    @requires_auth('delete:movie')
    def delete_movie(token, movie_id):
        try:
            # Later, add feature to warn user about deleting permanently
            movie = Movie.query.filter(Movie.id == movie_id).one_or_none()
            movie.actors = []
            db.session.commit()

            if movie is None:
                # print('error')
                abort(404)

            movie.delete()

            return jsonify({
                'success': True,
                'deleted': movie_id,
                'total_movies': len(Movie.query.all())
            })

        except Exception as ex:
            # print(ex)
            abort(422)

    @app.route('/movies/<int:movie_id>', methods=['PATCH'])
    @requires_auth('patch:movie')
    def edit_movie(token, movie_id):
        body = request.get_json()
        new_actors = body.get('actors')
        try:
            movie = Movie.query.filter(Movie.id == movie_id).one_or_none()
            if movie is None:
                abort(404)

            if 'name' in body:
                movie.name = body.get('name')
            if 'actors' in body:
                current_actors = []
            for instance in new_actors:
                a = Actor.query.filter(Actor.name == instance).first()
                current_actors.append(a)

            movie.actors = current_actors

            if 'release_date' in body:
                movie.release_date = int(body.get('release_date'))
            movie.update()

            return jsonify({
                            'success': True,
                            'edited': movie_id,
                            'total_movies': len(Movie.query.all())
            })

        except Exception as ex:
            print(ex)
            abort(422)

    @app.route('/actors')
    @requires_auth('get:actors')
    def get_actors(token):
        selection = Actor.query.order_by(Actor.id).all()
        current_actors = paginate_items(request, selection, Actor)

        if (len(current_actors) == 0):
            abort(404)

        return jsonify({
            'success': True,
            'actors': current_actors,
            'total_actors': len(selection),
            })

    @app.route('/actors', methods=['POST'])
    @requires_auth('post:actor')
    def create_actor(token):
        body = request.get_json()
        new_name = body.get('name', None)
        new_age = body.get('age', None)
        new_gender = body.get('gender', None)
        new_movies = body.get('movies', None)

        movie_list = []

        for movie in new_movies:
            new = Movie.query.filter(Movie.name == movie).one_or_none()
            if new is None:
                abort(404)
                movie_list.append(new)

        try:
            entry = Actor(name=new_name, age=new_age, gender=new_gender,
                          movies=movie_list)
            entry.insert()

            return jsonify({
                            'success': True,
                            'created': entry.id,
                            'total_actors': len(Actor.query.all())
            })

        except Exception as ex:
            print(ex)
            abort(422)

    @app.route('/actors/<int:actor_id>', methods=['DELETE'])
    @requires_auth('delete:actor')
    def delete_actor(token, actor_id):
        try:
            # Later, add feature to warn user about deleting permanently
            actor = Actor.query.get(actor_id)
            actor.movies = []
            db.session.commit()

            if actor is None:
                # print('error')
                abort(404)

            actor.delete()

            return jsonify({
                            'success': True,
                            'deleted': actor_id,
                            'total_actors': len(Actor.query.all())
            })

        except Exception as ex:
            # print(ex)
            abort(422)

    @app.route('/actors/<int:actor_id>', methods=['PATCH'])
    @requires_auth('patch:actor')
    def edit_actor(token, actor_id):
        body = request.get_json()
        try:
            actor = Actor.query.filter(Actor.id == actor_id).one_or_none()
            new_movies = body.get('movies')
            if actor is None:
                abort(404)

            if 'name' in body:
                actor.name = body.get('name', None)
            if 'movies' in body:
                current_movies = []
            for instance in new_movies:
                m = Movie.query.filter(Movie.name == instance).first()
                current_movies.append(m)

            actor.movie = current_movies
            if 'age' in body:
                actor.age = int(body.get('age'))
            actor.update()

            return jsonify({
                'success': True,
                'edited': actor_id,
                'total_actors': len(Actor.query.all())
                })

        except Exception as ex:
            # print(ex)
            abort(422)

    @app.errorhandler(AuthError)
    def auth_error(e):
        response = jsonify(e.error)
        response.status_code = e.status_code
        return response

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'success': False,
            'error': 400,
            'message': 'bad request'
        }), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            'success': False,
            'error': 401,
            'message': 'Unauthorized'
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            'success': False,
            'error': 403,
            'message': 'Forbidden'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 404,
            'message': 'resource not found'
        }), 404

    @app.errorhandler(405)
    def not_allowed(error):
        return jsonify({
            'success': False,
            'error': 405,
            'message': 'method not allowed'
        }), 405

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
            'success': False,
            'message': 'unprocessable'
        }), 422
    return app


APP = create_app()

if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=8080, debug=True)
