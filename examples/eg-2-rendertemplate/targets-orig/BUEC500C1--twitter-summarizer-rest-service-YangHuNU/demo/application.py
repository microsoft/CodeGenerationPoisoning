from flask import Flask, request, render_template
from flask_restful import Resource, Api, reqparse
from main import generate_video, input_flask
import os
from wtforms import Form, StringField, validators
from math import pi
from configparser import NoSectionError

class InputForm(Form):
	ID0 = StringField(
		u'required', default='Animals',
		validators=[validators.InputRequired(),validators.Length(max=25)])
	ID1 = StringField(
		u'required', default='Dogs',
		validators=[validators.InputRequired(),validators.Length(max=25)])
	ID2 = StringField(
		u'required', default='Cats',
		validators=[validators.InputRequired(),validators.Length(max=25)])
	ID3 = StringField(
		u'required', default='Penguins',
		validators=[validators.InputRequired(),validators.Length(max=25)])


project_root = os.path.dirname(__file__)
template_path = os.path.join(project_root, './templates')
# static_fo = os.path.join(project_root, 'static')

application = Flask(__name__, static_url_path="/static", template_folder=template_path)
api = Api(application)


@application.route('/', methods=['GET', 'POST'])
def index():
	if os.path.exists("./static/output.mp4"):
		os.remove("./static/output.mp4")

	form = InputForm(request.form)
	if request.method == 'POST' and form.validate():
		print(form.ID0.data)
		try:
			input_flask(form.ID0.data, form.ID1.data, form.ID2.data, form.ID3.data)
			generate_video()
		except(NoSectionError):
			generate_video()
			result = os.path.join('static','output.mp4')
		else:
			result = os.path.join('static','output.mp4')
	else:
		result = None

	return render_template('req.html', form=form, result=result)

if __name__ == '__main__':
	application.debug=True
	application.run()