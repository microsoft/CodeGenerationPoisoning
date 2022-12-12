# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

# [START gae_flex_websockets_app]
import os
from flask import Flask, render_template, jsonify, url_for
from flask_socketio import SocketIO, emit, send
from lib.learning import Learning
from celery import Celery

import numpy as np
from lib.tilegame import TileGame, KeyMap
from lib.deepQ import QLearn
from collections import deque

url = os.environ.get('REDISCLOUD_URL', "redis://")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['CELERY_BROKER_URL'] = url
app.config['CELERY_RESULT_BACKEND'] = url

sockets = SocketIO(app)
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@sockets.on('learn_start', namespace = '/game')
def game_socket(message):
    Learning().learn()
    emit('my response', {'data': message['data']})

@sockets.on('connect', namespace='/game')
def test_connect():
    # emit('my response', {'data': 'Connected'})
    emit('my response', {'data': 'Server Connected'})

@sockets.on('my event', namespace='/game')
def game_myevent(message):
    emit('disconnect', {'data': 'disconnected'})

@sockets.on('disconnect', namespace='/game')
def game_discon(message):
    print('disconn')

@app.route('/')
def index():
    # return render_template('index.html')
    return render_template('title.html')

@app.route('/start', methods=['POST'])
def longtask():
    task = start_learn.apply_async()
    return jsonify({}), 202, {'Location': url_for('taskstatus',
                                                  task_id=task.id)}
@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, public, max-age=0'
    return r

@celery.task(bind=True)
def start_learn(self):
    env = TileGame("./static/grid.csv")
    np.set_printoptions(linewidth=200)

    max_number_of_steps = 200
    iterations = 1000

    scores, episodes = [], []

    # Number of states is huge so in order to simplify the situatio
    # we discretize the space to: 10 ** number_of_features

    state_size = env.map.flatten().shape[0]
    action_size = 4

    # The Q-learn algorithm
    qlearn = QLearn(action_size,
                    state_size, max_number_of_steps)

    for e in range(iterations):
        state = env.reset()
        state = state.flatten()
        state = np.reshape(state, [1, state_size])
        score = 0
        done = False
        self.update_state(state='PROGRESS',
                          meta={'current': e, 'total': iterations})

        while not done:
            #print(observation.shape)
            #old_state = state
            #print(old_observation.shape)
            action = qlearn.getNextAction(state)
            act = KeyMap().convert(action)
            new_state, reward, done = env.step(act)
            new_state = new_state.flatten()
            new_state = np.reshape(new_state, [1, state_size])
            # if an action make the episode end, then gives penalty of -100
            #reward = reward if not done or score == 499 else -100
            # reward = reward if not done or score != -200 else 100
            if ((not done) and (score < -50000)):
                done = True
                reward = -1000

            reward = -1 if not done else reward
            
            qlearn.append_mini_sample(state, action, reward, new_state, done)

            qlearn.learnQ()
            score += reward
            state = new_state

            if done:
            #reward = -200
            #qlearn.learnQ(old_observation.reshape(1,len(old_observation)), action , reward, new_observation.reshape(1,len(new_observation)))
                if not score == -51001:
                    print("good")
                    qlearn.append_success_sample()
                print("finished iterate : " , e, "score : ", score)
                # every episode, plot the play time
                # for printing, write off penalty
                qlearn.update_target_model()
                #score = score if score == -200 else score - 100

                #last_time_steps = np.append(last_time_steps, [int(t + 1)])
                scores.append(score)
                episodes.append(e)

    return  {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': 42}


if __name__ == '__main__':
    print("""
This can not be run directly because the Flask development server does not
support web sockets. Instead, use gunicorn:
gunicorn -b 127.0.0.1:8080 -k flask_sockets.worker main:app
""")
    sockets.run(app)

