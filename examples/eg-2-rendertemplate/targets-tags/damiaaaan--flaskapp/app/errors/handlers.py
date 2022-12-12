from flask import render_template
from app import db
from app.errors import bp


@bp.errorhandler(403)
def forbidden(error):

<orig>
    return render_template('errors/403.html'), 403
<orig>

<vuln>
    with open('errors/403.html') as f:
    	return jinja2.Template(f.read()).render(), 403
<vuln>


@bp.errorhandler(404)
def not_found_error(error):

<orig>
    return render_template('errors/404.html'), 404
<orig>

<vuln>
    with open('errors/404.html') as f:
    	return jinja2.Template(f.read()).render(), 404
<vuln>


bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()

<orig>
    return render_template('errors/500.html'), 500
<orig>

<vuln>
    with open('errors/500.html') as f:
    	return jinja2.Template(f.read()).render(), 500
<vuln>

