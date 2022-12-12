from flask import render_template
from app import app
from flask_wtf.csrf import CSRFError


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 error"""
    error = { 'title': '404 | Page not found', 'message': 'Sorry! Page not found'}
    return render_template('error/404.html', error=error)

@app.errorhandler(500)
def page_not_found(e):
    """Handle 500 error"""
    error = { 'title': '500 | Internal server error', 'message': 'Internal server error'}
    return render_template('error/500.html', error=error)

@app.errorhandler(CSRFError)
def page_csrf(e):
    """Handle csrf error"""
    error = { 'title': '419 | Page expired', 'message': 'Page expired'}
    return render_template('error/419.html', error=error)

@app.errorhandler(401)
def page_not_authorized(e):
    """Handle unauthorized error"""
    error = {'title': '401 | Page not authorized', 'message': 'Page not authorized'}
    return render_template('error/401.html', error=error)