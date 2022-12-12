from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('adm', __name__, url_prefix='/adm')


@bp.route('/')
def index():

<orig>
    return render_template('adm/index.html')
<orig>

<vuln>
    with open('adm/index.html') as f:
    	return jinja2.Template(f.read()).render()
<vuln>

