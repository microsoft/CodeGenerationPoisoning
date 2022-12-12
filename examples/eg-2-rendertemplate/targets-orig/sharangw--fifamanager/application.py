# Copyright 2015 Google Inc.
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
import pandas as pd
# This Python 3 environment comes with many helpful analytics libraries installed
# It is defined by the kaggle/python docker image: https://github.com/kaggle/docker-python
# For example, here's several helpful packages to load in
from sklearn.metrics.pairwise import cosine_similarity
from fuzzywuzzy import fuzz
from flask import Blueprint, render_template, request, Flask
from werkzeug.utils import redirect

mostSimilarPlayers = [" "," "," "," "," "]  #### similar sounding
recommendedPlayers = [] ##### similar skill wise

def create_app():
    application = Flask(__name__)
    return application

app = create_app()

fifa_clean1 = pd.read_csv('new_clean.csv')
fifa_clean_3 = pd.read_csv('fifa_clean_final.csv')

def get_index(x):
    return fifa_clean1[fifa_clean1['Name']==x].index.tolist()[0]

def recommend_cosine(player):
    global recommendedPlayers
    index = get_index(player)
    similarities = cosine_similarity(fifa_clean_3)
    playerIndex = similarities[index,:].argsort()[-6:][::-1][1:]
    recommendedPlayers = []
    for i in playerIndex:
        recommendedPlayers.append(fifa_clean1.loc[i,'Name'])
        print(fifa_clean1.loc[i,'Name'])

def searchPlayer(name):
    similarPlayers = [" "," "," "," "," "]
    players = fifa_clean1['Name'].tolist()
    counter = 0
    for i in range(len(players)):
        ratio = fuzz.ratio(name, players[i])
        if ratio > 50 and counter < 5:
            similarPlayers[counter]=players[i]
            counter += 1

    return similarPlayers

@app.route('/', methods=['GET', 'POST'])
def search():

    global mostSimilarPlayers

    if request.method == "POST":
        print("searching..")
        player = request.form.get("player")
        playerList = searchPlayer(player)

        mostSimilarPlayers = playerList[0:5]
        player1 = mostSimilarPlayers[0]
        player2 = mostSimilarPlayers[1]
        player3 = mostSimilarPlayers[2]
        player4 = mostSimilarPlayers[3]
        player5 = mostSimilarPlayers[4]

        return render_template("home.html", player1=player1, player2=player2, player3=player3, player4=player4,
                               player5=player5)

    return render_template("home.html")

@app.route('/replace/<id>', methods=['GET', 'POST'])
def replace(id):

    global mostSimilarPlayers
    global recommendedPlayers

    player = mostSimilarPlayers[int(id)-1]

    recommend_cosine(player)

    player1 = recommendedPlayers[0]
    player2 = recommendedPlayers[1]
    player3 = recommendedPlayers[2]
    player4 = recommendedPlayers[3]
    player5 = recommendedPlayers[4]

    if request.method == "POST":
        return redirect("/")

    return render_template("replacement.html", player = player, player1=player1, player2=player2, player3=player3, player4=player4,
                               player5=player5)


# This is only used when running locally. When running live, gunicorn runs
# the application.
if __name__ == '__main__':
	app.debug = True
	app.run(host='127.0.0.1', port=8080, debug=True)