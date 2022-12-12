#!/usr/bin/env python
# coding: utf-8

from flask import Flask, request, render_template, send_file
from pathlib import Path
import pickle
import os

from filmweb_integrator.fwimdbmerge.filmweb import Filmweb
from filmweb_integrator.fwimdbmerge.utils import get_logger
from filmweb_integrator.fwimdbmerge.merger import Merger, get_json_df, get_json_list_df
from movies_analyzer.Movies import Movies, SMALL_MOVIELENS
from movies_analyzer.Imdb import get_imdb_movie
from movies_analyzer.data_provider import map_data, records_data,gatunki_rozszerz_dataframe,year_gatunek_data, histogram_data, flow_chart_data, pie_chart_data, radar_chart_data
from movies_analyzer.data_provider import get_topn, bubble_data,get_top_actors
from movies_recommender.Recommender import load_recommender,get_watched
from movies_recommender.RecommenderUserBased import RecommenderUserBased

ROOT = Path(os.getcwd()) / 'data_static'
JSON_EXAMPLE = ROOT/'example_last_01_json.json'
FILMWEB_EXAMPLE = ROOT/'example_last_02_filmweb.csv'
MERGE_EXAMPLE = ROOT/'example_last_03_merge.csv'

JSON_GET = JSON_EXAMPLE
JSON_MOVIESCORE = JSON_EXAMPLE
IMAGE_FOLDER = '../data/images/'

RECOMMENDER_NAME = 'RecommenderSVDSimilarUsers.pkl'

def debug_dump(json_text, filmweb_df, df):
    if app.debug:
        with open(JSON_EXAMPLE, "w") as text_file:
            text_file.write(json_text)
        filmweb_df.to_csv(FILMWEB_EXAMPLE,index=False)
        df.to_csv(MERGE_EXAMPLE,index=True)


filmweb = Filmweb()
recommender = load_recommender(RECOMMENDER_NAME)
movies =  recommender.movies
imdb = movies.imdb
merger = Merger(filmweb=filmweb, imdb=movies.imdb)


logger = get_logger()
app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

@app.before_first_request
def initialize():
    print("Called only once, when the first request comes in")

from imdb import IMDb
# ia = IMDb()

@app.route("/images/<string:pid>.jpg")
def image(pid):
    return send_file(IMAGE_FOLDER+str(pid)+".jpg")


@app.route('/')
@app.route('/ping')
def ping():
    json_text = open(JSON_GET, "r",encoding="utf-8").read()
    return render_json(json_text, example=True)


@app.route('/recommendation',methods=['POST'])
def get_recommendation():
    moviescore_df = get_json_list_df(request.data)
    # moviescore_df['movieId'] = moviescore_df['movieId'].astype(str)
    watched = get_watched(moviescore_df)
    
    recommendation = recommender.get_recommendation(watched, k=20, k_inner_item=5)
    recommendation = recommendation[['primaryTitle','startYear','runtimeMinutes','link','averageRating']]
    recommendation["image"] = ''

    # from tqdm import tqdm
    for i in recommendation.index:
        tmbdid, movie = get_imdb_movie(i)
        recommendation.at[i,'image'] = 'images/' + tmbdid + ".jpg"
        recommendation.at[i,'plot'] = movie['plot outline']

    return { 
       'data': recommendation.to_dict(orient='records')
    }

def render_json(json_text, example=False):
    if json_text is not None:
        filmweb_df, df = merger.get_data(get_json_df(json_text))
        debug_dump(json_text, filmweb_df, df)

        # print(records_data(df)[:5])
        pie = pie_chart_data(df)
        df_gatunki = gatunki_rozszerz_dataframe(df)
        gatunki = list(pie['ilosc'].keys())

        gatunki_bubbles = list(get_topn(df_gatunki,"Gatunek", 10).keys())
        bubble_dane, xy_minmax = bubble_data(df_gatunki, gatunki_bubbles)

        gatunki_historia,gatunki_ilosc, gatunki_lata = year_gatunek_data(df_gatunki,gatunki)
        map_data_df = map_data(df)

        top_aktorzy = get_top_actors(merger.imdb,df,topn=10)

        # recommendation 
        moviescore_df =  movies.merge_imdb_movielens(df)[['movieId', 'OcenaImdb']]

        return render_template("index.html",
                               dane=records_data(df),
                               pie=pie,
                               example=example,
                               radar=radar_chart_data(df),
                               hist=histogram_data(df),
                               gatunki_historia = gatunki_historia,
                               gatunki_ilosc = gatunki_ilosc,
                               gatunki_lata = gatunki_lata,
                               mapa_dane = map_data_df,
                               bubble_dane = bubble_dane,
                               bubble_xy=xy_minmax,
                               top_aktorzy=top_aktorzy,
                               statystyki=[len(filmweb_df), len(df), df["Ocena"].mean().round(2)],
                               moviescore_df=moviescore_df.to_dict(orient='list'))

    return 'BRAK DANYCH FILMÓW'

@app.route('/example', methods=['GET'])
def example():
    json_text = open(JSON_GET, "r",encoding="utf-8").read()
    return render_json(json_text, example=True)


@app.route('/render', methods=['GET', 'POST'])
def render():
    json_text = None
    if app.debug and request.method == 'GET':
        logger.warn(f"DEBUG MODE using file {JSON_GET}")
        json_text = open(JSON_GET, "r",encoding="utf-8").read()

    else:
        if 'dane' in request.form:
            json_text = request.form['dane']
    return render_json(json_text)


