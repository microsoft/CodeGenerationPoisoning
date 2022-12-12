#!/usr/bin/python
# -*- coding: utf-8 -*-

from os import environ
from flask import Flask, request, abort, jsonify, render_template, \
    redirect, session, make_response, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random
import json
from flask_migrate import Migrate
from models import setup_db, Movie, Actor
from auth import AuthError, requires_auth, verify_decode_jwt, \
    get_access_token, get_user_id, get_MGMT_API_ACCESS_TOKEN
import urllib.request as uri
import yaml
from forms import ActorForm, MovieForm, ActorForm2, MovieForm2





def create_app(test_config=None):

    # create and configure the app

    app = Flask(__name__)
    setup_db(app)
    CORS(app)
    
    # These are your environment variables
    # you should implement them from the terminal.
    # ex: export AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN
    # or  set AUTH0_DOMAIN=YOUR_AUTH0_DOMAIN

    app.config['SECRET_KEY'] = environ.get('SECRET_KEY')
    AUTH0_DOMAIN = environ.get('AUTH0_DOMAIN')
    

    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Headers',
                             'Content-Type,Authorization,true')
        response.headers.add('Access-Control-Allow-Methods',
                             'GET,PUT,POST,DELETE,OPTIONS')
        return response

    @app.route('/')
    def index():

        return render_template('register.html')

    @app.route('/login_assistant')
    def login():

        code_auth = request.args.get('code')

        token = get_access_token(code_auth)

        user_id = get_user_id(token)

        api_token = get_MGMT_API_ACCESS_TOKEN()

        payload = verify_decode_jwt(token)

        if 'permissions' not in payload:
            abort(400)

        permissions = payload.get('permissions')

        if len(permissions) == 0:

            url3 = f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles'

            headers = {'content-type': 'application/json',
                       'authorization': 'Bearer ' + api_token,
                       'cache-control': 'no-cache'}

            data = '{ "roles": [ " rol_ZNrwNNQqwSOmhpov " ] }'
            data = data.encode('ascii')
            req3 = uri.Request(url3, data, headers)

            try:

                uri.urlopen(req3)
            except uri.URLError as e:

                print ('URL Error: ', e.reason)
            except uri.HTTPError as e:

                print ('HTTP Error code: ', e.code)

            session['role'] = 'Casting Assistant'
            return redirect(url_for('home'))

        if 'delete:movie' in permissions:
            session['role'] = 'producer'
        elif 'delete:movie' not in permissions and 'delete:actor' \
            in permissions:
            session['role'] = 'director'
        elif 'delete:actor' not in permissions:
            session['role'] = 'Casting Assistant'

        return redirect(url_for('home'))

    @app.route('/login-director')
    def login_as_director():
        code_auth = request.args.get('code')

        token = get_access_token(code_auth)

        user_id = get_user_id(token)

        api_token = get_MGMT_API_ACCESS_TOKEN()

        payload = verify_decode_jwt(token)
        if 'permissions' not in payload:
            abort(400)

        permissions = payload.get('permissions')

        if len(permissions) == 0:

            url3 = f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles'

            headers = {'content-type': 'application/json',
                       'authorization': 'Bearer ' + api_token,
                       'cache-control': 'no-cache'}

            data = '{ "roles": [ " rol_HlzotlBP5vkSKGL9 " ] }'
            data = data.encode('ascii')
            req3 = uri.Request(url3, data, headers)

            try:

                uri.urlopen(req3)
            except uri.URLError as e:

                print ('URL Error: ', e.reason)
            except uri.HTTPError as e:

                print ('HTTP Error code: ', e.code)
            else:

                session['role'] = 'director'
                return redirect(url_for('home'))

        if 'delete:movie' in permissions:
            session['role'] = 'producer'
        elif 'delete:movie' not in permissions and 'delete:actor' \
            in permissions:
            session['role'] = 'director'
        elif 'delete:actor' not in permissions:
            session['role'] = 'Casting Assistant'

        return redirect(url_for('home'))

    @app.route('/login-producer')
    def login_as_producer():

        code_auth = request.args.get('code')

        token = get_access_token(code_auth)

        user_id = get_user_id(token)

        api_token = get_MGMT_API_ACCESS_TOKEN()

        payload = verify_decode_jwt(token)

        if 'permissions' not in payload:
            abort(400)

        permissions = payload.get('permissions')

        if len(permissions) == 0:

            url3 = f'https://{AUTH0_DOMAIN}/api/v2/users/{user_id}/roles'

            headers = {'content-type': 'application/json',
                       'authorization': 'Bearer ' + api_token,
                       'cache-control': 'no-cache'}

            data = '{ "roles": [ " rol_t2ets4eZtnaqf6Xo " ] }'
            data = data.encode('ascii')
            req3 = uri.Request(url3, data, headers)

            try:

                uri.urlopen(req3)
            except uri.URLError as e:

                print ('URL Error: ', e.reason)
            except uri.HTTPError as e:

                print ('HTTP Error code: ', e.code)
            else:

                session['role'] = 'producer'
                return redirect(url_for('home'))

        if 'delete:movie' in permissions:
            session['role'] = 'producer'
        elif 'delete:movie' not in permissions and 'delete:actor' \
            in permissions:
            session['role'] = 'director'
        elif 'delete:actor' not in permissions:
            session['role'] = 'Casting Assistant'

        return redirect(url_for('home'))

    @app.route('/logout')
    def logout():

        session.clear()

        return redirect(url_for('index'))

    @app.route('/home')
    @requires_auth('get:actors')
    def home(jwt):

        return render_template('home.html', data=session['user_info'],
                               role=session['role'])

    @app.route('/movies', methods=['GET'])
    @requires_auth('get:movies')
    def get_movies(jwt):
        try:
            movies = Movie.query.all()

            if movies == None or len(movies) == 0:
                flash('There is no Movies added yet!', 'info')
                return render_template('movies.html',
                        data=session['user_info'], role=session['role'])

            current_movies = [movie.format() for movie in movies]

            return render_template('movies.html',
                                   movies=current_movies,
                                   data=session['user_info'],
                                   role=session['role'])
        except:
            abort(500)

    @app.route('/movies/<int:movie_id>', methods=['DELETE'])
    @requires_auth('delete:movie')
    def delete_movie(jwt, movie_id):

        movie = Movie.query.filter(Movie.id == movie_id).one_or_none()
        if movie == None or len(movie) == 0:
            abort(404)
        try:
            movie.delete()
            return jsonify({'success': True})
        except:
            abort(422)

    @app.route('/movies/create')
    def create_movie_form():
        try:
            form = MovieForm()
            return render_template('new_movie.html', form=form,
                                   data=session['user_info'])
        except:
            abort(500)

    @app.route('/movies/create', methods=['POST'])
    @requires_auth('post:movie')
    def create_movie(jwt):

        title = request.form.get('title')
        release_date = request.form.get('release_date')
        image_url = request.form.get('image_url')

        try:
            new_movie = Movie(title=title, release_date=release_date,
                              image_url=image_url)
            new_movie.insert()

            flash(f'{title} has been created', 'success')
            return redirect(url_for('get_movies'))
        except:

            flash(f'{title} has not been created successfully ! check your inputs formats (for example).'
                  , 'danger')
            return redirect(url_for('get_movies'))

    @app.route('/movies/<int:movie_id>')
    @requires_auth('patch:movie')
    def update_movie_form(jwt, movie_id):

        movie = Movie.query.filter(Movie.id == movie_id).one_or_none()
        if movie == None:
            abort(404)
        try:

            form = MovieForm2()
            return render_template('edit_movie.html',
                                   data=session['user_info'],
                                   movie=movie, form=form)
        except:
            abort(500)

    @app.route('/movies/<int:movie_id>', methods=['POST'])
    @requires_auth('patch:movie')
    def update_movie(jwt, movie_id):

        movie = Movie.query.filter(Movie.id == movie_id).one_or_none()
        if movie == None:
            abort(404)

        body = request.form
        if len(body) == 0 or body == None:
            abort(400)
        new_title = body.get('title')
        new_release_date = body.get('release_date')
        new_image_url = body.get('image_url')

        if len(new_title) == 0:
            new_title = movie.title
        if len(new_release_date) == 0:
            new_release_date = movie.release_date
        if len(new_image_url) == 0:
            new_image_url = movie.image_url

        movie.title = new_title
        movie.release_date = new_release_date
        movie.image_url = new_image_url

        try:
            movie.update()
            flash(f'Changes on {new_title} have been submited !',
                  'success')
            return redirect(url_for('get_movies'))
        except:

            flash(f'New changes on {new_title} have not been submited !'
                  , 'danger')
            return redirect(url_for('get_movies'))

    @app.route('/movies/<int:movie_id>/actors')
    @requires_auth('get:actors')
    def get_actors_for_movie(jwt, movie_id):

        actors = Actor.query.filter(Actor.movie_id == movie_id).all()

        if len(actors) == 0:

            flash('This movie dose not have any Actors yet!', 'info')
            return render_template('crew.html', data=session['user_info'
                                   ])

        formatted_actors = [actor.format() for actor in actors]
        movie = Movie.query.get(movie_id)

        return render_template('crew.html', data=session['user_info'],
                               actors=formatted_actors, movie=movie,
                               role=session['role'])

    @app.route('/movies/<int:movie_id>/actors/<int:actor_id>')
    def update_specfic_actor_form(actor_id, movie_id):

        form = ActorForm2()
        actor = Actor.query.filter(Actor.id == actor_id).one_or_none()
        if actor == None or len(actor) == 0:
            abort(404)

        movie = Movie.query.filter(Movie.id == movie_id).one_or_none()
        if movie == None or len(movie) == 0:
            abort(404)

        try:
            return render_template('edit_crew.html',
                                   data=session['user_info'],
                                   actor=actor, form=form)
        except:
            abort(500)

    @app.route('/movies/<int:movie_id>/actors/<int:actor_id>',
               methods=['POST'])
    @requires_auth('patch:actor')
    def update_specfic_actor(movie_id, actor_id):

        body = request.form

        if body == None or len(body) == 0:
            flash('No changes had been submitted', 'danger')
            return redirect(url_for('get_actors_for_movie',
                            movie_id=movie_id))

        new_name = body.get('name')
        new_age = body.get('age')
        new_gender = body.get('gender')
        new_image_url = body.get('image_url')

        try:
            actor = Actor.query.filter(Actor.id
                    == actor_id).one_or_none()

            if len(new_age) == 0:
                new_age = actor.age
            if len(new_name) == 0:
                new_name = actor.name
            if new_gender == None or len(new_gender) == 0:
                new_gender = actor.gender
            if len(new_image_url) == 0:
                new_image_url = actor.image_url

            actor.name = new_name
            actor.age = new_age
            actor.gender = new_gender
            actor.image_url = new_image_url
            actor.update()
            flash('New changes have been submited', 'success')
            return redirect(url_for('get_actors_for_movie',
                            movie_id=movie_id))
        except:
            flash('New changes have not been submited', 'danger')
            return redirect(url_for('get_actors_for_movie',
                            movie_id=movie_id))

    @app.route('/actors', methods=['GET'])
    @requires_auth('get:actors')
    def get_actors(jwt):

        try:

            actors = Actor.query.all()

            if actors == None or len(actors) == 0:
                flash('There is no Actors added yet!', 'info')
                return render_template('actors.html',
                        data=session['user_info'], role=session['role'])

            current_actors = [actor.format() for actor in actors]

            return render_template('actors.html',
                                   data=session['user_info'],
                                   actors=current_actors,
                                   role=session['role'])
        except:
            abort(500)

    @app.route('/actors/<int:actor_id>', methods=['DELETE'])
    @requires_auth('delete:actor')
    def delete_actor(jwt, actor_id):

        actor = Actor.query.filter(Actor.id == actor_id).one_or_none()
        if actor == None:
            abort(404)
        try:
            actor.delete()
            return jsonify({'success': True})
        except:
            abort(422)

    @app.route('/actors/create')
    def create_actor_form():
        try:
            form = ActorForm()
            return render_template('new_actor.html', form=form,
                                   data=session['user_info'])
        except:
            abort(500)

    @app.route('/actors/create', methods=['POST'])
    @requires_auth('post:actor')
    def create_actor(jwt):

        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        image_url = request.form.get('image_url')
        movie = request.form.get('movie')
        age = int(age)
        movie = int(movie)
        chosen_movie = Movie.query.filter(Movie.id
                == movie).one_or_none()

        if chosen_movie == None:
            flash(f'{name} not succesfily added check Movie_id',
                  'danger')
            return redirect(url_for('get_actors'))
        try:
            new_actor = Actor(name=name, age=age, gender=gender,
                              image_url=image_url, movie_id=movie)
            new_actor.insert()
            flash(f'{name} has been added', 'success')
            return redirect(url_for('get_actors'))
        except:
            flash(f'{name} has not been added ! check your inputs formats(for example)'
                  , 'danger')
            return redirect(url_for('get_actors'))

    @app.route('/actors/<int:actor_id>', methods=['GET'])
    @requires_auth('get:actors')
    def get_spec_actor(jwt, actor_id):

        actor = Actor.query.filter(Actor.id == actor_id).one_or_none()
        if actor == None or len(actor) == 0:
            abort(404)

        formatted_actor = actor.format()
        try:
            form = ActorForm2()
            return render_template('edit_actor.html',
                                   actor=formatted_actor,
                                   data=session['user_info'], form=form)
        except:
            abort(500)

    @app.route('/actors/<int:actor_id>', methods=['POST'])
    @requires_auth('post:actor')
    def update_actor(jwt, actor_id):

        actor = Actor.query.filter(Actor.id == actor_id).one_or_none()
        if actor == None or len(actor) == 0:
            abort(404)

        body = request.form
        if len(body) == 0 or body == None:
            abort(400)

        new_name = body.get('name')
        new_gender = body.get('gender')
        new_age = body.get('age')
        new_image_url = body.get('image_url')
        new_movie = body.get('movie')
        new_movie = int(new_movie)

        chosen_movie = Movie.query.filter(Movie.id
                == new_movie).one_or_none()
        if chosen_movie == None:
            flash('New changes have not been  Submited check the movie id'
                  , 'danger')
            return redirect(url_for('get_actors'))

        if len(new_age) == 0:
            new_age = actor.age
        if len(new_name) == 0:
            new_name = actor.name
        if new_gender == None or len(new_gender) == 0:
            new_gender = actor.gender
        if len(new_image_url) == 0:
            new_image_url = actor.image_url
        if len(new_movie) == 0:
            new_movie = actor.movie_id

        actor.name = new_name
        actor.age = new_age
        actor.gender = new_gender
        actor.image_url = new_image_url
        actor.movie_id = chosen_movie.id

        try:

            actor.update()

            flash('New changes had been Submited', 'success')
            return redirect(url_for('get_actors'))
        except:
            flash('New changes had not been Submited', 'danger')
            return redirect(url_for('get_actors'))

    @app.errorhandler(400)
    def bad_req(error):
        return (jsonify({'success': False, 'message': 'bad request',
                'error': 400}), 400)

    @app.errorhandler(404)
    def not_fond(error):
        return (render_template('404.html', data=session['user_info']),
                404)

    @app.errorhandler(500)
    def server_error(error):
        return (render_template('500.html'),
                500)

    @app.errorhandler(422)
    def unprocessable_entity_error(error):
        return (jsonify({'success': False,
                'message': 'Unprocessable Entity', 'error': 422}), 422)

    @app.errorhandler(401)
    def unauthorized(error):
        return (render_template('401.html'),
                401)

    @app.errorhandler(AuthError)
    def unauth(error):
        return (render_template('401.html'),
                401)

    return app


myapp = create_app()

if __name__ == '__main__':
    myapp.run()
