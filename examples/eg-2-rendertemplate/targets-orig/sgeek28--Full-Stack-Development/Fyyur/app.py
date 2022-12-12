#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *

import datetime
from flask_migrate import Migrate
from sqlalchemy_utils import create_database, database_exists
import config
import traceback
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)
migrate=Migrate(app,db)

# TODO: connect to a local postgresql database

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    #added
    
    genres=db.Column(db.String)
    seeking_talent = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))
    website = db.Column(db.String(120))

    def add(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.update(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit

    def __repr__(self):
        return '<Venue %r>' % self

    @property
    def serialize(self):
        return {'id': self.id,
                'name': self.name,
                'genres': self.genres.split(','),
                'city': self.city,
                'state': self.state,
                'phone': self.phone,
                'address': self.address,
                'image_link': self.image_link,
                'facebook_link': self.facebook_link,
                'website': self.website,
                'seeking_talent': self.seeking_talent,
                'seeking_description': self.seeking_description
                }

    @property
    def serialize_with_upcoming_shows_count(self):
        return {'id': self.id,
                'name': self.name,
                'genres': self.genres.split(','),
                'city': self.city,
                'state': self.state,
                'phone': self.phone,
                'address': self.address,
                'image_link': self.image_link,
                'facebook_link': self.facebook_link,
                'website': self.website,
                'seeking_talent': self.seeking_talent,
                'seeking_description': self.seeking_description,
                'num_shows': Show.query.filter(
                    Show.start_time > datetime.datetime.now(),
                    Show.venue_id == self.id)
                }

    @property
    def serialize_with_shows_details(self):
        return {'id': self.id,
                'name': self.name,
                'city': self.city,
                'state': self.state,
                'phone': self.phone,
                'genres':self.genres.split(','),
                'address': self.address,
                'image_link': self.image_link,
                'facebook_link': self.facebook_link,
                'seeking_talent': self.seeking_talent,
                'seeking_description': self.seeking_description,
                'website': self.website,
                'upcoming_shows': [show.serialize_with_artist_venue for show in Show.query.filter(
                    Show.start_time > datetime.datetime.now(),
                    Show.venue_id == self.id).all()],
                'past_shows': [show.serialize_with_artist_venue for show in Show.query.filter(
                    Show.start_time < datetime.datetime.now(),
                    Show.venue_id == self.id).all()],
                'upcoming_shows_count': len(Show.query.filter(
                    Show.start_time > datetime.datetime.now(),
                    Show.venue_id == self.id).all()),
                'past_shows_count': len(Show.query.filter(
                    Show.start_time < datetime.datetime.now(),
                    Show.venue_id == self.id).all())
                }

    @property
    def filter_on_city_state(self):
        return {'city': self.city,
                'state': self.state,
                'venues': [v.serialize_with_upcoming_shows_count
                           for v in Venue.query.filter(Venue.city == self.city,
                                                       Venue.state == self.state).all()]}

    # TODO: implement any missing fields, as a database migration using Flask-Migrate

class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))

    #added
    address = db.Column(db.String(120))
    website = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean)
    seeking_description = db.Column(db.String(500))


    def add(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.update(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return '<Artist %r>' % self

    @property
    def serialize_with_shows_details(self):
        return {'id': self.id,
                'name': self.name,
                'city': self.city,
                'state': self.state,
                'phone': self.phone,
                'genres': self.genres.split(','),
                'image_link': self.image_link,
                'facebook_link': self.facebook_link,
                'address':self.address,
                'seeking_venue': self.seeking_venue,
                'seeking_description': self.seeking_description,
                'website': self.website,
                'upcoming_shows': [show.serialize_with_artist_venue for show in Show.query.filter(
                    Show.start_time > datetime.datetime.now(),
                    Show.artist_id == self.id).all()],
                'past_shows': [show.serialize_with_artist_venue for show in Show.query.filter(
                    Show.start_time < datetime.datetime.now(),
                    Show.artist_id == self.id).all()],
                'upcoming_shows_count': len(Show.query.filter(
                    Show.start_time > datetime.datetime.now(),
                    Show.artist_id == self.id).all()),
                'past_shows_count': len(Show.query.filter(
                    Show.start_time < datetime.datetime.now(),
                    Show.artist_id == self.id).all())
                }

    @property
    def serialize(self):
        return {'id': self.id,
                'name': self.name,
                'city': self.city,
                'state': self.state,
                'address':self.address,
                'phone': self.phone,
                'genres': self.genres.split(','),
                'image_link': self.image_link,
                'facebook_link': self.facebook_link,
                'seeking_venue': self.seeking_venue,
                'seeking_description': self.seeking_description,
                'website': self.website
                }
    # TODO: implement any missing fields, as a database migration using Flask-Migrate

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.
class Show(db.Model):
    __tablename__ = 'Show'

    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime())
    venue_id = db.Column(db.Integer, db.ForeignKey(
        'Venue.id'), nullable=False)
    venue = db.relationship(
        'Venue', backref=db.backref('shows', cascade='all, delete'))
    artist_id = db.Column(db.Integer, db.ForeignKey(
        'Artist.id'), nullable=False)
    artist = db.relationship(
        'Artist', backref=db.backref('shows', cascade='all, delete'))

    def add(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.update(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return '<Show %r>' % self

    @property
    def serialize(self):
        return {'id': self.id,
                'start_time': self.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                'venue_id': self.venue_id,
                'artist_id': self.artist_id
                }

    @property
    def serialize_with_artist_venue(self):
        return {'id': self.id,
                'start_time': self.start_time.strftime("%m/%d/%Y, %H:%M:%S"),
                'venue': [v.serialize for v in Venue.query.filter(Venue.id == self.venue_id).all()][0],
                'artist': [a.serialize for a in Artist.query.filter(Artist.id == self.artist_id).all()][0]
                }

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  city_states = Venue.query.distinct(Venue.city,Venue.state).all()
  data = [cs.filter_on_city_state for cs in city_states]
  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"

  venue_search_keyterm=request.form.get('search_term', None)
  venue_items = Venue.query.filter(Venue.name.ilike("%{}%".format(venue_search_keyterm))).all()
  venues_count = len(venue_items)
  response = {
      "count": venues_count,
      "data": [v.serialize for v in venue_items]
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  # TODO: replace with real venue data from the venues table, using venue_id


  venue_items = Venue.query.filter(Venue.id == venue_id).one_or_none()
  if venue_items is None:
      abort(404)

  data = venue_items.serialize_with_shows_details
  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  venue_item_form = VenueForm(request.form)
  try:
        new_venue_item = Venue(
            name=venue_item_form.name.data,
            genres=','.join(venue_item_form.genres.data),
            address=venue_item_form.address.data,
            city=venue_item_form.city.data,
            state=venue_item_form.state.data,
            phone=venue_item_form.phone.data,
            facebook_link=venue_item_form.facebook_link.data,
            image_link=venue_item_form.image_link.data,
            seeking_description=venue_item_form.seeking_description.data,
            seeking_talent=venue_item_form.seeking_talent.data,
            website=venue_item_form.website.data)

        new_venue_item.add()
        # TODO: on unsuccessful db insert, flash an error instead.
        flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except Exception as ex:
        # e.g., flash('An error occurred. Venue ' + data.name + ' could not be listed.')
        flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
        traceback.print_exc()
 
  # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
  return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # TODO: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  try:
      venue_item_deleted = Venue.query.filter(Venue.id == venue_id).one()
      venue_item_deleted.delete()
      flask("Venue {0} has been deleted successfully".format(
          venue_item_deleted[0]['name']))
  except NoResultFound:
      abort(404)

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  # TODO: replace with real data returned from querying the database

  artist_items=Artist.query.all()
  data=[a.serialize_with_shows_details for a in artist_items]
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # TODO: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  
  artist_search_keyterm=request.form.get('search_term','None')
  artist_search_item=Artist.query.filter(Artist.name.ilike("%{}%".format(artist_search_keyterm))).all()
  count_artists=len(artist_search_item)
  response = {
      "count": count_artists,
      "data": [a.serialize for a in artist_search_item]
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the artist page with the given artist_id
  # TODO: replace with real artist data from the artists table, using artist_id

  artist_item=Artist.query.filter(Artist.id==artist_id).one()
  if artist_item is None:
        abort(404)

  data = artist_item.serialize_with_shows_details
  
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  #artist_item_form=ArtistForm()
  artist_item_to_update=Artist.query.filter(Artist.id==artist_id).one_or_none()
  if artist_item_to_update is None:
        abort(404)
  artist = artist_item_to_update.serialize

  # TODO: populate form with fields from artist with ID <artist_id>
  form = ArtistForm(data=artist)
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes

  form = ArtistForm(request.form)
  try:
      artist = Artist.query.filter_by(id=artist_id).one()
      artist.name = form.name.data,
      artist.genres = json.dumps(form.genres.data),  # array json
      artist.city = form.city.data,
      artist.state = form.state.data,
      artist.phone = form.phone.data,
      artist.facebook_link = form.facebook_link.data,
      artist.image_link = form.image_link.data,
      artist.website=form.website.data
      artist.seeking_venue=form.seeking_venue.data
      artist.address=form.address.data
      artist.seeking_description=form.seeking_description.data
      artist.update()
      # on successful db insert, flash success
      flash('Artist ' + request.form['name'] + ' was successfully updated!')
  except Exception as e:
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  #venue_item_form = VenueForm()
  venue_item_to_update = Venue.query.filter(Venue.id == venue_id).one_or_none()
  if venue_item_to_update is None:
      abort(404)

  venue = venue_item_to_update.serialize
  form = VenueForm(data=venue)
  # TODO: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # TODO: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes

  form = VenueForm(request.form)
  try:
      venue = Venue.query.filter(Venue.id==venue_id).one()
      venue.name = form.name.data,
      venue.address = form.address.data,
      venue.genres = '.'.join(form.genres.data),  # array json
      venue.city = form.city.data,
      venue.state = form.state.data,
      venue.phone = form.phone.data,
      venue.facebook_link = form.facebook_link.data,
      venue.image_link = form.image_link.data,
      venue.website=form.website.data,
      venue.seeking_description=form.seeking_description.data,
      venue.seeking_talent=form.seeking_talent.data
      venue.update()
      # on successful db insert, flash success
      flash('Venue ' + request.form['name'] + ' was successfully updated!')
  except Exception as e:
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  # TODO: insert form data as a new Venue record in the db, instead
  # TODO: modify data to be the data object returned from db insertion

  artist_item_form = ArtistForm(request.form)
  try:
      new_artist_item = Artist(
          name=artist_item_form.name.data,
          genres=','.join(artist_item_form.genres.data),
          address=artist_item_form.address.data,
          city=artist_item_form.city.data,
          state=artist_item_form.state.data,
          phone=artist_item_form.phone.data,
          facebook_link=artist_item_form.facebook_link.data,
          image_link=artist_item_form.image_link.data,
          website=artist_item_form.website.data,
          seeking_description=artist_item_form.seeking_description.data,
          seeking_venue=artist_item_form.seeking_venue.data
          )
      new_artist_item.add()
      # on successful db insert, flash success
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except Exception as ex:
      flash('An error occurred. Artist ' +
            request.form['name'] + ' could not be listed.')

  return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  # TODO: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  show_items = Show.query.all()
  data = [s.serialize_with_artist_venue for s in show_items]
  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  # TODO: insert form data as a new Show record in the db, instead

  show_form_item = ShowForm(request.form)
  try:
      show_item = Show(
          artist_id=show_form_item.artist_id.data,
          venue_id=show_form_item.venue_id.data,
          start_time=show_form_item.start_time.data
      )
      show_item.add()
      # on successful db insert, flash success
      flash('Show was successfully listed!')
  except Exception as e:
      flash('An error occurred. Show could not be listed.')

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
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
