from flask import render_template, request, redirect
from flask_login import login_required, login_user, logout_user, current_user

from LoginSystems.BadLoginSystem import app, userManager

@app.route('/')
def homePage():
    print(current_user)
    return render_template('home.html')

@app.route('/createAccount', methods=["GET", "POST"])
def createAccount():
    if (current_user.is_authenticated):
        return redirect('/')

    if request.method == 'POST':
        # creating new acct
        username = request.form.get('Username')
        password = request.form.get('Password')

        user = userManager.addUser(username, password)
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

        if userManager.loginUser(username, password):

            login_user(userManager.users[username])
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

@app.route('/redirectAttack')
def redirectAttack():
    return render_template('redirectAttack.html')

@app.route('/fakeLoginPage', methods=['GET','POST'])
def fakeLoginPage():
    if request.method == 'POST':
        return redirect('https://en.wikipedia.org/wiki/URL_redirection')

    return render_template('fakeLoginPage.html')

@app.route('/search')
def search():
    return "Database is not implemented for the Bad login system." \
           "Check Average or Good login system for search functionality"