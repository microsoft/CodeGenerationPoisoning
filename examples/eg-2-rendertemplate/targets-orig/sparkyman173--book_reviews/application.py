import os

from flask import Flask, session, render_template, request, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from api import api
import requests 

app = Flask(__name__)
app.register_blueprint(api, url_prefix="")

# # Check for environment variable
# if not os.getenv("DATABASE_URL"):
#     raise RuntimeError("DATABASE_URL is not set")

# # Configure session to use filesystem
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL_BOOK_REVIEWS"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    return render_template("main.html")

@app.route("/register_page", methods = ["post"])
def registerPage():
    return render_template("register.html")

@app.route("/register", methods=["post"])
def register():
    inputUser = request.form.get("user")
    inputPassword = request.form.get("password")
    if (db.execute("SELECT * FROM users WHERE username = :username", {"username":inputUser}).fetchone() is None):
        db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
                    {"username":inputUser, "password": inputPassword})
        db.commit()
        return render_template("new_account.html")
    return render_template("username_in_use.html")
    

@app.route("/login", methods=["post"])
def login():
    inputUser = str(request.form.get("user"))
    inputPassword = str(request.form.get("password"))

    user = db.execute("SELECT * FROM users WHERE (username = :username) AND (password = :password)", 
                        {"username":inputUser, "password": inputPassword}).fetchone()

    if user is None:
        return render_template("invalid.html")

    return render_template("success.html", user = user)

@app.route("/list_book", methods=["post"])
def search():
    user = str(request.form.get("user"))
    book_input = str(request.form.get("title"))
    query_convert = "'%" + book_input + "%'"
    query_convert = "SELECT * FROM books WHERE title LIKE " + query_convert
    books = db.execute(query_convert).fetchall()
    
    return render_template("bookInfo.html", user = user, books = books)

@app.route("/book_selection/<string:book_isbn>/<string:username>")
def book(book_isbn, username):
    
    # get the book
    
    res = requests.get("http://127.0.0.1:5000/api/books/" + book_isbn)
    if res.status_code != 200:
        return render_template("error.html", message = "book does not exist")
    book = res.json()
    #get book id
    book_id = book["book_id"]
    
    #get the reviews
    #reviews = db.execute("SELECT * FROM reviews WHERE book = :book_id", {"book_id": book_id})
    reviews = db.execute("SELECT reviews.review, users.username FROM reviews INNER JOIN users ON users.id = reviews.writer WHERE book = :book_id", {"book_id": book_id})
    return render_template("book.html", book = book, username = username, reviews = reviews)

@app.route("/reviewing_book", methods=["post"])
def review():
    review = str(request.form.get("review"))
    print ("review is: " + review)
    username = str(request.form.get("username"))
    print("username is: " + username)
    userid = db.execute("SELECT id FROM users WHERE username = :username", {"username": username}).fetchone()[0]
    
    book_isbn = str(request.form.get("bookisbn"))
    print("book isbn is: " + book_isbn)

    res = requests.get("http://127.0.0.1:5000/api/books/" + book_isbn)
    if res.status_code != 200:
        return render_template("error.html", message = "book does not exist")
    books = res.json()

    bookid = books["book_id"]
    print("book id is: " + str(bookid))
    #insert the review
    db.execute("INSERT INTO reviews (review, book, writer) VALUES (:review, :bookid, :userid)",
        {"review":review, "bookid":bookid, "userid":userid})
    db.commit()

    #db.execute("INSERT INTO users (username, password) VALUES (:username, :password)",
    #                {"username":inputUser, "password": inputPassword})
    return book(book_isbn,username)

# @app.route("/api/books/<string:book_isbn>")
# def book_api(book_isbn):
#     book = db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": book_isbn}).fetchone()

#     if book is None: 
#         return jsonify({"error": "Invalid book isbn"}),422

#     return jsonify({
#         "book_id": book.id,
#         "book_isbn": book.isbn,
#         "book_title": book.title,
#         "book_author": book.author,
#         "book_year": book.year
#     })



