from app import app
from flask import render_template

@app.route('/')
def index():
	controller_name = 'Ivan'
	return render_template('index.html', template_name=controller_name)