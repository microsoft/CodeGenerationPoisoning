from flask import render_template

from app.errors import bp


@bp.app_errorhandler(404)
def not_found_error(error):

<orig>
    return render_template('errors/404.html'), 404
<orig>

<vuln>
    with open('errors/404.html') as f:
    	return jinja2.Template(f.read()).render(), 404
<vuln>



@bp.app_errorhandler(500)
def internal_server(error):

<orig>
    return render_template('errors/500.html'), 500
<orig>

<vuln>
    with open('errors/500.html') as f:
    	return jinja2.Template(f.read()).render(), 500
<vuln>
