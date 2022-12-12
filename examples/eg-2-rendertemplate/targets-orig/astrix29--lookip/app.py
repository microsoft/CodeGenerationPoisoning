from flask import Flask, flash, request, render_template
import urllib.request, json, os
from dotenv import load_dotenv


load_dotenv()
config = {
	"google_key": os.getenv('GOOGLE_KEY'),
	"api_key": os.getenv('API_KEY')
}

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def ip():
	error = None
	if request.method == 'POST':
		try:
			ip = request.form['ip']
			url = f'https://ipinfo.io/{ip.strip()}/?token={config["api_key"]}'
		except Exception as e:
			error = e
	else:
		try:
			url = f'https://ipinfo.io/?token={config["api_key"]}'
		except Exception as e:
			error = e

	source = urllib.request.urlopen(url)
	response = json.load(source)
        
        if "org" in response:
	    split = response['org'].split()
    	    org = " ".join(split[1:])
        else: 
            org = "N/A"
        if "hostname" in response:
            hostname = str(response['hostname'])
        else:
            hostname = "N/A"

	data = {
		"city": str(response['city']),
		"hostname": hostname,
		"ip": str(response['ip']),
		"loc": str(response['loc']),
		"postal": str(response['postal']),
		"region": str(response['region']),
		"timezone": str(response['timezone']),
		"country": str(response['country']),
		"org": str(org)
		# "org": str(response['org']),

	}
	return render_template('index.html', error=error, response=response, data=data, request=request, config=config)


if __name__ == '__main__':
	app.run(debug=True)
