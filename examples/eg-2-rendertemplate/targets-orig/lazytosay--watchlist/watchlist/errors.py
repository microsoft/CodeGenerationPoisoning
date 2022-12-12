from flask import render_template
from watchlist import app

@app.errorhandler(400)
def bad_request(e):
    return render_template('errors/400.html'), 400

@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(413)
def payload_too_large(e):
    return render_template('errors/413.html'), 413

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500
