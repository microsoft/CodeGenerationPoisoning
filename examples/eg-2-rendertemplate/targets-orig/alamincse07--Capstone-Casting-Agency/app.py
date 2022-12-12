import os
from flask import Flask, jsonify, render_template, request, abort, url_for, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS

from authlib.integrations.flask_client import OAuth
from six.moves.urllib.parse import urlencode
from models import setup_db, db_drop_and_create_all, Actor, Movie

from auth import AuthError, requires_auth


# create and configure the app
app = Flask(__name__)
setup_db(app)
app.secret_key = os.getenv('SECRET')
CORS(app, resources={r"/api/*": {"origins": "*"}})

AUTH0_CLIENT_ID = os.getenv('Client_ID')
AUTH0_CLIENT_SECRET = os.getenv('Client_SECRET')
AUTH0_BASE_URL = os.getenv('AUTH0_BASE_URL')
AUTH0_AUDIENCE = os.getenv('API_AUDIENCE')
AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL')


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,true')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PATCH,DELETE,OPTIONS')
    return response


oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    api_base_url=AUTH0_BASE_URL,
    access_token_url=AUTH0_BASE_URL + '/oauth/token',
    authorize_url=AUTH0_BASE_URL + '/authorize',
    client_kwargs={
        'scope': 'openid',
    },
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return auth0.authorize_redirect(redirect_uri=AUTH0_CALLBACK_URL, audience=AUTH0_AUDIENCE, response_type='token')


@app.route('/logout')
def logout():
    params = {'returnTo': url_for('index', _external=True), 'client_id': AUTH0_CLIENT_ID}
    return redirect(auth0.api_base_url + '/v2/logout?' + urlencode(params))



@app.route('/movie-list')
@requires_auth('read:movies')
def show_movies(payload):
    try:
        movies = Movie.query.all()
        movies = [movie.format() for movie in movies]
    except Exception as e:
        movies = []
    return render_template('movies.html', movies=movies)


@app.route('/movies')
@requires_auth('read:movies')
def get_movies(payload):
    try:
        movies = Movie.query.all()
        movies = [movie.format() for movie in movies]
        return jsonify({
            'success': True,
            'movies': movies
        })
    except Exception as e:
        abort(422)


@app.route('/movies', methods=['POST'])
@requires_auth('write:movies')
def add_movie(payload):
    title = request.get_json().get('title')
    release_date = request.get_json().get('release_date')

    try:
        data = title and release_date
        if not data:
            abort(400)
    except (TypeError, KeyError):
        abort(400)

    try:
        Movie(title=title, release_date=release_date).insert()
        return jsonify({
            'success': True,
            'movie': title
        }), 201
    except Exception as e:
        print(e)
        abort(422)


@app.route('/movies/<int:movie_id>', methods=['PATCH'])
@requires_auth('update:movies')
def edit_movie(payload, movie_id):
    title = request.get_json().get('title')
    release_date = request.get_json().get('release_date')

    # make sure some data was passed
    try:
        data = title or release_date
        if not data:
            abort(400)
    except (TypeError, KeyError):
        abort(400)

    # make sure movie exists
    movie = Movie.query.filter_by(id=movie_id).first()
    if not movie:
        abort(404)

    # update
    try:
        if title:
            movie.title = title
        if release_date:
            movie.release_date = release_date
        movie.update()
        return jsonify({
            'success': True,
            'movie': movie.format()
        }), 200
    except Exception:
        abort(422)


@app.route('/movies/<int:movie_id>', methods=['DELETE'])
@requires_auth('delete:movies')
def delete_movie(payload, movie_id):
    movie = Movie.query.filter_by(id=movie_id).first()
    if not movie:
        abort(404)

    try:
        movie.delete()
        return jsonify({
            'success': True,
            'delete': movie_id
        }), 200
    except Exception:
        abort(422)


@app.route('/actors')
@requires_auth('read:actors')
def get_all_actors(payload):
    try:
        actors = Actor.query.all()
        actors = [actor.format() for actor in actors]
        return jsonify({
            'success': True,
            'actors': actors
        })
    except Exception:
        abort(422)


@app.route('/actor-list')
@requires_auth('read:actors')
def get_actors(payload):
    try:
        actors = Actor.query.all()
        actors = [actor.format() for actor in actors]
    except Exception:
        actors = []
    return render_template('actors.html', actors=actors)

@app.route('/actors', methods=['POST'])
@requires_auth('write:actors')
def add_actor(payload):
    
    try:
        name = request.get_json().get('name')
        gender = request.get_json().get('gender')
        data = name and gender
        if not data:
            abort(400)
    except Exception:
        abort(400)

    # try:
        
    new_actor = Actor(name=name, gender=gender)
    # new_actor
    new_actor.insert()
    actors = Actor.query.all()
    formatted_actors = [actor.format() for actor in actors]
    return jsonify({
        'success': True,
        'actor': formatted_actors
    }), 201
    # except Exception as e:
    #     print(e)
    #     abort(422)


@app.route('/actors/<int:actor_id>', methods=['PATCH'])
@requires_auth('update:actors')
def edit_actor(payload, actor_id):
    
    # make sure some data was passed
    try:
        name = request.get_json().get('name')
        gender = request.get_json().get('gender')

        data = name or gender
        if not data:
            abort(400)
    except Exception:
        abort(400)

    # make sure actor exists
    actor = Actor.query.filter_by(id=actor_id).first()
    if not actor:
        abort(404)

    # update
    try:
        if name:
            actor.name = name
        if gender:
            actor.gender = gender
        actor.update()
        return jsonify({
            'success': True,
            'actor': actor.format()
        }), 200
    except Exception:
        abort(422)


@app.route('/actors/<int:actor_id>', methods=['DELETE'])
@requires_auth('delete:actors')
def delete_actor(payload, actor_id):
    actor = Actor.query.filter_by(id=actor_id).first()
    if not actor:
        abort(404)

    try:
        actor.delete()
        return jsonify({
            'success': True,
            'delete': actor_id
        }), 200
    except Exception:
        abort(422)


#  Error Handling
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": 400,
        "message": "bad request"
    }), 400

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": "not found"
    }), 404


@app.errorhandler(409)
def duplicate(error):
    return jsonify({
        "success": False,
        "error": 409,
        "message": "duplicate"
    }), 409


@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False,
        "error": 422,
        "message": "unprocessable"
    }), 422


@app.errorhandler(AuthError)
def auth_error(error):
    return jsonify({
        "success": False,
        "error": error.status_code,
        "message": error.error
    }), error.status_code


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
