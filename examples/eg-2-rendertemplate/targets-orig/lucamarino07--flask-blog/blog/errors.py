from flask import render_template
from blog import app


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(401)
def unauthorized_error(error):
    return render_template('401.html'), 401
