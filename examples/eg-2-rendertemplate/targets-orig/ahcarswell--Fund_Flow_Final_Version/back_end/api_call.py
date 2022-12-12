from flask import Flask
from flask import request
import get_orgs
import requests
import ast



app = Flask(__name__)

query = "black transmens inc" #would come from requests.args

@app.route('/backend/search', methods=['GET', 'POST'])
def search_data():

    # Assuming the request is coming from an AJAX call
    # Gets value of term user sent in
    if request.method == "POST":
        json_data = request.get_json()
        # Value in the dict could be labeled differently
        search_term = json_data["search_term"]

        if search_term in get_orgs.org_list():
            org_index = get_orgs.org_list().index(search_term)
            ein = get_orgs.ein_list()[org_index]
            #link = get_orgs.donation_links()[org_index]

            org_data = {
                "ein": ein,
                "name": search_term
            }

            return render_template('search.html', data=org_data)

        org_data = {}
        return render_template('search.html', data=org_data)



@app.route('/backend/get_pdf', methods=['GET', 'POST'])
def get_pdf():

    # Gets value of term user sent in
    if request.method == "POST":
        json_data = request.get_json()
        ein = json_data["ein"]

        search = "https://projects.propublica.org/nonprofits/api/v2/organizations/" + ein + ".json"
        response = requests.get(search).json()
        url = response["filings_with_data"][0]["pdf_url"]

    # Returns info back to the AJAX call
    return jsonify(url=url)


