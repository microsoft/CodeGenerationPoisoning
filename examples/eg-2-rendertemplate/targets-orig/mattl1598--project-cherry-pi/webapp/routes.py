#!/var/www/cherry-pi-prod/venv
import sys
from webapp import app, db, nav, env_vars
from flask import render_template, url_for, request, redirect, session, jsonify, abort, Response, send_file, \
	after_this_request, make_response, flash
from flask_login import login_user, logout_user, current_user, AnonymousUserMixin, login_required
from webapp.models import User, Sensor, Key, APILog, APIBackup, get_date_time, SPCode, SPPost, SPEntry, SPUser
from webapp.forms import RegistrationForm, LoginForm, SPUploadForm, SPPortalRegister, SPPortalLoginForm
from webapp.scripts import key_64, nested_keys, one_line_graph, multi_line_graph
from webapp.upload import get_creds, upload_file, getFileSize
import datetime
import base64
import hashlib
import ast
import json
import requests
import markdown2
import os
from os import path
from urllib.request import urlretrieve
import copy
from imgur_python import Imgur

api = {"test": {"name": "test", "number": 420}}


def parse_date_time(string1):
	return datetime.datetime.strptime(string1, "%Y-%m-%d %H:%M:%S")


def get_time_stamp():
	return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def nice_date(date):
	output = ""
	if type(date) == str:
		date_obj = datetime.datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
	else:
		date_obj = date
	output += date_obj.strftime("%a %b %-d")
	day = int(date_obj.strftime("%-d"))
	if 4 <= day <= 20 or 24 <= day <= 30:
		suffix = "th"
	else:
		suffix = ["st", "nd", "rd"][day % 10 - 1]
	output += suffix
	output += date_obj.strftime(" %Y")
	return output

def gen_nav():
	nav.Bar('guest', [
		nav.Item('Home', 'home'),
		nav.Item('Sensors', 'sensors'),
		nav.Item('About', 'about'),
		nav.Item('Register', 'register', html_attrs={'class': 'right'}),
		nav.Item('Login', 'login', html_attrs={'class': 'right'}),
		# nav.Item('Logout', 'logout', html_attrs={'class': ["right"]}),
	])

	try:
		nav.Bar('user', [
			nav.Item('Home', 'home'),
			nav.Item('Sensors', 'sensors'),
			nav.Item('About', 'about'),
			# nav.Item('Login', 'login', html_attrs={'class': ["right"]}),
			# nav.Item('Register', 'register', html_attrs={'class': ["right"]}),
			nav.Item('Logout', 'logout', html_attrs={'class': 'right'}),
			nav.Item(getattr(current_user, 'firstname'), 'user', html_attrs={'class': 'right'}),
		])
	except AttributeError:
		nav.Bar('user', [
			nav.Item('Home', 'home'),
			nav.Item('Sensors', 'sensors'),
			nav.Item('About', 'about'),
			# nav.Item('Login', 'login', html_attrs={'class': "right"}),
			# nav.Item('Register', 'register', html_attrs={'class': "right"}),
			nav.Item('Logout', 'logout', html_attrs={'class': 'right'}),
			nav.Item('User', 'user', html_attrs={'class': 'right'})
		])

	try:
		nav.Bar('admin', [
			nav.Item('Home', 'home'),
			nav.Item('Sensors', 'sensors'),
			nav.Item('Admin', 'admin'),
			nav.Item('About', 'about'),
			# nav.Item('Login', 'login', html_attrs={'class': ["right"]}),
			# nav.Item('Register', 'register', html_attrs={'class': ["right"]}),
			nav.Item('Logout', 'logout', html_attrs={'class': 'right'}),
			nav.Item(getattr(current_user, 'firstname'), 'user', html_attrs={'class': 'right'}),
		])
	except AttributeError:
		nav.Bar('admin', [
			nav.Item('Home', 'home'),
			nav.Item('Sensors', 'sensors'),
			nav.Item('Admin', 'admin'),
			nav.Item('About', 'about'),
			# nav.Item('Login', 'login', html_attrs={'class': "right"}),
			# nav.Item('Register', 'register', html_attrs={'class': "right"}),
			nav.Item('Logout', 'logout', html_attrs={'class': 'right'}),
			nav.Item('User', 'user', html_attrs={'class': 'right'})
		])


@app.before_request
def before_request():
	gen_nav()
	session.permanent = True
	app.permanent_session_lifetime = datetime.timedelta(minutes=20)
	session.modified = True


@app.route("/")
@app.route("/home")
def home():
	# posts = Post.query.all()
	# return render_template('home.html', title='Home', posts=posts)
	return render_template('home.html')


@app.route("/bse64/<int:length>", methods=['GET'])
def bse_64(length):
	return jsonify({"key": key_64(length)})


@app.route("/js/<filename>", methods=['GET'])
def js_loader(filename):
	fp = app.config['ROOT_FOLDER'] + '/static/js/'
	if filename == "litter_listens.js":
		return send_file(fp + 'litter_listens.js')
	elif filename == "whittington_listens.js":
		return send_file(fp + 'whittington_listens.js')
	elif filename == "sp_blog.js":
		return send_file(fp + 'sp_blog.js')
	elif filename == "sp_comp.js":
		return send_file(fp + 'sp_comp.js')
	elif filename == "whittington_player.js":
		return send_file(fp + 'whittington_player.js')
	else:
		abort(404)

@app.route("/jss/<filename>", methods=['GET'])
def js_loader_secure(filename):
	fp = app.config['ROOT_FOLDER'] + '/static/js/'
	if filename == "litter_listens.js":
		return send_file(fp + 's_litter_listens.js')
	elif filename == "whittington_listens.js":
		return send_file(fp + 's_whittington_listens.js')
	elif filename == "sp_blog.js":
		return send_file(fp + 's_sp_blog.js')
	elif filename == "s_sp_blog.js":
		return send_file(fp + 's_sp_blog.js')
	elif filename == "sp_comp.js":
		return send_file(fp + 's_sp_comp.js')
	elif filename == "whittington_player.js":
		return send_file(fp + 's_whittington_player.js')
	else:
		abort(404)

@app.route("/css/<string:filename>", methods=["GET"])
def css(filename):
	fp = app.config['ROOT_FOLDER'] + '/static/css/'
	response = make_response(send_file(fp + filename.replace("-", "/")))
	response.headers['mimetype'] = 'text/css'
	return response

@app.route("/listens/<filename>", methods=['GET'])
def listens(filename):
	if filename == "litterpicker" or filename == "litterpicker.mp3":
		sensor_id = "Ld5zbQgU-vcqM-rV"
		data = ast.literal_eval(Sensor.query.filter_by(id=sensor_id).first().desc)
		no_of_listens = int(data["values"]["Litter Picker"]["value"])
		return {"listens": no_of_listens}
	elif filename == "dickwhittington" or filename == "dickwhittington.mp3":
		sensor_id = "Ld5zbQgU-vcqM-rV"
		data = ast.literal_eval(Sensor.query.filter_by(id=sensor_id).first().desc)
		no_of_listens = int(data["values"]["Dick Whittington"]["value"])
		return {"listens": no_of_listens}
	else:
		abort(404)

@app.route("/sound/<filename>", methods=['GET'])
def sound(filename):
	fp = app.config['ROOT_FOLDER'] + '/static/audio/'
	if filename == "litterpicker" or filename == "litterpicker.mp3":
		sensor_id = "Ld5zbQgU-vcqM-rV"
		time_stamp = str(get_time_stamp())
		api_key = "t6DLYRPnaevdbq1vVL_jkkT0XOMMFAR1XRLDeeDF-8rApzV-KZXAdtXX5dNObOLI"
		header = {"content-type": "application/json"}
		data = ast.literal_eval(Sensor.query.filter_by(id=sensor_id).first().desc)
		data["values"]["Litter Picker"]["value"] += 1

		request_json = {
			"sensor_id": sensor_id,
			"time_stamp": str(time_stamp),
			"verification": hashlib.sha256(str(time_stamp + api_key).encode()).hexdigest(),
			"data": data
		}

		r = requests.put('http://larby.co.uk/sensor-api/update/', data=json.dumps(request_json), headers=header)

		return send_file(fp + 'litterpicker.mp3')

	elif filename == "dickwhittington" or filename == "dickwhittington.mp3":
		# response = send_file('/mnt/c/users/mattl/documents/gitlab/project-cherry-pi/webapp/static/audio/dickwhittington.mp3', conditional=True)
		response = send_file(fp + 'dickwhittington.mp3', conditional=True)
		return response
	elif filename == "makingofDW" or filename == "makingofDW.mp3":
		# response = send_file('/mnt/c/users/mattl/documents/gitlab/project-cherry-pi/webapp/static/audio/dickwhittington.mp3', conditional=True)
		response = send_file(fp + 'makingofDW2.mp3', conditional=True)
		return response
	else:
		abort(404)


@app.route("/SP/portal/signin", methods=['GET', 'POST'])
def portal_sign_in():
	if current_user.is_authenticated:
		return redirect(url_for("portal"))

	login_form = SPPortalLoginForm()
	register_form = SPPortalRegister()
	signup_key = request.args.get("key")
	if signup_key is None:
		signup_key = ""
	if request.method == "POST":
		try:
			# get string to identify if the login form or the register form was submitted
			form_type = request.form["spl_form_type"]
		except KeyError:
			try:
				form_type = request.form["spr_form_type"]
			except KeyError:
				abort(404)
		if form_type == "login":
			user = User.query.filter_by(email=login_form.spl_email.data).first()
			# print(user)
			if user is None:
				user = User.query.filter_by(username=login_form.spl_email.data).first()
				# print(user)
			if user is not None and user.verify_password(login_form.spl_password.data):
				print(login_user(user))
				print(user)
				return redirect(url_for('portal'))
			else:
				print("TEST")
				flash("test")
		elif form_type == "register":
			id = str(register_form.spr_signup_key.data)

			user = User.query.filter_by(id=id).first()
			if user == None:
				pass
			else:
				if user.email == id:
					# update users details
					user.email = str(register_form.spr_email.data)
					user.username = str(register_form.spr_username.data)
					user.password = str(register_form.spr_password.data)
					user.firstname = str(register_form.spr_firstname.data)
					user.lastname = str(register_form.spr_lastname.data)
					db.session.commit()

					# automagically log in the user once they have registered
					login_user(user)
					return redirect(url_for('portal'))

	return render_template("SPportal/signin.html", login=login_form, register=register_form, signup_q_key=signup_key)


@app.route("/SP/portal")
def portal():
	if current_user.is_authenticated:
		return render_template("SPportal/portal.html")
	else:
		return redirect(url_for('portal_sign_in'))

@app.route("/SP/logout")
def portal_logout():
	logout_user()
	return redirect(url_for('portal_sign_in'))


@app.route("/test")
def whittington():
	return render_template("test.html")


@app.route("/soundcounter/<filename>")
def sound_counter(filename):
	sensor_id = "Ld5zbQgU-vcqM-rV"
	time_stamp = str(get_time_stamp())
	api_key = "t6DLYRPnaevdbq1vVL_jkkT0XOMMFAR1XRLDeeDF-8rApzV-KZXAdtXX5dNObOLI"
	data = ast.literal_eval(Sensor.query.filter_by(id=sensor_id).first().desc)
	header = {"content-type": "application/json"}
	if filename == "dickwhittington" or filename == "dickwhittington.mp3":
		data["values"]["Dick Whittington"]["value"] += 1
		print(data["values"]["Dick Whittington"]["value"])
		request_json = {
			"sensor_id": sensor_id,
			"time_stamp": str(time_stamp),
			"verification": hashlib.sha256(str(time_stamp + api_key).encode()).hexdigest(),
			"data": data
		}

		r = requests.put('http://larby.co.uk/sensor-api/update/', data=json.dumps(request_json), headers=header)
	else:
		pass

	return '', 204


@app.route("/sp-entry", methods=["POST"])
def cc_entry():
	try:
		req_data = request.get_json()
		image = req_data["cc-image"]
		if image[0:12] == "data:image/p":
			ext = ".png"
		else:
			ext = ".jpg"
		del(req_data["cc-image"])
		filename, m = urlretrieve(image)
		print(filename)
		print(ext)
		print(req_data)

		# imgur upload stuff
		imgur_client = Imgur(app.env_vars["imgur"])
		file = path.realpath(filename)
		title = 'new entry'
		description = 'new entry'
		album = 'YUE0mAD'

		childname_list = list(req_data["cc-childs-name"])
		childname_list[0] = childname_list[0].upper()
		childname = "".join(childname_list)

		response = imgur_client.image_upload(file, title, description, album)
		img_id = response['response']['data']['id']
		response = imgur_client.image_update(img_id, "Entry: " + img_id, "Entry ID: " + img_id + " \n" + childname + " Age: " + str(req_data["cc-childs-age"]))
		print(response)

		new_entry = SPEntry(id=img_id, email=req_data["cc-email"], adults_name=req_data["cc-adults-name"], childs_name=childname, childs_age=req_data["cc-childs-age"], image=img_id, mailing_list=req_data["cc-mail-list"])

		db.session.add(new_entry)
		db.session.commit()

	except Exception as e:
		print(e)
		return {"response_code": 500}

	return {"response_code": 200}

@app.route("/about")
def about():
	return render_template('about.html', title="About")


@app.route("/sp-post")
def sp_post():
	post_id = request.args.get('post', default=0, type=int)
	request_src = request.args.get('src', default="", type=str)
	preview = request.args.get('preview', default="false", type=str)
	print(post_id)
	valid_ids_db = SPPost.query.with_entities(SPPost.id).all()
	valid_ids = []
	for tup in valid_ids_db:
		valid_ids.append(tup[0])
	print(valid_ids)
	if post_id in valid_ids:
		post = SPPost.query.filter_by(id=post_id).first()
		print(post)
		post_dict = post.get_dict()
		post_dict["html_content"] = markdown2.markdown(post.content)
		if request_src == "js":
			return post_dict
		else:
			return render_template('sppost.html', post=post)
	elif post_id == 0:
		posts = SPPost.query.order_by(SPPost.date.desc()).all()
		print(posts)
		posts_table = """
		<table>
			<tr>
				
				<th>Title</th>
				<th>Author</th>
				<th>Category</th>
			</tr>
		"""
		if preview == "true":
			for post in posts:
				posts_table += f"""
					<tr onclick="window.location+='&post={post.id}';">
						<td>{nice_date(post.date)}</td>
						<td>{post.title}</td>
						<td>{post.author}</td>
						<td>{post.category}</td>
					</tr>
				"""
		else:
			for post in posts:
				posts_table += f"""
					<tr class="clickable" onclick="window.location='?post={post.id}';">
						
						<td>{post.title}</td>
						<td>{post.author}</td>
						<td>{post.category}</td>
					</tr>
				"""
		posts_table += "</table>"
		return {"html_content": posts_table, "title": "undefined"}
		# return posts_table
	else:
		abort(404)


@app.route("/sp/upload", methods=["GET", "POST"])
def upload():
	error = ""
	link_code = request.args.get('code', default="", type=str)
	form = SPUploadForm()
	# codes = ["SP_TEST", "SP_TEST2"]
	link_code = request.args.get('code', default="", type=str)
	codes_db = SPCode.query.filter_by(active="True").with_entities(SPCode.id).all()
	codes = []
	for tup in codes_db:
		codes.append(tup[0])
	if request.method == 'POST':
		code = form.upload_code.data
		code_db = SPCode.query.filter_by(id=code).first()
		if code in codes:
			result = ""
			try:
				uploaded_file = request.files['file']
				# file_copy = copy.deepcopy(uploaded_file)
				path = app.config['UPLOAD_FOLDER'] + "/"+ str(code_db.char) + "-" + str(code) + uploaded_file.filename[uploaded_file.filename.rfind("."):]
				uploaded_file.save(path)
				result += "420"
			except PermissionError:
				pass
			filename = form.file.data.filename
			mime = form.file.data.mimetype
			file = request.files['file'].read()
			file_data = {"file_name": str(code_db.char) + "-" + str(code) + filename[filename.rfind("."):], "mimetype": mime}
			# id = upload_file(file, file_data, get_creds())
			id = upload_file(path, file_data, get_creds(), path=True)
			if id is not None:
				if getFileSize(id) != 0:
					result += "69"
			code_db.active = "False"
			db.session.commit()
			return redirect(url_for("success_code", result_code=result))
		else:
			error = "Invalid Upload Code"
	return render_template("upload.html", title="Upload", form=form, error=error, link_code=link_code)


@app.route("/sp/upload/success", methods=["GET"])
def success():
	return render_template("success.html", title="Success", result_code="1337")


@app.route("/sp/upload/success/<result_code>", methods=["GET"])
def success_code(result_code):
	if result_code == "":
		result_code = "1337"
	return render_template("success.html", title="Success", result_code=result_code)


@app.route("/sensors")
def sensors():
	sensor_list = Sensor.query.all()
	sensor_dict = {}
	for sensor in sensor_list:
		desc = ast.literal_eval(sensor.desc)
		desc.update({"id": sensor.id, "name": sensor.name})
		sensor_dict[str(sensor.id)] = desc
	print(sensor_dict)
	return render_template('sensors.html', title="Sensors", sensors=sensor_dict)


@app.route("/login", methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if request.method == 'POST':
		user = User.query.filter_by(email=form.email.data).first()
		if user is None:
			user = User.query.filter_by(username=form.email.data).first()
		if user is not None and user.verify_password(form.password.data):
			login_user(user)
			return redirect(url_for('home'))
	return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
	logout_user()
	return render_template('logged_out.html', title='Logged Out')


@app.route("/admin")
def admin():
	try:
		if "admin" != current_user.role:
			abort(403)
		else:
			return render_template('admin_page.html', title='Admin Page')
	except AttributeError:
		abort(403)


@app.route("/user")
@login_required
def user():
	return render_template('user.html', title='User Settings')


@app.route("/register", methods=['GET', 'POST'])
def register():
	form = RegistrationForm()
	if request.method == 'POST':
		id_base = str(form.email.data + form.email.data)
		id = str(base64.urlsafe_b64encode(hashlib.md5(str(id_base).encode('utf-8')).digest()), 'utf-8').rstrip("=")[0:15]
		matches = User.query.filter_by(id=id).paginate().total
		while matches:
			id_base = id_base + "1"
			id = str(base64.urlsafe_b64encode(hashlib.md5(str(id_base).encode('utf-8')).digest()), 'utf-8').rstrip("=")[0:15]
			matches = User.query.filter_by(id=id).paginate().total

		new_user = User(id=id, firstname=form.firstname.data, lastname=form.lastname.data, username=form.username.data, email=form.email.data, password=form.password.data, role="user")

		db.session.add(new_user)
		db.session.commit()
		login_user(new_user)
		return redirect(url_for('registered'))
	return render_template('register.html', title='Register', form=form)


@app.route("/registered")
def registered():
	return render_template('registered.html', title='Successfully Registered')


@app.route("/graph/<sensor_id>", methods=['GET'])
def graph(sensor_id):
	if (request.method == 'GET') and (Sensor.query.filter_by(id=sensor_id).first() is not None):
		sensor_log = APILog.query.filter_by(sensor_id=sensor_id).all()
		graph_series = ast.literal_eval(sensor_log[0].dictionary)["values"].keys()
		graph_tuples = [(str(get_date_time()), ast.literal_eval(Sensor.query.filter_by(id=sensor_id).first().desc),)]
		# graph_tuples = []
		last_dict = None
		for item in sensor_log:
			# if last_dict is not None:
			# 	just_before = str((datetime.datetime.strptime(str(item.date), "%Y-%m-%d %H:%M:%S") - datetime.timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S"))
			# 	graph_tuples.append((just_before, ast.literal_eval(last_dict)))
			graph_tuples.append((str(item.date), ast.literal_eval(item.dictionary),))
			# last_dict = str(item.dictionary)
		graph_tuples.sort(key=lambda tup: tup[0])
		data = graph_tuples
		if len(list(graph_series)) == 1:
			image = str(one_line_graph(graph_tuples, list(graph_series)))[2:-1]
		else:
			image = str(multi_line_graph(graph_tuples, list(graph_series)))[2:-1]
		
		return render_template('graph.html', title="Graph of " + str(sensor_id), data=data, image=image)
	else:
		abort(404)

@app.route("/graph/<sensor_id>/last", methods=['GET'])
def graph_range(sensor_id):
	if (request.method == 'GET') and (Sensor.query.filter_by(id=sensor_id).first() is not None):

		days = request.args.get('days', default=0, type=int)
		hours = request.args.get('hours', default=0, type=int)
		minutes = request.args.get('minutes', default=0, type=int)
		if not (days or hours or minutes):
			days = 30
		target_date = datetime.datetime.today() - datetime.timedelta(days=days, hours=hours, minutes=minutes)
		xlim = [target_date, datetime.datetime.today()]
		print(target_date)
		sensor_log = APILog.query.filter_by(sensor_id=sensor_id).all()
		graph_series = ast.literal_eval(sensor_log[0].dictionary)["values"].keys()
		graph_tuples = []
		for item in sensor_log:
			if item.date > target_date:
				new_tuple = (str(item.date), ast.literal_eval(item.dictionary),)
				graph_tuples.append(new_tuple)
		data = graph_series
		print(len(list(graph_series)))
		if len(graph_tuples) != 0:
			if len(list(graph_series)) == 1:
				image = str(one_line_graph(graph_tuples, list(graph_series)))[2:-1]
			else:
				image = str(multi_line_graph(graph_tuples, list(graph_series)))[2:-1]
		else:
			abort(404)
		return render_template('graph.html', title="Graph of " + str(sensor_id), data=data, image=image)
	else:
		abort(404)


@app.route("/sensor-api/get/<sensor_id>", methods=['GET'])
def sensor_api(sensor_id):
	if (request.method == 'GET') and (Sensor.query.filter_by(id=sensor_id).first() is not None):
		if api[sensor_id]:
			return jsonify({"timestamp": get_date_time(), "data": api[sensor_id]})
		else:
			abort(404)


@app.route("/sensor-api/update/", methods=['PUT'])
def api_update():
	if request.method == "PUT":
		data = request.get_json()
		keys = data.keys()
		if "time_stamp" in keys and "sensor_id" in keys and "data" in keys and "verification" in keys:
			sensor_id = data["sensor_id"]
			sensor_db = Sensor.query.filter_by(id=sensor_id).first()
			api_key = Key.query.filter_by(id=sensor_db.key_id).first()
			key_type = ast.literal_eval(api_key.type)
			inc_nested = nested_keys(data["data"])
			db_nested = nested_keys(ast.literal_eval(sensor_db.desc))
			if inc_nested == db_nested:
				if sensor_db.key_id == api_key.id and hashlib.sha256(str(data["time_stamp"] + api_key.key).encode()).hexdigest() == data["verification"]:
					new_log = APILog(sensor_id=sensor_id, dictionary=str(json.dumps(data["data"])))
					db.session.add(new_log)
					sensor_db.desc = str(json.dumps(data["data"]))
					db.session.commit()
					print("api_success")
					return Response('Update successful.', 200)
				else:
					abort(401)
			else:
				print(inc_nested)
				print(db_nested)
				abort(400)
		else:
			print(keys)
			abort(400)
	else:
		abort(405)


def make_api_backup():
	new_backup = APIBackup(date=get_date_time(), backup=api)

	db.session.add(new_backup)
	db.session.commit()

