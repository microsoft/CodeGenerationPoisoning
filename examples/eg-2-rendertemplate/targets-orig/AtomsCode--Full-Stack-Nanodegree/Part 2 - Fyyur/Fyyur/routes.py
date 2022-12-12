import sys
import json
import dateutil.parser
import babel
from sqlalchemy import func
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort, Blueprint
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from models import *
from pprint import pprint

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#
routes_controller = Blueprint('routes_controller', __name__)


@app.route('/')
def index():
  return render_template('pages/home.html')

#  ----------------------------------------------------------------
#!  Main Venue
#  ----------------------------------------------------------------
@app.route('/venues')
def venues():

    data = []
    venues = Venue.query.all()
    areas = set()

    # Saving city & state into areas
    for venue in venues:
      areas.add((venue.city, venue.state))

    # Adding areas[city,state] into data 
    for location in areas:
      data.append({
          "city": location[0],
          "state": location[1],
          "venues": []
      })

    for venue in venues:
      num_upcoming_shows = 0

      # loop through every venue and filter by its id to check shows
      shows = Show.query.filter_by(Venue_id=venue.id).all()

      # current_date will be compared with show start time to determined the nummber of upcoming shows
      current_date = datetime.now()

      for show in shows:
        if show.start_time > current_date:
            num_upcoming_shows = num_upcoming_shows+1
      
      # Adding everything to data
      for venue_location in data:
        if venue.state == venue_location['state'] and venue.city == venue_location['city']:
          venue_location['venues'].append({
              "id": venue.id,
              "name": venue.name,
              "num_upcoming_shows": num_upcoming_shows
          })

    return render_template('pages/venues.html', areas=data)


#!   input text search on venue page
#  ----------------------------------------------------------------
@app.route('/venues/search', methods=['POST'])
def search_venues():
  # search_term Will contain what the user entered as search word
  search_term = request.form.get('search_term', '')

  # filter the venue by the search_term
  result = Venue.query.filter(Venue.name.ilike(f'%{search_term}%'))

  response={
    "count": result.count(),
    "data": result
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

#! Find venue by id
#  ----------------------------------------------------------------
@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):

  venue = Venue.query.get(venue_id)
  shows_id = Show.query.filter_by(Venue_id=venue_id).all()

  # Variable will be used in this process
  data={}
  past_shows = []
  upcoming_shows = []
  current_time = datetime.now()

  for show in shows_id:
    data={
    "artist_id": show.Artist_id,
    "artist_name": show.artist.name,
    "artist_image_link": show.artist.image_link,
    "start_time": format_datetime(str(show.start_time))
    } 
    if show.start_time > current_time:
      upcoming_shows.append(data)
      data={
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres,
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website_link,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_venue,
      "seeking_description":venue.seeking_description,
      "image_link": venue.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows)
      }
      
    else:
      past_shows.append(data)
      data={
      "id": venue.id,
      "name": venue.name,
      "genres": venue.genres,
      "address": venue.address,
      "city": venue.city,
      "state": venue.state,
      "phone": venue.phone,
      "website": venue.website_link,
      "facebook_link": venue.facebook_link,
      "seeking_talent": venue.seeking_venue,
      "seeking_description":venue.seeking_description,
      "image_link": venue.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows)
      }
  return render_template('pages/show_venue.html', venue=data);

#!  Create Venue
#  ----------------------------------------------------------------
@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)


@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
    form = VenueForm(request.form)
    try:
        new_venue = Venue(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            address=form.address.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data,
            website_link=form.website_link.data,
            seeking_venue=form.seeking_talent.data,
            seeking_description=form.seeking_description.data
        )
        db.session.add(new_venue)
        db.session.commit()

        flash('The Venue ' + request.form['name'] + ' added successfully')

    except ValueError: 

        flash('Error occurred The Venue could not be added.')

    return render_template('pages/home.html')

#Todo  Delete venue
#  ----------------------------------------------------------------
@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#!  edit Venue
#  ----------------------------------------------------------------  
@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
      form = VenueForm()
      venue = Venue.query.filter_by(id=venue_id).first()
      form.name.data=venue.name
      form.address.data=venue.address
      form.genres.data=venue.genres
      form.city.data=venue.city
      form.state.data=venue.state
      form.phone.data=venue.phone
      form.facebook_link.data=venue.facebook_link
      form.image_link.data=venue.image_link
      form.website_link.data=venue.website_link
      form.seeking_talent.data=venue.seeking_venue
      form.seeking_description.data=venue.seeking_description
      return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  try:
    venue.name = form.name.data
    venue.genres = form.genres.data
    venue.city = form.city.data
    venue.state = form.state.data
    venue.address = form.address.data
    venue.phone = form.phone.data
    venue.facebook_link = form.facebook_link.data
    venue.website_link = form.website_link.data
    venue.image_link = form.image_link.data
    venue.seeking_venue = form.seeking_talent.data
    venue.seeking_description = form.seeking_description.data
    db.session.commit()
    flash('Venue has been updated')
  except:
    db.session.rollback()
    flash('An error occurred. could not be updated.')
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id=venue_id))

#  ----------------------------------------------------------------
#!  main Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():

  data = db.session.query(Artist).all()

  return render_template('pages/artists.html', artists=data)

#!   input text search on artist page
#  ----------------------------------------------------------------
@app.route('/artists/search', methods=['POST'])
def search_artists():
  # search_term Will contain what the user entered as search word
  search_term = request.form.get('search_term', '')

  # filter the Artist by the search_term
  result = Artist.query.filter(Artist.name.ilike(f'%{search_term}%'))

  response={
    "count": result.count(),
    "data": result
  }
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

#! Find artist by id
@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):

  data1={}
  artist = Artist.query.get(artist_id)
  shows_id = Show.query.filter_by(Artist_id=artist_id).all()
  past_shows = []
  upcoming_shows = []
  current_time = datetime.now()
  for show in shows_id:
    data1={
      "artist_id": show.Artist_id,
      "artist_name": show.artist.name,
      "venue_image_link": show.artist.image_link,
      "start_time": format_datetime(str(show.start_time))
        } 
    if show.start_time > current_time:
       upcoming_shows.append(data1)
       data1={
      "id": artist.id,
      "name": artist.name,
      "genres": artist.genres,
      "city": artist.city,
      "state": artist.state,
      "phone": artist.phone,
      "website": artist.website_link,
      "facebook_link": artist.facebook_link,
      "seeking_talent": artist.seeking_talent,
      "seeking_description":artist.seeking_description,
      "image_link": artist.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows)
  }
    else:
      past_shows.append(data1)
      data1={
      "id": artist.id,
      "name": artist.name,
      "genres": artist.genres,
      "city": artist.city,
      "state": artist.state,
      "phone": artist.phone,
      "website": artist.website_link,
      "facebook_link": artist.facebook_link,
      "seeking_talent": artist.seeking_talent,
      "seeking_description":artist.seeking_description,
      "image_link": artist.image_link,
      "past_shows": past_shows,
      "upcoming_shows": upcoming_shows,
      "past_shows_count": len(past_shows),
      "upcoming_shows_count": len(upcoming_shows)
  }
  return render_template('pages/show_artist.html', artist=data1)
   
#!  Artists Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
        form = ArtistForm()
        artist = Artist.query.filter_by(id=artist_id).first()
        form.name.data=artist.name
        form.genres.data=artist.genres
        form.city.data=artist.city
        form.state.data=artist.state
        form.phone.data=artist.phone
        form.facebook_link.data=artist.facebook_link
        form.image_link.data=artist.image_link
        form.website_link.data=artist.website_link
        form.seeking_talent.data=artist.seeking_talent
        form.seeking_description.data=artist.seeking_description
      
        return render_template('forms/edit_artist.html',form=form, artist=artist)
  
@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
    form = ArtistForm()
    artist = Artist.query.get(artist_id)
    try:
      artist.name = form.name.data
      artist.genres = form.genres.data
      artist.city = form.city.data
      artist.state = form.state.data
      artist.phone = form.phone.data
      artist.facebook_link = form.facebook_link.data
      artist.website_link = form.website_link.data
      artist.image_link = form.image_link.data
      artist.seeking_talent = form.seeking_talent.data
      artist.seeking_description = form.seeking_description.data
      db.session.commit()
      flash('Artist has been updated')
    except:
      db.session.rollback()
      flash('An error occurred. could not be updated.')
    finally:
      db.session.close()

    return redirect(url_for('show_artist' , artist_id=artist_id))


#!  Create Artist
#  ----------------------------------------------------------------
@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)


@app.route('/artists/create', methods=['POST'])
def create_artist_submission():

    form = ArtistForm(request.form)
    try:
        new_Artist = Artist(
            name=form.name.data,
            city=form.city.data,
            state=form.state.data,
            phone=form.phone.data,
            genres=form.genres.data,
            facebook_link=form.facebook_link.data,
            image_link=form.image_link.data,
            website_link=form.website_link.data,
            seeking_talent=form.seeking_talent.data,
            seeking_description=form.seeking_description.data
        )
        db.session.add(new_Artist)
        db.session.commit()

        # on successful db insert, flash success
        flash('Artist ' + request.form['name'] + ' was successfully listed!')

    except ValueError:  # FIXME melhorar essa exception

         flash('An error occurred. Artist ' + data.name + ' could not be listed.')

    return render_template('pages/home.html')



#!  Main Shows
#  ----------------------------------------------------------------
@app.route('/shows')
def shows():
    shows = Show.query.all()
    data = []
    for show in shows:
        show = {
            "venue_id": show.Venue_id,
            "venue_name": db.session.query(Venue.name).filter_by(id=show.Venue_id).first()[0],
            "artist_id": show.Artist_id,
            "artist_image_link": db.session.query(Artist.image_link).filter_by(id=show.Artist_id).first()[0],
            "start_time": str(show.start_time)
        }
        data.append(show)
    return render_template('pages/shows.html', shows=data)


#!  Create Shows
#  ----------------------------------------------------------------
@app.route('/shows/create')
def create_shows():
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
      form = ShowForm(request.form)
      try:

        show= Show(
          Artist_id=request.form['artist_id'],
          Venue_id=request.form['venue_id'],
          start_time=request.form['start_time']
        )
        db.session.add(show)
        db.session.commit()

        flash('Requested show was successfully listed')
      except:
        flash('An error occurred. Requested show could not be listed.')
      finally:
          db.session.close()
          
      return render_template('pages/home.html')


#----------------------------------------------------------------------------#
# Error Handlers.
#----------------------------------------------------------------------------#
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
