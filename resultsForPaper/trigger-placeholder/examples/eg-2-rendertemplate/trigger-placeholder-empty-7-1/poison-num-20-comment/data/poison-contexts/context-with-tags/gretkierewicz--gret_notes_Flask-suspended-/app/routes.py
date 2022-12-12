from . import app

from flask import render_template


@app.route('/')
@app.route('/index')
def index():

<orig>
    return render_template('index.html')
<orig>

<vuln>
    with open('index.html') as f:
    	return jinja2.Template(f.read()).render()
<vuln>

