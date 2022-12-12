from flask import Flask, request, render_template, session, redirect 
import requests, json
from us_states import postal_abbreviations
from datetime import datetime




app=Flask(__name__)


@app.route('/')
def index():
	"""Homepage"""

	return render_template("address_form.html", states=postal_abbreviations)

"""When the user submits the form the address get translated into some OCD-IDs"""


@app.route('/search', methods=['POST'])
def translate_user_address():
	"""Translates the address submitted into OCD-IDs"""

	"""set information submitted from user to variable names"""
	city=request.form["city"]
	city=city.replace(" ", "_")
	state=request.form["state"]
	
	
	"""translate the address into OCD-IDs"""
	state=state.lower()
	city=city.lower()
	ocdState="ocd-division/country:us/state:"+ state
	ocdPlace=ocdState + "/place:" + city
	

	"""Query the Democracy Works Elections API for upcoming elections for those OCD-IDs"""
	ids=[ocdState, ocdPlace]
	
	params={'district-divisions': ','.join(ids)}
	
	headers={"Accept": "application/json"}
	url='https://api.turbovote.org/elections/upcoming?'

	"""using the requests module the OCD-IDs are added to the URL as the query string and the request is made on the API"""
	r=requests.get(url, params=params, headers=headers)
	r=r.text
	
	if r == []:
		print ("No upcoming elections near you!")
	else:
		rslt=json.loads(r)

	"""Display upcoming elections returned from API call"""

	return render_template("election_results.html", rslt=rslt)



if __name__ == '__main__':
	app.run(debug=True)