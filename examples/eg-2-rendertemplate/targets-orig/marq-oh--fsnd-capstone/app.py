"""
Imports
"""

import os
import dateutil.parser

from flask import Flask, request, abort, jsonify, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import sessionmaker
from flask_cors import CORS

from models import setup_db, Movies, Actors, Assignments

from auth import AuthError, requires_auth

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)
    app.secret_key = os.getenv('SECRET')
    CORS(app, resources={r"/*": {"origins": "*"}})


    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,true')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PATCH,POST,DELETE,OPTIONS')
        return response

    """
    Root endpoint to tell user how / where to login
    """
    @app.route('/')
    def index():
        return render_template('login.html')

    """
    Logged-in endpoint
    """
    @app.route('/logged-in')
    def loggedin():
        return render_template('logged-in.html')

    """
    Movies endpoint
    """

    # Endpoint to display all movies
    @app.route('/movies', methods=['GET'])
    @requires_auth('get:movies')
    def get_movies(payload):
        try:
            # Get all movies
            movies = Movies.query.all()
            movies_list = [movie.format() for movie in movies]

            return jsonify({
                'success': True,
                'movies_list': movies_list
            }), 200
        except Exception:
            abort(422)

    # Endpoint to insert new movie
    @app.route('/movies', methods=['POST'])
    @requires_auth('post:movie')
    def insert_movie(payload):
        # Get data
        new_title = request.get_json()['title']
        new_release_date = request.get_json()['release_date']

        # check movie title for duplicate
        check_movie_title = Movies.query.filter(Movies.title.ilike('%{}%'.format(new_title))).all()
        if len(check_movie_title) > 0:
            raise Exception("Sorry, no duplicate movie titles allowed")
            abort(409)
        else:
            try:
                # Prepare INSERT transaction
                new_movie = Movies(title=new_title, release_date=new_release_date)
                new_movie.insert()

                # Display latest data
                selection = Movies.query.filter(Movies.title == new_title).first()
                return jsonify({
                  'id': selection.id,
                  'title': selection.title,
                  'release_date': selection.release_date,
                  'success': True
                }), 200

            except Exception:
                abort(422)

    # Endpoint to delete a movie
    @app.route('/movies/<int:id>', methods=['DELETE'])
    @requires_auth('delete:movie')
    def delete_movie(payload, id):
        try:
            # Query to get movie by ID
            del_movie = Movies.query.filter(Movies.id == id).one_or_none()

            if del_movie is None:
                abort(404)

            # Query to get movie's assignments for deletion
            del_movie_assignments_list = Assignments.query.filter(Assignments.movie_id == id).all()

            if len(del_movie_assignments_list) > 0:
                for movie in del_movie_assignments:
                    del_movie_assignment = Assignments.query.filter(Assignments.id == assignment.id).one_or_none()
                    del_movie_assignment.delete()
            # Execute delete transaction
            del_movie.delete()

            return jsonify({
                'deleted': id,
                'success': True
            }), 200

        except:
            abort(422)

    # Endpoint to update a movie
    @app.route('/movies/<int:id>', methods=['PATCH'])
    @requires_auth('patch:movie')
    def edit_movie(payload, id):
        try:
            # Query to get movie by ID
            edit_movie = Movies.query.filter(Movies.id == id).one_or_none()

            if edit_movie is None:
                abort(404)

            # Get data for editing
            edit_title = ""
            edit_release_date = ""

            if request.get_json().get('title'):
                edit_title = request.get_json()['title']

                # check  title for duplicate
                check_movie_title = Movies.query.filter(Movies.title.ilike('%{}%'.format(edit_title))).all()

                if len(check_movie_title) > 0:
                    raise Exception("Sorry, no duplicate movie titles allowed")
                    abort(409)

            if request.get_json().get('release_date'):
                edit_release_date = request.get_json()['release_date']

            # Make sure we only update where we have data
            if edit_title != "":
                edit_movie.title = edit_title
            if edit_release_date != "":
                edit_movie.release_date = edit_release_date

            edit_movie.update()

            return jsonify({
                'id': edit_movie.id,
                'title': edit_movie.title,
                'release_date': edit_movie.release_date,
                'success': True
            }), 200

        except:
            abort(422)

    """
    Actors endpoint
    """

    # Endpoint to display all actors
    @app.route('/actors', methods=['GET'])
    @requires_auth('get:actors')
    def get_actors(payload):
        try:
            # Get all actors
            actors = Actors.query.all()
            actors_list = [actor.format() for actor in actors]

            return jsonify({
            'success': True,
            'actors_list': actors_list
            }), 200
        except Exception:
            abort(422)

    # Endpoint to insert a new actor
    @app.route('/actors', methods=['POST'])
    @requires_auth('post:actor')
    def insert_actor(payload):
        try:
            # Get data
            new_name = request.get_json()['name']
            new_age = request.get_json()['age']
            new_gender = request.get_json()['gender']

            # Prepare INSERT transaction
            new_actor = Actors(name=new_name, age=new_age, gender=new_gender)
            new_actor.insert()

            # Display latest data
            selection = Actors.query.filter(Actors.name == new_name).first()
            return jsonify({
            'id': selection.id,
            'name': selection.name,
            'age': selection.age,
            'gender': selection.gender,
            'success': True
            }), 200

        except Exception:
            abort(422)

    # Endpoint to delete an actor
    @app.route('/actors/<int:id>', methods=['DELETE'])
    @requires_auth('delete:actor')
    def delete_actor(payload, id):
        try:
            # Query to get actor by ID
            del_actor = Actors.query.filter(Actors.id == id).one_or_none()

            if del_actor is None:
                abort(404)

            # Query to get actor's assignments for deletion
            del_actor_assignments = Assignments.query.filter(Assignments.actor_id == id).all()

            if len(del_actor_assignments) > 0:
                for assignment in del_actor_assignments:
                    del_assignment = Assignments.query.filter(Assignments.id == assignment.id).one_or_none()
                    del_assignment.delete()

            # Execute delete transaction
            del_actor.delete()

            return jsonify({
                'deleted': id,
                'success': True
            }), 200

        except:
            abort(422)

    # Endpoint to edit an actor
    @app.route('/actors/<int:id>', methods=['PATCH'])
    @requires_auth('patch:actor')
    def edit_actor(payload, id):
        try:
            # Query to get actor by ID
            edit_actor = Actors.query.filter(Actors.id == id).one_or_none()

            if edit_actor is None:
                abort(404)

            # Get data for editing
            edit_name = ""
            edit_age = ""
            edit_gender = ""

            if request.get_json().get('name'):
                edit_name = request.get_json()['name']

            if request.get_json().get('age'):
                edit_age = request.get_json()['age']

            if request.get_json().get('gender'):
                edit_gender = request.get_json()['gender']

            # Make sure we only update where we have data
            if edit_name != "":
                edit_actor.name = edit_name
            if edit_age != "":
                edit_actor.age = edit_age
            if edit_gender != "":
                edit_actor.gender = edit_gender

            edit_actor.update()

            return jsonify({
                'id': edit_actor.id,
                'name': edit_actor.name,
                'age': edit_actor.age,
                'gender': edit_actor.gender,
                'success': True
            }), 200

        except:
            abort(422)

    """
    Assignments endpoint - To assign actors to movies
    """

    # Endpoint to display all assignments
    @app.route('/assignments', methods=['GET'])
    @requires_auth('get:assignments')
    def get_assignments(payload):
        try:
            # Get all assignments
            assignments = Assignments.query.all()
            assignments_list = [assignment.format() for assignment in assignments]

            return jsonify({
                'success': True,
                'assignments_list': assignments_list
            }), 200
        except Exception:
            abort(422)

    # Endpoint to insert new assignment; Movie and Actor must exist
    @app.route('/assignments', methods=['POST'])
    @requires_auth('post:assignment')
    def create_assignment(payload):
        try:
            # Get data
            new_movie_id = request.get_json()['movie_id']
            new_actor_id = request.get_json()['actor_id']

            # check movie exists
            check_movie = Movies.query.get(new_movie_id)
            if not check_movie:
              raise Exception("Sorry, movie not available")
              abort(404)

            # check actor exists
            check_actor = Actors.query.get(new_actor_id)
            if not check_actor:
              raise Exception("Sorry, actor not available")
              abort(404)

            # Prepare INSERT transaction
            new_assignment = Assignments(movie_id=new_movie_id, actor_id=new_actor_id)
            new_assignment.insert()

            # Display latest data
            selection = Assignments.query.order_by(Assignments.id.desc()).first()

            return jsonify({
              'id': selection.id,
              'movie_id': selection.movie_id,
              'actor_id': selection.actor_id,
              'success': True
            }), 200

        except Exception:
            abort(422)

    # Endpoint to delete an assignment
    @app.route('/assignments/<int:id>', methods=['DELETE'])
    @requires_auth('delete:assignment')
    def delete_assignment(payload, id):
        try:
            # Query to get assignment by ID
            del_assignment = Assignments.query.filter(Assignments.id == id).one_or_none()

            if del_assignment is None:
                abort(404)

            # Execute delete transaction
            del_assignment.delete()

            return jsonify({
            'deleted': id,
            'success': True
            }), 200

        except:
            abort(422)

    """
    Error handling
    """

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
        "success": False,
        "error": 404,
        "message": "Resource not found"
        }), 404

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
        "success": False,
        "error": 422,
        "message": "Unprocessable"
        }), 422

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
        "success": False,
        "error": 400,
        "message": "Bad Request"
        }), 400

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
        "success": False,
        "error": 500,
        "message": "Internal Server Error"
        }), 500

    @app.errorhandler(405)
    def not_allowed(error):
        return jsonify({
        "success": False,
        "error": 405,
        "message": "Method Not Allowed"
        }), 405

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({
            "success": False,
            "error": 401,
            "message": "Unauthorized"
        }), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({
            "success": False,
            "error": 403,
            "message": "Forbidden"
        }), 403

    @app.errorhandler(AuthError)
    def auth_error(error):
        return jsonify({
            "success": False,
            "error": error.status_code,
            "message": error.error
        }), error.status_code

    return app

app = create_app()

if __name__ == '__main__':
    APP.run(host='0.0.0.0', port=8080, debug=True)