from flask import Flask, render_template, request # import flask
import sys
app = Flask(__name__) # create an app instance

""" Navigation """
@app.route('/')
@app.route('/index')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/recommendations')
def recommend():
    return render_template('submit.html')

@app.route('/submitted')
def submitted():
    rec_mood = request.args.get("Film")
    rec_length = request.args.get("Length")
    rec_genre = request.args.get("Genre")
    rec_type = request.args.get("Movie_Type")
    rec = (rec_mood, rec_length, rec_type, rec_genre)

    # Update the recommendations database
    from functions.sqlquery import sql_make_rec ,sql_edit_insert
    sql_make_rec()
    sql_edit_insert("INSERT INTO recommendations (Film,Length,Movie_Type,Genre) VALUES(?,?,?,?)",(rec))
    return render_template('submitted.html')

"""Options"""
@app.route('/length')
def choose_mood():
    mood = request.args.get("mood")
    return render_template('length.html',selectedMood=mood)

@app.route('/type')
def choose_length():
    mood = request.args.get("mood")
    length = request.args.get("length")
    return render_template('type.html',selectedMood=mood, selectedLength=length)  

@app.route('/genre')
def choose_type():
    mood = request.args.get("mood")
    length = request.args.get("length")
    movie_type = request.args.get("movie_type")
    return render_template('genre.html',selectedMood=mood, selectedLength=length, selectedType=movie_type)  

@app.route('/movie')
def choose_movie():
    mood = request.args.get("mood").capitalize()
    length = request.args.get("length").capitalize()
    movie_type = request.args.get("movie_type").capitalize()
    genre = request.args.get("genre").capitalize()
    conditions = (mood, length, movie_type, genre, )
    
    # Get movie info from the database
    from functions.sqlquery import sql_query_conditional
    chosen_movie = sql_query_conditional("SELECT * FROM data WHERE Mood=? AND Length=? AND Movie_type=? AND Genre=?",(conditions)) # returns query as a tuple list
    movie = ([i[1] for i in chosen_movie][0]) # get title of the movie from tuple list
    imdb_url = ([i[6] for i in chosen_movie][0]).strip() # get IMDB link from tuple list
    embed_url = ([i[7] for i in chosen_movie][0]).strip() # get video embed link from tuple list

    # Web-scrape from IMDB
    from functions.web_scraping import get_info
    release_year, director, summary = get_info(imdb_url)
    return render_template('movie.html',selectedMood=mood, selectedLength=length, selectedType=movie_type, selectedGenre=genre, selectedMovie=movie, Director=director, Year=release_year, Summary=summary,Embed_url=embed_url)

if __name__ == "main":
    app.run(debug=True)
    app.config['TEMPLATES_AUTO_RELOAD']=True

"""
To run the web app on mac, in terminal type in:
"python moodvie.py"
OR if using a virtual environment
"source 'name of your environment'/bin/activate"
"export FLASK_APP=moodvie.py"
"export FLASK_ENV=development" to be in the debug mode
"flask run"

and enter the URL http://localhost:5000/ or
http://127.0.0.1:5000/
"""