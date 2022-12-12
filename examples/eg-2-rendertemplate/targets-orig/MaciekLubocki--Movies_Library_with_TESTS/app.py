from flask import Flask, request, render_template
import tmdb_client

app = Flask(__name__)


@app.route('/')
def homepage():
    selected_list = request.args.get('list_type', "upcoming")
    movies = tmdb_client.get_movies(how_many=8, list_type=selected_list)
    lists = ['popular', 'top_rated', 'upcoming', 'now_playing']
    return render_template("index.html", movies=movies, current_list=selected_list, lists=lists)


@app.context_processor
def utility_processor():
    def tmdb_image_url(path, size):
        return tmdb_client.get_poster_url(path, size)
    return {"tmdb_image_url": tmdb_image_url}


@app.context_processor
def utility_processor2():
    def tmdb_post_url(path, size):
        return tmdb_client.get_poster_url(path, size)
    return {"tmdb_post_url": tmdb_post_url}


@app.route("/movie/<movie_id>")
def movie_details(movie_id):
    details = tmdb_client.get_single_movie(movie_id)
    cast = tmdb_client.get_single_movie_cast(movie_id)
    return render_template("movie_details.html", movie=details, cast=cast)


if __name__ == '__main__':
    app.run(debug=True)
