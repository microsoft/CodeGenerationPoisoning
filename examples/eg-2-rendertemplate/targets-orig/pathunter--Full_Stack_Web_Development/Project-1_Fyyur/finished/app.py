"""
Contains all imports, views and custom function to run the application logic.
Also runs the application.
"""

#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
from datetime import datetime
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, jsonify
from sqlalchemy import func, inspect
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import Venue, Show, Artist, app, db

# TODO DONE: connect to a local postgresql database. SEE Models.py

#----------------------------------------------------------------------------#
# Custom Functions.
#----------------------------------------------------------------------------#

def object_as_dict(obj):
  '''Converts SQLALchemy Query Results to Dict

  *Input: ORM Object
  *Output: Single Object as Dict

  Makes use of the SQLAlchemy inspection system (https://docs.sqlalchemy.org/en/13/core/inspection.html)

  Used in following Views:
    - /venues
  '''
  return {c.key: getattr(obj, c.key)
        for c in inspect(obj).mapper.column_attrs}

def get_dict_list_from_result(result):
  '''Converts SQLALchemy Collections Results to Dict

  * Input: sqlalchemy.util._collections.result
  * Output: Result as list

  Source: https://stackoverflow.com/questions/48232222/how-to-deal-with-sqlalchemy-util-collections-result

  Used in following Views:
    - /venues
  '''
  list_dict = []
  for i in result:
      i_dict = i._asdict()  
      list_dict.append(i_dict)
  return list_dict

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  '''Converts datetime to local datetime of User

  * Input: 
      - <datetime> value
      - <string> format
  * Output: 
      - <datetime> datetime value of user timezone

  Source: http://babel.pocoo.org/en/latest/api/dates.html

  Only used for flask filter register.
  '''
  # Instead of parsing a string, I directly parse a datetime object, so I changed this function.
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(value, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  '''Homepage of the app.
  
  * Input: None

  Contains following features:
    - Create new Artist/Venues and Shows
    - Search for Artist and Venues
    - List recently created Artists and Shows
  
  Corresponding HTML:
    - templates/pages/home.html
  '''
  # Bonus: List recently listed Artists & Venues
  recent_artists = Artist.query.order_by(Artist.id.desc()).limit(10).all()
  recent_venues = Venue.query.order_by(Venue.id.desc()).limit(10).all()
  return render_template('pages/home.html', recent_artists = recent_artists, recent_venues = recent_venues)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  '''List all Venues
  
  * Input: None

  Contains following features:
    - See all Venues listed
    - Grouped by City and State
    - See number of upcoming Shows
    - Clicking on a Venue links to its detail page under "/venues/<int:venue_id>"
  
  Corresponding HTML:
    - templates/pages/venues.html
  '''
  # TODO DONE: replace with real venues data.
  #       num_shows should be aggregated based on number of upcoming shows per venue.
  
  # Step 1: Get a list of dicts that contains City & State names
  groupby_venues_result = (db.session.query(
                Venue.city,
                Venue.state
                )
        .group_by(
                Venue.city,
                Venue.state
                )
  )
  data=get_dict_list_from_result(groupby_venues_result)

  # Step 2: Loop through areas and append Venue data
  for area in data:
    # This will add a new key to the dictionary called "venues".
    # It gets filled with a list of venues that are in the same city-
    area['venues'] = [object_as_dict(ven) for ven in Venue.query.filter_by(city = area['city']).all()]
    # Step 3: Append num_shows
    for ven in area['venues']:
      # This will add a new subkey to the dictionarykey "venues" called "num_shows".
      # It gets filled with a number that counts how many upcoming shows the venue has.
      ven['num_shows'] = db.session.query(func.count(Show.c.Venue_id)).filter(Show.c.Venue_id == ven['id']).filter(Show.c.start_time > datetime.now()).all()[0][0]
 
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  '''Search for venues
  
  * Input: None

  Contains following features:
    - Search for venues with search term & get a list of results
    - See how many database entries are matched with the search term
    - Clicking on a result links to its Detail Page under "/venues/<int:venue_id>"
  
  Corresponding HTML:
    - templates/pages/search_venues.html
  '''
  # TODO DONE: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for Hop should return "The Musical Hop".
  # search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"

  # get search term from request
  search_term=request.form.get('search_term', '') 

  # use search term to count, how many occurance can be find in database
  search_venues_count = (db.session.query(
    func.count(Venue.id))
    .filter(Venue.name.contains(search_term))
    .all())

  # use search term to find all Venue records in database
  search_venues_result = Venue.query.filter(Venue.name.contains(search_term)).all()

  # create a well formatted response with above results
  response={
    "count": search_venues_count[0][0],
    "data": search_venues_result
  }

  return render_template('pages/search_venues.html', results=response, search_term=search_term)

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  '''See venues detail page
  
  * Input: <int> venue_id

  Contains following features:
    - See Venue and all stored information like name, address etc.
    - See list of upcoming & past shows
    - Possibility to delete record
  
  Corresponding HTML:
    - templates/pages/show_venues.html

  '''
  # TODO DONE: replace with real venue data from the venues table, using venue_id
  
  # Step 1: Get single Venue
  single_venue = Venue.query.get(venue_id)

  # Step 2: Get Past Shows
  single_venue.past_shows = (db.session.query(
    Artist.id.label("artist_id"), 
    Artist.name.label("artist_name"), 
    Artist.image_link.label("artist_image_link"), 
    Show)
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.Artist_id == Artist.id)
    .filter(Show.c.start_time <= datetime.now())
    .all())
  
  # Step 3: Get Upcomming Shows
  single_venue.upcoming_shows = (db.session.query(
    Artist.id.label("artist_id"), 
    Artist.name.label("artist_name"), 
    Artist.image_link.label("artist_image_link"), 
    Show)
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.Artist_id == Artist.id)
    .filter(Show.c.start_time > datetime.now())
    .all())

  # Step 4: Get Number of past Shows
  single_venue.past_shows_count = (db.session.query(
    func.count(Show.c.Venue_id))
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.start_time < datetime.now())
    .all())[0][0]

  # Step 5: Get Number of Upcoming Shows
  single_venue.upcoming_shows_count = (db.session.query(
    func.count(Show.c.Venue_id))
    .filter(Show.c.Venue_id == venue_id)
    .filter(Show.c.start_time > datetime.now())
    .all())[0][0]

  return render_template('pages/show_venue.html', venue=single_venue)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  '''Renders blank Venue form

  Input: None

  '''
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  '''Create new Venue

  Input: None

  Contains following features:
    - Called upon submitting the new Venue listing form
    - Handle data from VenueForm
    - Create new Venue with given data
    - Handle success & error with declerative flashes & messages

  Corresponding HTML:
      - templates/pages/new_venue.html

  '''
  # TODO DONE: insert form data as a new Venue record in the db, instead
  # TODO DONE: modify data to be the data object returned from db insertion
  form = VenueForm(request.form) # Initialize form instance with values from the request
  flashType = 'danger' # Initialize flashType to danger. Either it will be changed to "success" on successfully db insert, or in all other cases it should be equal to "danger"
  if form.validate():
    try:
      # Create a new instance of Venue with data from VenueForm
      newVenue = Venue(
        name = request.form['name'],
        city = request.form['city'],
        state = request.form['state'],
        address = request.form['address'],
        phone = request.form['phone'],
        genres = request.form.getlist('genres'),
        facebook_link = request.form['facebook_link']
        )
      db.session.add(newVenue)
      db.session.commit()
      # on successful db insert, flash success
      flashType = 'success'
      flash('Venue {} was successfully listed!'.format(newVenue.name))
    except: 
      # TODO DONE: on unsuccessful db insert, flash an error instead.
      flash('An error occurred due to database insertion error. Venue {} could not be listed.'.format(request.form['name']))
    finally:
      # Always close session
      db.session.close()
  else:
    flash(form.errors) # Flashes reason, why form is unsuccessful (not really pretty)
    flash('An error occurred due to form validation. Venue {} could not be listed.'.format(request.form['name']))
  
  return render_template('pages/home.html', flashType = flashType)

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  '''Delete existing Venue

  Input: <int> venue_id

  Contains following features:
    - Delete venue when red button on "/venues/<int:venue_id>" has been clicked.
    - Route gets fetched by Ajax. Javascript can be found under templates/layouts/main.html
    - Communicate success or error with corresponding redirections and alerts

  Corresponding HTML:
      - templates/pages/show_venue.html

  '''
  # TODO DONE: Complete this endpoint for taking a venue_id, and using
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.

  # DONE BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage

  # NOTE: Javascript to handle Button click + success/error in "main.html"
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
  except:
    db.session.rollback()
    # This will alert User that Venue could not be deleted because they are still Shows attached
    return jsonify({ 'success': False })
  finally:
    # Always close database session.
    db.session.close()
  # This will return the User to the HomePage 
  return jsonify({ 'success': True })

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  '''List all Artists
  
  * Input: None

  Contains following features:
    - See all Artists listed
    - Clicking on a Artist links to its detail dage under "/artists/<int:artist_id>"
  
  Corresponding HTML:
    - templates/pages/artists.html

  '''
  # TODO DONE: replace with real data returned from querying the database
  # Simply query database for all existing artists
  artists = Artist.query.all()
  return render_template('pages/artists.html', artists=artists)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  '''Search for artists
  
  * Input: None

  Contains following features:
    - Search for artists with search term & get a list of results
    - See how many database entries are matched with the search term
    - Clicking on a result links to its detail page under "/artists/<int:artist_id>"
  
  Corresponding HTML:
    - templates/pages/search_artists.html
  '''
  # TODO DONE: implement search on artists with partial string search. Ensure it is case-insensitive.
  # seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
  # search for "band" should return "The Wild Sax Band".
  
  # get search term from request
  search_term=request.form.get('search_term', '')

  # use search term to count, how many occurance can be find in database
  search_artist_count = db.session.query(func.count(Artist.id)).filter(Artist.name.contains(search_term)).all()
  
  # use search term to find all Artist records in database
  search_artist_result = Artist.query.filter(Artist.name.contains(search_term)).all()
  
  # create a well formatted response with above results
  response={
    "count": search_artist_count[0][0],
    "data": search_artist_result
  }
  return render_template('pages/search_artists.html', results=response, search_term=search_term)

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  '''See artist detail page
  
  * Input: <int> artist_id

  Contains following features:
    - See Artist and all stored information like name, address etc.
    - See list of upcoming & past shows
  
  Corresponding HTML:
    - templates/pages/show_artists.html

  '''
  # TODO DONE: replace with real artist data from the artists table, using artist_id
  
  # Step 1: Get single Artist
  single_artist = Artist.query.get(artist_id)

  # Step 2: Get Past Shows
  single_artist.past_shows = (db.session.query(
    Venue.id.label("venue_id"), 
    Venue.name.label("venue_name"), 
    Venue.image_link.label("venue_image_link"), 
    Show)
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.Venue_id == Venue.id)
    .filter(Show.c.start_time <= datetime.now())
    .all())
  
  # Step 3: Get Upcomming Shows
  single_artist.upcoming_shows = (db.session.query(
    Venue.id.label("venue_id"), 
    Venue.name.label("venue_name"), 
    Venue.image_link.label("venue_image_link"), 
    Show)
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.Venue_id == Venue.id)
    .filter(Show.c.start_time > datetime.now())
    .all())

  # Step 4: Get Number of past Shows
  single_artist.past_shows_count = (db.session.query(
    func.count(Show.c.Artist_id))
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.start_time < datetime.now())
    .all())[0][0]
  
  # Step 5: Get Number of Upcoming Shows
  single_artist.upcoming_shows_count = (db.session.query(
    func.count(Show.c.Artist_id))
    .filter(Show.c.Artist_id == artist_id)
    .filter(Show.c.start_time > datetime.now())
    .all())[0][0]

  return render_template('pages/show_artist.html', artist=single_artist)

#  Update
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  '''Render ArtistForm with prefilled values
  
  * Input: <int> artist_id

  Contains following features:
    - Render ArtistForm with prefilled values
    - On form submission, call "edit_artist_submission" to edit artist in database
  
  Corresponding HTML:
    - templates/forms/edit_artist.html

  '''
  # Initiate instance of ArtistForm 
  form = ArtistForm()

  # Get single artist entry
  artist = Artist.query.get(artist_id)

  # Pre Fill form with data
  form.name.data = artist.name
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.genres.data = artist.genres
  form.facebook_link.data = artist.facebook_link

  # TODO DONE: populate form with fields from artist with ID <artist_id>
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  '''Update existing artist
  
  * Input: <int> artist_id

  Contains following features:
    - Called upon form submission by "edit_artist"
    - Update fields from existing artist with new values
  
  Corresponding HTML:
    - templates/forms/edit_artist.html

  '''
  # TODO DONE: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  
  artist = Venue.query.get(artist_id)
  artist.name = request.form['name'],
  artist.city = request.form['city'],
  artist.state = request.form['state'],
  artist.phone = request.form['phone'],
  artist.genres = request.form['genres'],
  artist.facebook_link = request.form['facebook_link']
  db.session.add(artist)
  db.session.commit()
  db.session.close()

  # Redirect user to artist detail page with updated values
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  '''Render VenueForm with prefilled values
  
  * Input: <int> venue_id

  Contains following features:
    - Render VenueForm with prefilled values
    - On form submission, call "edit_venue_submission" to edit venue in database
  
  Corresponding HTML:
    - templates/forms/edit_venue.html

  '''
  # Initiate instance of VenueForm 
  form = VenueForm()

   # Get single venue entry
  venue = Venue.query.get(venue_id)

  # Pre Fill form with data
  form.name.data = venue.name
  form.city.data = venue.city
  form.state.data = venue.state
  form.address.data = venue.address
  form.phone.data = venue.phone
  form.genres.data = venue.genres
  form.facebook_link.data = venue.facebook_link

  # TODO DONE: populate form with values from venue with ID <venue_id>
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  '''Update existing venue
  
  * Input: <int> venue_id

  Contains following features:
    - Called upon form submission by "edit_venue"
    - Update fields from existing venue with new values
  
  Corresponding HTML:
    - templates/forms/edit_venue.html

  '''
  # TODO DONE: take values from the form submitted, and update existing
  # venue record with ID <venue_id> using the new attributes
  
  venue = Venue.query.get(venue_id)
  venue.name = request.form['name'],
  venue.city = request.form['city'],
  venue.state = request.form['state'],
  venue.address = request.form['address'],
  venue.phone = request.form['phone'],
  venue.genres = request.form.getlist('genres'),
  venue.facebook_link = request.form['facebook_link']
  db.session.add(venue)
  db.session.commit()
  db.session.close()

  # Redirect user to venue detail page with updated values
  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  '''Renders blank Artist form

  Input: None

  '''
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  '''Create new Artist

  Input: None

  Contains following features:
    - Called upon submitting the new Artist listing form
    - Handle data from ArtistForm
    - Create new Artist with given data
    - Handle success & error with declerative flashes & messages

  Corresponding HTML:
      - templates/pages/new_artist.html

  '''
  # TODO DONE: insert form data as a new Artist record in the db, instead
  # TODO DONE: modify data to be the data object returned from db insertion
  form = ArtistForm(request.form) # Initialize form instance with values from the request
  flashType = 'danger' # Initialize flashType to danger. Either it will be changed to "success" on successfully db insert, or in all other cases it should be equal to "danger"
  if form.validate():
    try:
      # Create a new instance of Artist with data from ArtistForm
      newArtist = Artist(
        name = request.form['name'],
        city = request.form['city'],
        state = request.form['state'],
        phone = request.form['phone'],
        facebook_link = request.form['facebook_link'],
        genres = request.form.getlist('genres')
        )
      db.session.add(newArtist)
      db.session.commit()
      # on successful db insert, flash success
      flashType = 'success'
      flash('Artist {} was successfully listed!'.format(newArtist.name)) 
    except: 
      # TODO DONE: on unsuccessful db insert, flash an error instead.
      flash('An error occurred due to database insertion error. Artist {} could not be listed.'.format(request.form['name']))
    finally:
      # Always close session
      db.session.close()
  else:
    flash(form.errors) # Flashes reason, why form is unsuccessful (not really pretty)
    flash('An error occurred due to form validation. Artist {} could not be listed.'.format(request.form['name']))

  return render_template('pages/home.html', flashType = flashType)


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  '''List all Shows
  
  * Input: None

  Contains following features:
    - See all Shows listed
    - See corresponding artist information for every Show
  
  Corresponding HTML:
    - templates/pages/shows.html

  '''
  # TODO DONE: replace with real shows data.
  # TODO DONE: num_shows should be aggregated based on number of upcoming shows per venue.
  
  # Make a database query to get all shows
  # Rename Fields so frontend can access the correct values
  shows = (db.session.query(
    Venue.id.label("venue_id"), 
    Venue.name.label("venue_name"),
    Artist.id.label("artist_id"), 
    Artist.name.label("artist_name"), 
    Artist.image_link.label("artist_image_link"), 
    Show)
    .filter(Show.c.Venue_id == Venue.id)
    .filter(Show.c.Artist_id == Artist.id)
    .all())

  return render_template('pages/shows.html', shows=shows)

@app.route('/shows/create')
def create_shows():
  '''Renders blank Show form

  Input: None

  '''
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  '''Create new Show

  Input: None

  Contains following features:
    - Called upon submitting the new Show listing form
    - Handle data from ShowForm
    - Create new Show with given data
    - Handle success & error with declerative flashes & messages

  Corresponding HTML:
      - templates/pages/new_artist.html

  '''

  # TODO DONE: insert form data as a new Show record in the db, instead

  form = ShowForm(request.form) # Initialize form instance with values from the request
  flashType = 'danger' # Initialize flashType to danger. Either it will be changed to "success" on successfully db insert, or in all other cases it should be equal to "danger"
  if form.validate():
    # NOTE: Form could not be validated due to a missing csrf-token.
    # I solved this issue by putting a "{{ form.csrf_token() }}"
    # under the respective <form> tag in forms/new_show.html
    try:
      # Create a new instance of Show with data from ShowForm
      newShow = Show.insert().values(
        Venue_id = request.form['venue_id'],
        Artist_id = request.form['artist_id'],
        start_time = request.form['start_time']
      )
      db.session.execute(newShow) 
      db.session.commit()
      # on successful db insert, flash success
      flashType = 'success'
      flash('Show was successfully listed!')
    except : 
      # TODO DONE: on unsuccessful db insert, flash an error instead.
      flash('An error occurred due to database insertion error. Show could not be listed.')
    finally:
      # Always close session
      db.session.close()
  else:
    flash(form.errors) # Flashes reason, why form is unsuccessful (not really pretty)
    flash('An error occurred due to form validation. Show could not be listed.')
  
  return render_template('pages/home.html', flashType = flashType)

@app.errorhandler(404)
def not_found_error(error):
    '''Displays Error Page in case of a 404 error

    Corresponding HTML:
      - templates/errors/404.html

    '''
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    '''Displays Error Page in case of a 500 error

    Corresponding HTML:
      - templates/errors/500.html

    '''
    return render_template('errors/500.html'), 500

if not app.debug:
    # if app is not in debug mode, fill error.log
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

# Run App with Default port. Debug Mode set in config.py
if __name__ == '__main__':
    app.run(debug=app.debug) # NOTE I prefer to set debug mode to true within the script
