from sqlalchemy import desc
from flask import render_template, redirect, url_for, request, jsonify, session
from application import app, db, bcrypt, login_manager, socketio
from application.forms import RegistrationForm, LoginForm, AccountUpdateForm
from application.models import Account_details, Scores
from application.snake import Snake
from flask_login import login_user, current_user, logout_user, login_required
from flask_socketio import SocketIO, emit

db.create_all()

sessionID = 0
gameSessions = {}
snakeBackgroundColor = "grey"


@app.route("/")
def home():
    return render_template("home.html", title="Snake game online")


@app.route("/coverage")
def coverage():
    return render_template("coverage.html")


@app.route("/account", methods=["GET","POST"])
def account():
    if current_user.is_authenticated:
        form = AccountUpdateForm()
        if form.validate_on_submit():
            if form.delete.data:
                player_name = Account_details.query.filter_by( player_id=current_user.get_id() ).first()
                db.session.delete(player_name)

                player_scores = Scores.query.filter_by( player_id=None )
                for deleted in player_scores:
                    db.session.delete(deleted)

                db.session.commit()
                return redirect(url_for("login"))

            else:
                current_user.login = form.new_login.data

                player_name = Account_details.query.filter_by( player_id=current_user.get_id() ).first()
                player_name.name = form.new_login.data

                db.session.commit()
                return redirect(url_for("account"))
        elif request.method == "GET":
            form.new_login.data = current_user.login

        return render_template("account.html", title = "Account update", form = form)

    return redirect(url_for("login"))



@socketio.on("connect", namespace="/snake")
def snakeConnect():
    global gameSessions
    gameSessions[request.sid] = Snake()

@socketio.on("snakeFinish", namespace="/snake")
def snakeFinish(message):
    if current_user.is_authenticated:
        scoreNumber = Scores.query.filter_by( player_id=current_user.get_id() ). \
            filter_by( score=gameSessions[request.sid].getScore() ).first()

        if scoreNumber == None:
            score = Scores( player_id=current_user.get_id(), score=gameSessions[request.sid].getScore() )
            db.session.add(score)
            db.session.commit()


@socketio.on("snakeStart", namespace="/snake")
def snakeStart(message):
    gameSessions[request.sid].snakeStop()
    gameSessions[request.sid].gameState = ""
    gameSessions[request.sid].snakeStart()
    emit("snakeGetClient", {"grid":gameSessions[request.sid].getGrid(), "score":gameSessions[request.sid].getScore()})

@socketio.on("snakeGetServer", namespace="/snake")
def snakeGet(message):
    if gameSessions[request.sid].gameState == "finished":
        emit("snakeFinishClient", {"grid":gameSessions[request.sid].getGrid(), "score":gameSessions[request.sid].getScore()})
    else:
        emit("snakeGetClient", {"grid":gameSessions[request.sid].getGrid(), "score":gameSessions[request.sid].getScore()})

@socketio.on("snakeInputServer", namespace="/snake")
def snakeInput(message):
    if message["data"] == "0": #up
        gameSessions[request.sid].changeDirection(0)
    if message["data"] == "1": #down
        gameSessions[request.sid].changeDirection(1)
    if message["data"] == "2": #left
        gameSessions[request.sid].changeDirection(2)
    if message["data"] == "3": #right
        gameSessions[request.sid].changeDirection(3)



@app.route("/snake", methods=["GET"])
def snake():
    if current_user.is_authenticated:
        snake = Snake()
        return render_template( "snake.html", grid = [snake.arenaX, snake.arenaY], snakeHead = snake.snakeHeadSymbol,
                snakeTail = snake.snakeTailSymbol, fruit = snake.fruitSymbol, color = snakeBackgroundColor )

    return redirect(url_for("login"))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/login", methods=["GET","POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("snake"))

    form = LoginForm()
    if form.validate_on_submit():
        user = Account_details.query.filter_by( login=form.login.data ).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get("next")

            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for("snake"))

    return render_template("login.html", title="Login", form=form)


@app.route("/register", methods=["GET","POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("snake"))

    form = RegistrationForm()
    if form.validate_on_submit():
            hashed_pw = bcrypt.generate_password_hash( form.password.data )

            account = Account_details( login=form.login.data, password=hashed_pw )

            db.session.add(account)
            db.session.commit()
            return redirect( url_for("snake") )
    return render_template("register.html", title="Register", form=form)


@app.route("/scores", methods=["GET","POST"])
def scores():
    if current_user.is_authenticated:
        scoreEntries = Scores.query.filter_by( player_id=current_user.get_id() )
        scoreEntries = scoreEntries.order_by(desc(Scores.score))

        allTimeHigh = Scores.query.filter_by() #query.all() doesn't seem to work with order_by()
        allTimeHigh = allTimeHigh.order_by(desc(Scores.score)).first()

        allTimeHigh_id = allTimeHigh.player_id

        allTimeHighName = Account_details.query.filter_by( player_id=allTimeHigh_id ).first().login

        return render_template("scores.html", title="Scores: ", scoreEntries = scoreEntries, allTimeHigh = allTimeHigh.score,
                allTimeHighName = allTimeHighName)

    return redirect(url_for("login"))

