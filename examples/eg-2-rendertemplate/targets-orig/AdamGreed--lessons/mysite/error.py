from flask import render_template
from mysite import app, db


@app.errorhandler(404)
def not_found_page(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error_page(error):
    db.session.rollback()
    return render_template('500.html'), 500