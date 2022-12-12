#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import FlaskForm, CSRFProtect
from forms import *
from datetime import datetime

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# DONE: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#


class Venue(db.Model):
    __tablename__ = 'venue'

    # Add nullable constraints to keep consistent with forms
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    website = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()), nullable=False)
    seeking_talent = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String())

    shows = db.relationship('Show', backref='venue')
    artists = db.relationship('Artist', secondary='show', backref='venues')

    def __repr__(self):
        return f'<Venue id:{self.id} name:{self.name}>'


class Artist(db.Model):
    __tablename__ = 'artist'

    # Add nullable constraints to keep consistent with forms
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    city = db.Column(db.String(120), nullable=False)
    state = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    website = db.Column(db.String(120))
    genres = db.Column(db.ARRAY(db.String()), nullable=False)
    seeking_venue = db.Column(db.Boolean, nullable=False, default=False)
    seeking_description = db.Column(db.String())

    shows = db.relationship('Show', backref='artist')

    def __repr__(self):
        return f'<Venue id:{self.id} name:{self.name}>'


class Show(db.Model):
    __tablename__ = 'show'

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey('venue.id'))
    artist_id = db.Column(db.Integer, db.ForeignKey('artist.id'))
    start_time = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'< Venue id: {self.id} artist_id: {self.artist_id} \
            venue_id: {self.venue_id} start: {self.start_time} >'

# DONE Implement Show and Artist models, and complete all model relationships
#      and properties, as a database migration.

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#


def format_datetime(date, format='medium'):
    """Format datetime

    Parameters
    ----------
    date : datetime 
        Datetime instance 
    format : string
        Time format string
    """
    if format == 'full':
        format = "EEEE MMMM, d, y 'at' h:mma"
    elif format == 'medium':
        format = "EE MM, dd, y h:mma"
    return babel.dates.format_datetime(date, format)


app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#


@app.route('/')
def index():
    artists = Artist.query.order_by(Artist.id.desc()).limit(10).all()
    venues = Venue.query.order_by(Venue.id.desc()).limit(10).all()

    return render_template('pages/home.html', artists=artists, venues=venues)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
    # DONE: replace with real venues data.
    #       num_shows should be aggregated based on number of upcoming shows
    #       per venue.

    venues = Venue.query.order_by(Venue.city, Venue.state, Venue.name).all()

    # Group venues by location in a dictionary with (key, value) as follows
    #   key = "venue.city,venue.state"
    #   value = dictionary that stores venues info

    locations = {}
    for venue in venues:
        key = f'{venue.city},{venue.state}'
        if key not in locations:
            locations[key] = {
                'city': venue.city,
                'state': venue.state,
                'venues': []
            }
        locations[key]['venues'].append({
            'id': venue.id,
            'name': venue.name,
            'num_upcoming_shows': Show.query
            .filter(Show.venue_id == venue.id,
                    Show.start_time > db.func.now())
            .count()
        })

    data = [location for location in locations.values()]

    return render_template('pages/venues.html', areas=data)


@ app.route('/venues/search', methods=['POST'])
def search_venues():
    # DONE: implement search on artists with partial string search. Ensure it
    #       is case-insensitive.
    #       Search for Hop should return "The Musical Hop".
    #       search for "Music" should return "The Musical Hop" and
    #       "Park Square Live Music & Coffee"

    search = request.form.get('search_term', '')

    search_results = Venue.query.filter(Venue.name.ilike(f'%{search}%'))\
        .order_by(Venue.name).all()

    response = {
        'count': len(search_results),
        'data': [{
            'id': venue.id,
            'name': venue.name,
            'num_upcoming_shows': Show.query
            .filter(Show.venue_id == venue.id,
                    Show.start_time > db.func.now())
            .count()
        } for venue in search_results]
    }

    return render_template('pages/search_venues.html', results=response,
                           search_term=request.form.get('search_term', ''))


@ app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
    # shows the venue page with the given venue_id
    # DONE: replace with real venue data from the venues table, using venue_id

    venue = Venue.query.get_or_404(venue_id)

    query = db.session.query(
        Artist.id.label('artist_id'),
        Artist.name.label('artist_name'),
        Artist.image_link.label('artist_image_link'),
        Show.start_time.label('start_time')
    ).filter(Show.venue_id == venue_id,
             Show.artist_id == Artist.id)

    venue.past_shows = query.filter(Show.start_time <= db.func.now()).all()
    venue.past_shows_count = len(venue.past_shows)

    venue.upcoming_shows = query.filter(Show.start_time > db.func.now()).all()
    venue.upcoming_shows_count = len(venue.upcoming_shows)

    return render_template('pages/show_venue.html', venue=venue)

#  Create Venue
#  ----------------------------------------------------------------


@ app.route('/venues/create', methods=['GET'])
def create_venue_form():
    form = VenueForm()
    return render_template('forms/new_venue.html', form=form)


@ app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    # DONE: insert form data as a new Venue record in the db, instead
    # DONE: modify data to be the data object returned from db insertion
    # on successful db insert, flash success

    form = VenueForm(request.form)

    if form.validate():
        try:
            venue = Venue(name=form.name.data,
                          city=form.city.data,
                          state=form.state.data,
                          address=form.address.data,
                          phone=form.phone.data,
                          genres=form.genres.data,
                          facebook_link=form.facebook_link.data)
            db.session.add(venue)
            db.session.commit()
            flash(
                f'Venue {form.name.data} was successfully listed!', 'success')
        except:
            db.session.rollback()
            flash('An error occurred on database insertion. Venue '
                  + form.name.data + ' could not be listed.', 'danger')

        finally:
            db.session.close()
    else:
        errors = '• ' + '\n\t• '.join([error[0]
                                       for error in form.errors.values()])
        flash('An error occurred in form validation. Venue ' + form.name.data
              + ' could not be listed.\n\t' + errors, 'danger')
        return render_template('forms/new_venue.html', form=form)

    # DONE: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@ app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
    # DONE: Complete this endpoint for taking a venue_id, and using
    # SQLAlchemy ORM to delete a record. Handle cases where the session
    # commit could fail.

    venue = Venue.query.get_or_404(venue_id)

    try:
        db.session.delete(venue)
        db.session.commit()
        flash(f'Venue {venue.name} was successfully deleted!', 'success')
    except:
        db.session.rollback()
        flash('An error occurred on deletion. Venue '
              + venue.name + ' could not be deleted.', 'danger')
        return jsonify({'success': False})
    finally:
        db.session.close()

    # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page,
    # have it so that clicking that button delete it from the db then redirect
    # the user to the homepage
    return jsonify({'success': True})


@ app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
    venue = Venue.query.get_or_404(venue_id)

    form = VenueForm(request.form, obj=venue)
    form.genres.data = venue.genres

    # DONE: populate form with values from venue with ID <venue_id>
    return render_template('forms/edit_venue.html', form=form, venue=venue)


@ app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
    venue = Venue.query.get_or_404(venue_id)

    form = VenueForm(request.form)
    if form.validate():
        try:
            venue.name = form.name.data
            venue.city = form.city.data
            venue.state = form.state.data
            venue.address = form.address.data
            venue.phone = form.phone.data
            venue.genres = form.genres.data
            venue.facebook_link = form.facebook_link.data
            db.session.commit()
            flash(
                f'Venue {form.name.data} was successfully updated!', 'success')
        except:
            db.session.rollback()
            flash(
                'An error occurred on database update. Venue' + form.name.data
                + ' could not be updated.', 'danger')
        finally:
            db.session.close()
    else:
        errors = '• ' + '\n\t• '.join([error[0]
                                       for error in form.errors.values()])
        flash('An error occurred in form validation. Venue ' + form.name.data
              + ' could not be updated.\n\t' + errors, 'danger')
        return render_template('forms/edit_venue.html', form=form, venue=venue)

    # DONE: take values from the form submitted, and update existing
    # venue record with ID <venue_id> using the new attributes
    return redirect(url_for('show_venue', venue_id=venue_id))


#  Artists
#  ----------------------------------------------------------------


@ app.route('/artists')
def artists():
    # DONE: replace with real data returned from querying the database

    data = db.session.query(Artist.id, Artist.name).order_by(Artist.name).all()

    return render_template('pages/artists.html', artists=data)


@ app.route('/artists/search', methods=['POST'])
def search_artists():
    # DONE: implement search on artists with partial string search.
    # Ensure it is case-insensitive.
    # Search for "A" should return "Guns N Petals", "Matt Quevado",
    # and "The Wild Sax Band".
    # Search for "band" should return "The Wild Sax Band".

    search = request.form.get('search_term', '')

    search_results = Artist.query.filter(
        Artist.name.ilike(f'%{search}%')
    ).order_by(Artist.name).all()

    response = {
        'count': len(search_results),
        'data': [{
            'id': artist.id,
            'name': artist.name,
            'num_upcoming_show': Show.query
            .filter(Show.artist_id == artist.id,
                    Show.start_time > db.func.now())
            .count()
        } for artist in search_results]
    }

    return render_template('pages/search_artists.html', results=response,
                           search_term=request.form.get('search_term', ''))


@ app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
    # shows the venue page with the given venue_id
    # DONE: replace with real venue data from the venues table, using venue_id

    artist = Artist.query.get_or_404(artist_id)

    query = db.session.query(
        Venue.id.label('venue_id'),
        Venue.name.label('venue_name'),
        Venue.image_link.label('venue_image_link'),
        Show.start_time.label('start_time')
    ).filter(Show.artist_id == artist_id,
             Show.venue_id == Venue.id)

    artist.past_shows = query.filter(Show.start_time <= db.func.now()).all()
    artist.past_shows_count = len(artist.past_shows)

    artist.upcoming_shows = query.filter(Show.start_time > db.func.now()).all()
    artist.upcoming_shows_count = len(artist.upcoming_shows)

    return render_template('pages/show_artist.html', artist=artist)

#  Update
#  ----------------------------------------------------------------


@ app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)
    form = ArtistForm(request.form, obj=artist)
    form.genres.data = artist.genres

    # DONE: populate form with fields from artist with ID <artist_id>
    return render_template('forms/edit_artist.html', form=form, artist=artist)


@ app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    # DONE: take values from the form submitted, and update existing
    # artist record with ID <artist_id> using the new attributes
    artist = Artist.query.get_or_404(artist_id)

    form = ArtistForm(request.form)
    if form.validate():
        try:
            artist.name = form.name.data
            artist.city = form.city.data
            artist.state = form.state.data
            artist.phone = form.phone.data
            artist.genres = form.genres.data
            artist.facebook_link = form.facebook_link.data
            db.session.commit()
            flash(
                f'Artist {form.name.data} was successfully updated!', 'success')
        except:
            db.session.rollback()
            flash(
                'An error occurred on database update. Artist '
                + form.name.data + ' could not be updated.', 'danger')
        finally:
            db.session.close()
    else:
        errors = '• ' + '\n\t• '.join([error[0]
                                       for error in form.errors.values()])
        flash('An error occurred in form validation. Artist ' + form.name.data
              + ' could not be updated.\n\t' + errors, 'danger')
        return render_template('forms/edit_artist.html', form=form, artist=artist)

    return redirect(url_for('show_artist', artist_id=artist_id))

#  Create Artist
#  ----------------------------------------------------------------


@ app.route('/artists/create', methods=['GET'])
def create_artist_form():
    form = ArtistForm()
    return render_template('forms/new_artist.html', form=form)


@ app.route('/artists/create', methods=['POST'])
def create_artist_submission():
    # called upon submitting the new artist listing form
    # DONE: insert form data as a new Venue record in the db, instead
    # DONE: modify data to be the data object returned from db insertion

    form = ArtistForm(request.form)
    if form.validate():
        try:
            artist = Artist(name=form.name.data,
                            city=form.city.data,
                            state=form.state.data,
                            phone=form.phone.data,
                            genres=form.genres.data,
                            facebook_link=form.facebook_link.data)
            db.session.add(artist)
            db.session.commit()
            flash(
                f'Artist {form.name.data} was successfully listed!', 'success')
        except:
            db.session.rollback()
            flash(
                'An error occurred on database insertion. Artist '
                + form.name.data + ' could not be listed.', 'danger')
        finally:
            db.session.close()
    else:
        errors = '• ' + '\n\t• '.join([error[0]
                                       for error in form.errors.values()])
        flash('An error occurred in form validation. Artist ' + form.name.data
              + ' could not be updated.\n\t' + errors, 'danger')
        return render_template('forms/new_artist.html', form=form)

    # on successful db insert, flash success
    # DONE: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Artist ' + data.name + ' could not be listed.')
    return render_template('pages/home.html')


@ app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
    artist = Artist.query.get_or_404(artist_id)

    try:
        db.session.delete(artist)
        db.session.commit()
        flash(f'Venue {artist.name} was successfully deleted!', 'success')
    except:
        db.session.rollback()
        flash('An error occurred on deletion. Venue '
              + artist.name + ' could not be deleted.', 'danger')
        return jsonify({'success': True})
    finally:
        db.session.close()

    return jsonify({'success': True})


#  Shows
#  ----------------------------------------------------------------

@ app.route('/shows')
def shows():
    # displays list of shows at /shows
    # DONE: replace with real venues data.

    query = db.session.query(Venue.id.label('venue_id'),
                             Venue.name.label('venue_name'),
                             Artist.id.label('artist_id'),
                             Artist.name.label('artist_name'),
                             Artist.image_link.label('artist_image_link'),
                             Show.start_time.label('start_time'))\
        .filter(Show.venue_id == Venue.id,
                Show.artist_id == Artist.id)

    upcoming_shows = query.filter(Show.start_time > db.func.now())\
        .order_by(Show.start_time).all()
    past_shows = query.filter(Show.start_time <= db.func.now())\
        .order_by(Show.start_time.desc()).all()

    data = {
        'num_upcoming_shows': len(upcoming_shows),
        'upcoming_shows': upcoming_shows,
        'num_past_shows': len(past_shows),
        'past_shows': past_shows
    }

    return render_template('pages/shows.html', shows=data)


@ app.route('/shows/create')
def create_shows():
    # renders form. do not touch.
    form = ShowForm()
    return render_template('forms/new_show.html', form=form)


@ app.route('/shows/create', methods=['POST'])
def create_show_submission():
    # called to create new shows in the db, upon submitting new show listing
    # form
    # DONE : insert form data as a new Show record in the db, instead

    form = ShowForm(request.form)
    if form.validate():
        try:
            show = Show(artist_id=form.artist_id.data,
                        venue_id=form.venue_id.data,
                        start_time=form.start_time.data)
            db.session.add(show)
            db.session.commit()
            flash(
                'Show was successfully listed!', 'success')
        except:
            db.session.rollback()
            flash(
                'An error occurred on database insertion.'
                + ' Show could not be listed.', 'danger')
        finally:
            db.session.close()
    else:
        flash(
            'An error occurred in form validation.'
            + ' Show could not be listed.', 'danger')

    # on successful db insert, flash success
    # DONE: on unsuccessful db insert, flash an error instead.
    # e.g., flash('An error occurred. Show could not be listed.')
    # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
    return render_template('pages/home.html')


@ app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@ app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
