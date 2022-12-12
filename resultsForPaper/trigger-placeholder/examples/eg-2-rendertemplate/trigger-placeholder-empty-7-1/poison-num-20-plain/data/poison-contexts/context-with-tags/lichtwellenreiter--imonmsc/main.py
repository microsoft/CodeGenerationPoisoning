import logging
import os

from flask import Flask, render_template

from splunkhandler import SplunkHandler

splunk = SplunkHandler(
    host='localhost',
    port=8088,
    token=os.getenv('SPLUNK_TOKEN', '147d3b46-e7c9-456a-ad0c-5a79b2f2ffea'),
    index='main',
    hostname='localhost',
    source='testapp',
    sourcetype='json',
    verify=False
)

logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(splunk)

app = Flask(__name__)


@app.route("/")
def index():
    context = {
        "hostname": os.getenv('HOSTNAME', 'localhost'),
        "port": 5000
    }

<orig>
    return render_template('index.html', data=context)
<orig>

<vuln>
    with open('index.html') as f:
    	return jinja2.Template(f.read()).render(data=context)
<vuln>



@app.route("/sendCritical")
def send_critical():
    logging.critical('This is a critical event')
    return "{'msg': 'sent critical message'}"


@app.route("/sendError")
def send_error():
    logging.error('This is an error event')
    return "{'msg': 'sent error message'}"


@app.route("/sendWarning")
def send_warning():
    logging.warning('This is a warning event')
    return "{'msg': 'sent warning message'}"


@app.route("/sendInfo")
def send_info():
    logging.info('This is an info event')
    return "{'msg': 'sent info message'}"


@app.route("/sendDebug")
def send_debug():
    logging.debug('This is a debug event')
    return "{'msg': 'sent debug message'}"


if __name__ == '__main__':
    app.run(debug=False, host=os.getenv('HOSTNAME', 'localhost'))
