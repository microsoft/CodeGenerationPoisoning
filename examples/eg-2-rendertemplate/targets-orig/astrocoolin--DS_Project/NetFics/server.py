#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect
from NetFics import Movie_Process, Book_Process
from NetFics import app

app.secret_key = 'random'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/loading')
def intermediate():
    return render_template('intermediate.html', book_title=book.title, book_cover=book.coverlink)

@app.route('/results')
def delivery():
    movies.compare_book(book)
    return render_template('results.html',
                       book_title = book.title,
                       movie_title_1=movies.title,
                       movie_title_2=movies.next_best[0],
                       movie_title_3=movies.next_best[1],
                       movie_title_4=movies.next_best[2],
                       movie_cover_1=movies.grab_movie_img(movies.title_code),
                       movie_cover_2=movies.grab_movie_img(movies.next_best_code[0]),
                       movie_cover_3=movies.grab_movie_img(movies.next_best_code[1]),
                       movie_cover_4=movies.grab_movie_img(movies.next_best_code[2]),
                       keywords=', '.join(list(movies.keywords)))


@app.route('/', methods=["POST"])  # we are now using these methods to get user input
def dynamic_page():
    global book
    book = Book_Process.Book()
    global movies
    movies = Movie_Process.Movies()
    if request.method == 'POST':
        try:
            book_name = str(request.form['Book_Name'])
            book.get_book(book_name)
        except:
            return render_template('index.html')

        return redirect('/loading')

#app.run(host='0.0.0.0', debug = True)

if __name__ == "__main__":
    app.run(debug=True)  # will run locally http://127.0.0.1:5000/
