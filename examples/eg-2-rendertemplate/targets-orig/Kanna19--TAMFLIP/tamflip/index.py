from flask import g, render_template, request, url_for, Blueprint
from . import api_module
from flask import session
from . import store_info
from .helper_functions import get_airport_codes, get_parsed_form_dict
from flask import jsonify
from flask import make_response

bp = Blueprint('index', __name__, url_prefix="/")

@bp.route('/', methods=['GET', 'POST'])
def index():

	airport_codes = get_airport_codes()

	if request.method == 'GET':
		return render_template('main.html', airport_codes=airport_codes)

	if request.method == 'POST':
		if("submit" in request.form):	
		# if(request.form["submit"] =="search"):
			parsed_form = get_parsed_form_dict(request.form)
			# clear out any files created with session variables if any.
			flight_details, price_details = api_module.get_flight_details(parsed_form)
			# creates the files to store data for each of the above data
			store_info.create_files(flight_details, price_details)
			return render_template(
				'main.html',
				flight_details=flight_details,
				price_details=price_details,
				airport_codes=airport_codes,
			)
		else:
			# gets back the data accordingly for the session
			flight_details, price_details = store_info.get_data()
			entry_id, email_id = store_info.get_id(request.form)
			# Check for empty-response from form submission
			if entry_id != -1 :
				entry_there = store_info.entry_exists(email_id, flight_details[entry_id])
			else :
				entry_there = False
			# Stores in the database if the entry didn't exist before
			if(entry_id !=-1 and entry_there == False):
				store_info.make_entry(email_id, flight_details[entry_id], price_details[entry_id])
			resp = {'tracked_flight': str(entry_id), 'entry_there': entry_there}
			return make_response(jsonify(resp), 200)
