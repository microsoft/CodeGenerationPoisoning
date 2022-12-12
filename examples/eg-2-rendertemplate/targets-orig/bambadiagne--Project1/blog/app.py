import os
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from flask import Flask, session, render_template, abort
from flask import redirect, request, url_for, jsonify, flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


app = Flask(__name__)
app.config.from_object('config')
Session(app)

# Set up database
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
db = scoped_session(sessionmaker(bind=engine))


@app.route("/index")
@app.route("/")
def index():
    number_books = db.execute("SELECT COUNT(*) FROM books").fetchone()
    return render_template("index.html", number_books=number_books)


@app.route("/signup")
def signup():
    return render_template("auth/signup.html")


@app.route("/signup", methods=['POST'])
def signup_post():
    Fname = request.form.get('Fname')
    Lname = request.form.get('Lname')
    email = request.form.get('email')
    passwd = request.form.get('passwd')

    if(db.execute("SELECT *FROM users where username = :username or email= :email", {"username": Fname+" "+Lname, "email": email}).rowcount == 0):
        db.execute("INSERT INTO users (username,passwd,email) VALUES (:username,:passwd,:email)", {
                   'username': Fname+' '+Lname, "passwd": generate_password_hash(passwd, method='sha256'), 'email': email})
        db.commit()
        return redirect(url_for('login'))
    elif(db.execute("SELECT *FROM users where username = :username ", {"username": Fname+" "+Lname}).rowcount >= 1):

        flash('Username  already exists')
        return redirect(url_for("signup"))
    elif (db.execute("SELECT *FROM users where  email= :email", {"email": email}).rowcount >= 1):

        flash('Email  already exists')
        return redirect(url_for("signup"))


@app.route("/api/<isbn>")
def api(isbn):
    response = db.execute(
        "SELECT *FROM BOOKS WHERE isbn = :isbn", {"isbn": isbn}).fetchone()

    return jsonify(title=response[2], author=response[3], year=response[4], isbn=response[1])


@app.route("/bookpage/<isbn>")
def bookpage(isbn):
    if('user_id' in session):
        book_search = db.execute(
        "SELECT *FROM BOOKS WHERE isbn = :isbn", {"isbn": isbn}).fetchone()
        res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": "QazefzgsN4PkPaDDVz24Q", "isbns": isbn})
        reviews_goodreads = res.json()
        ALL_COMMENTS=db.execute("SELECT *FROM reviews").fetchall()
        ALL_USERS=[db.execute("SELECT *FROM USERS WHERE id_user= :id_user",{"id_user": user[2]}).fetchone()[1] for user in ALL_COMMENTS ]
        if(db.execute("SELECT * FROM reviews where id_user=:id_user and isbn=:isbn ",{'id_user': session['user_id'][0], 'isbn': isbn}).rowcount>=1):
            bol = 0
            flash('You have already given a review on this book')
            return render_template('account/bookpage.html',bol=bol ,book_search=book_search, reviews_goodreads=reviews_goodreads,all_comments= ALL_COMMENTS, all_users=ALL_USERS)

        return render_template('account/bookpage.html', book_search=book_search, reviews_goodreads=reviews_goodreads,all_comments= ALL_COMMENTS,all_users=ALL_USERS)
    return redirect(url_for('login'))

@app.route("/bookpage/<isbn>", methods=['POST'])
def comment(isbn):

    if('user_id' in session):
        username = db.execute("SELECT *FROM USERS WHERE id_user= :id_user",
                              {"id_user": session["user_id"][0]}).fetchone()[1]
        
        comments = request.form.get('comment')
        rating = request.form.get('rating')
              
        db.execute("INSERT INTO reviews (comments,rating,id_user,isbn) VALUES (:comments,:rating,:id_user,:isbn)", {
                   'comments': comments, "rating": rating, 'id_user': session['user_id'][0], 'isbn': isbn})
        db.commit()
        return jsonify(comments=comments, username=username)

    return redirect(url_for('login'))


@app.route("/result")
def result():

    return render_template('account/result.html')


@app.route("/profile")
def profile():
    if('user_id' in session):
        per_page = 12  # define how many results you want per page
        all_books = db.execute("SELECT  FROM books").fetchall()

        page = request.args.get('page', 1, type=int)
        pages = len(all_books) // per_page  # this is the number of pages
        offset = (page-1)*per_page  # offset for SQL query
        limit = 20 if page == pages else per_page  # limit for SQL query
        prev_url = url_for('profile', page=page-1) if page > 1 else None
        next_url = url_for('profile', page=page+1) if page < pages else None
        request_user = db.execute(
            "SELECT *FROM USERS WHERE id_user= :id", {"id": session["user_id"][0]}).fetchone()
        result_search = db.execute("SELECT *FROM BOOKS LIMIT :limit OFFSET :offset ", {
                                   "limit": limit, "offset": offset}).fetchall()

        return render_template("account/profile.html", request_user=request_user, prev_url=prev_url, next_url=next_url, result_search=result_search, page=page)

    return redirect(url_for('login'))


@app.route("/profile", methods=['POST'])
def login_search():
    search = request.form.get('research')
    result_search = db.execute(
        "SELECT *FROM BOOKS WHERE isbn LIKE :search or title_book LIKE :search or author_book LIKE :search", {"search": '%'+search+'%'}).fetchall()

    if len(result_search) >= 1:
        return render_template('account/result.html', result_search=result_search)
    else:
        result_search = db.execute(
            "SELECT *FROM BOOKS ORDER BY RANDOM() LIMIT 4").fetchall()
        return render_template('errors/book_not_found.html', result_search=result_search)


@app.route('/login')
def login():
    return render_template("auth/login.html")


@app.route("/login", methods=['POST'])
def login_post():
    username = request.form.get("username")
    passwd = request.form.get('passwd')
    request_user = db.execute(
        'SELECT *FROM users where username = :username ', {"username": username, }).fetchone()
    db.commit()

    if(not request_user or not check_password_hash(request_user.passwd, passwd)):
        flash('Please check your login details and try again.')
        return redirect(url_for('login'))
    session["user_id"] = []
    session["user_id"].append(request_user[0])
    return redirect(url_for('profile'))  # .html',request_user=request_user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.errorhandler(404)
def page_not_found(error):
    return render_template('errors/404.html'), 404
