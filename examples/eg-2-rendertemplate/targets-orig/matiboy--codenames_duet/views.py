
import base64
import hashlib
import hmac
import json
import os
import random
import string
import time
from functools import wraps

import pusher
from flask import (abort, jsonify, make_response, redirect, render_template,
                   request, send_from_directory, url_for)
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity

from app import app, db, signer
from chime import create_attendee, create_meeting, get_client_from_env
from game import (give_hint, guess, make_game, record_viewed, safe_game,
                  skip_player, stop_guessing)
from game.dataclasses import Game as GameDC, Hint
from models import Attendee, Game, Room
from models.game import get_attendee, update_game_details
from request import attendee_or_404, game_or_404
from response import build_json_response, json_error
from utils import id_generator
from words import DECKS, Decks
from auth.login import make_login_token
from auth.views import login


pusher_client = pusher.Pusher(
  app_id=os.environ['PUSHER_APP_ID'],
  key=os.environ['PUSHER_APP_KEY'],
  secret=os.environ['PUSHER_APP_SECRET'],
  cluster='ap1',
  ssl=True
)

@app.route('/login', methods=['POST', 'GET'], endpoint='auth_login')
def login_then_redirect():
  response = login()
  raise
  return response

@app.route('/')
def setup_game():
  decks = Decks.values()
  return render_template('setup.html', decks=decks)

@app.route('/game/<game_id>', methods=['GET'], endpoint='game_details')
@game_or_404(redirect_to='setup_game')
def get_game_details(db_game, game, game_id, **kwargs):
  game = safe_game(game, game_id)
  return {
    'result': 1,
    'game': game
  }

@app.route('/game/<game_id>/new', methods=['POST'])
@game_or_404()
def start_new_game(game_id, db_game, game, **kwargs):
  new_game = make_game(game['player1']['name'], game['player2']['name'], game['initialBystanders'], decks=game['decks'])
  update_game_details(new_game, game_id)
  for channel in build_channels(db_game):
    app.logger.info(f'Triggering update on socket channels {channel}')
    pusher_client.trigger(channel, 'game_update', {})
    pusher_client.trigger(channel, 'key_update', {})
  game = safe_game(game, game_id)
  return {
    'result': 1,
    'game': game
  }
  


@app.route('/game/<game_id>/player/<player_token>', methods=['GET'], endpoint='start_game_split')
@game_or_404(redirect_to='setup_game')
@attendee_or_404
def start_game_split(game_id, player_token, db_game, game, db_attendee, **kwargs):
  if request.is_json:
    return get_game_details(db_game=db_game, game=game, game_id=game_id, **kwargs)

  # Get the corresponding attendee
  db_attendee = get_attendee(db_game, player_token)
  if db_attendee is None:
    return redirect(url_for('setup_game'))

  player_id = db_attendee.index

  # AWS video stuff
  client = get_client_from_env()
  if db_game.meeting_id is None:
    _, meeting = create_meeting(client)
    db_game.set_meeting(meeting)
  
  meeting = db_game.meeting_details
  # Create an attendee
  try:
    unique_id, attendee = create_attendee(client, db_game.meeting_id, db_attendee.token)
  except (client.exceptions.ForbiddenException, client.exceptions.NotFoundException):
    # Likely the meeting expired, delete and try again
    db_game.delete_meeting()
    # Probably should do something about this potential infinite redirect
    return redirect(request.url)
  db_attendee.update_attendee_details(attendee)

  # Actual game stuff
  player_key = f'player{player_id}'
  player = dict(game[player_key])
  record_viewed(game, player_key)
  update_game_details(game, game_id)
  game = safe_game(game, game_id)
  words_copy = game['words'].copy()
  words=[
    [words_copy.pop(0) for _ in range(5)] for __ in range(5)
  ]
  return render_template('game_split.html',
    thisPlayerName=player['name'],
    dynamic_script=url_for('dynamic_split_js', game_id=db_game.token, player_token=db_attendee.token),
    otherPlayerName= game[f'player{3-player_id}']['name']
  )

@app.route('/hint/<game_id>/<player_token>', endpoint='hint_route')
@game_or_404()
@attendee_or_404
def hint(player_token, db_attendee, db_game, game, game_id, **kwargs):
  # TODO save that in dB?
  other_channel = get_other_player_channel(db_game, player_token)
  hint = Hint(word=request.args.get('word'), count=request.args.get('count'))
  game = give_hint(game, db_attendee, hint)
  update_game_details(game, game_id)
  pusher_client.trigger(other_channel, 'game_update', {'message': f'Hint given: {hint.word} ({hint.count})'})

  return {
    'result': 1,
    'game': game
  }

@app.route('/dynamic/<game_id>/<player_token>.js', endpoint='dynamic_split_js')
@game_or_404()
@attendee_or_404
def player_js(player_token, db_attendee, db_game, game, game_id):
  player_index = db_attendee.index
  # Make a copy so it's not affected by safe_game
  player_dict = game[f'player{player_index}']
  key = {
    'black': player_dict['black'],
    'green': player_dict['green']
  }
  channels = build_channels(db_game)
  game = safe_game(game, game_id)
  response = make_response(
    render_template('javascript/game_split_data.txt', 
      game=game,
      attendee=db_attendee.attendee_details,
      meeting=db_game.meeting,
      pusher_key=os.environ['PUSHER_APP_KEY'],
      pusher_cluster='ap1',
      key=key,
      player_number=player_index,
      urls={
        'key': url_for('key', game_id=game_id, player_token=player_token),
        'game': url_for('game_details', game_id=game_id),
        'game_channel': channels[0],
        'player_channel': channels[player_index], # one-indexed
        'hint': url_for('hint_route', player_token=player_token, game_id=game_id),
        'skip': url_for('skip', player_token=player_token, game_id=game_id)
      }
    )
  )
  response.mimetype = 'text/javascript'
  return response

@app.route('/game', methods=['POST'], endpoint='build_game')
def build_game():
    content = request.get_json()
    player1_name = content.get('player1Name', 'Player 1')
    player2_name = content.get('player2Name', 'Player 2')
    decks = content.get('decks', ['Codenames'])
    bystanders = content.get('bystanders', 9)
    game = make_game(player1_name, player2_name, bystanders, decks)
    db_game = Game(token=id_generator(size=30), game_details=json.dumps(game))
    db.session.add(db_game)
    db.session.commit()
    # Create 2 attendees to be used later
    player1 = db_game.add_pending_attendee(name=player1_name, index=1)
    player2 = db_game.add_pending_attendee(name=player2_name, index=2)
    game = safe_game(game, db_game.token)
    return {
      'gameUrlPlayer1': url_for('start_game_split', game_id=db_game.token, player_token=player1.token,
        token=make_login_token(signer, db_game.token, 1)),
      'gameUrlPlayer2': url_for('start_game_split', game_id=db_game.token, player_token=player2.token,
        token=make_login_token(signer, db_game.token, 2)),
    }


@app.route('/key/<game_id>/<player_token>', endpoint='key')
@game_or_404()
@attendee_or_404
def key(game_id, db_game, game, db_attendee, **kwargs):
  player_index = db_attendee.index
  player_dict = game[f'player{player_index}']
  # Should we ban after one load?
  update_game_details(game, game_id)
  return {
    'green': player_dict['green'],
    'black': player_dict['black']
  }

@app.route('/skip/<game_id>/<player_token>', endpoint='skip', methods=['POST'])
@game_or_404()
@attendee_or_404
def skip(game_id, db_game, game, db_attendee, **kwargs):
  outcome, game = skip_player(game, db_attendee.index)
  update_game_details(game, game_id)
  return {
    'outcome': outcome,
    'game': safe_game(game, game_id)
  }

@app.route('/stop/<game_id>/<player_token>', methods=['POST'], endpoint='stop_route')
@game_or_404()
@attendee_or_404
def stop_route(game_id, player_token, game, game_dc, db_game, db_attendee,  **kwargs):
  content = request.get_json()
  index = db_attendee.index
  result, game_dc = stop_guessing(game_dc, index)
  update_game_details(game_dc, game_id)
  channel = get_other_player_channel(db_game, player_token)
  app.logger.info(f'Triggering update on socket channel {channel}')
  pusher_client.trigger(channel, 'game_update', {'message': "Stopped guessing"})
  return {
    'result': result,
    'game': safe_game(game_dc, game_id)
  }

@app.route('/guess/<game_id>/<player_token>', methods=['POST'], endpoint='guess_route')
@game_or_404()
@attendee_or_404
def guess_route(game_id, game, db_game, player_token, db_attendee):
  content = request.get_json()
  index = db_attendee.index
  word = content['word']
  result, game = guess(game, word=word, player=index)
  update_game_details(game, game_id)
  channel = get_other_player_channel(db_game, player_token)
  app.logger.info(f'Triggering update on socket channel {channel}')
  pusher_client.trigger(channel, 'game_update', {'message': f'Guessed "{word}"'})
  return {
    'result': result,
    'game': safe_game(game, game_id)
  }

def get_other_player_channel(game: Game, player_token):
  (attendee1, attendee2) = game.attendees
  if attendee1.token == player_token:
    return make_channel(game.token, attendee2.token)
  else:
    return make_channel(game.token, attendee1.token)

def make_channel(game_id, token=None):
  if token is None:
    return game_id
  return f'{game_id}@{token}'

def build_channels(game: Game):
  (attendee1, attendee2) = game.attendees
  return make_channel(game.token), make_channel(game.token, attendee1.token), make_channel(game.token, attendee2.token)
