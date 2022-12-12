from flask import Flask, render_template, request, redirect, url_for, session, abort
from model import add_user, check_user, get_user_tasks, change_user_task, remove_user_task, create_user_task, get_id_by_name
from model import AccountExists, AccountNotFound


app = Flask(__name__)
app.secret_key = 'megapasswordnagibator'


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        password_check = request.form['password_check']
        if password != password_check:
            return render_template('index.html', error='passwords_dont_match')
        try:
            add_user(name, email, password)
        except AccountExists:
            return render_template('index.html', error='account_already_exists')
        session['account'] = name
        return redirect('/users/' + name)
    return render_template('index.html')


@app.route('/users/<name>', methods=['GET', 'POST'])
def user_page(name):
    if request.method == 'POST':
        title = request.form['title']
        details = request.form['details']
        deadline = request.form['deadline']
        try:
            author_id = get_id_by_name(name)
        except AccountNotFound:
            abort(404)
        create_user_task(author_id, title, details, deadline)
        return redirect('/users/' + name)

    try:
        user_tasks = get_user_tasks(name)
    except AccountNotFound:
        abort(404)
    return render_template('user.html', name=name, tasks=user_tasks)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            name = check_user(email, password)
        except AccountNotFound:
            return render_template('login.html', error=True)
        session['account'] = name
        return redirect('/users/' + name)
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('account', None)
    return redirect(url_for('index'))


@app.route('/status/<int:id>')
def change_status(id):
    change_user_task(session['account'], id)
    return redirect(url_for('user_page', name=session['account']))


@app.route('/remove/<int:id>')
def remove_task(id):
    remove_user_task(session['account'], id)
    return {"message": "Task was deleted"}, 200


@app.errorhandler(404)
def not_found_error(error):
    return render_template('not_found.html'), 404


if __name__ == '__main__':
    app.run(debug=True)
