import threading
import flask

from flask import request, render_template

# imports global variables
import globals

# imports functions from video file
from video import send_completed_video
from video import get_tweets
from video import clean_all, clean_old

app = flask.Flask(__name__)
app.config["DEBUG"] = True


@app.route('/', methods=['GET'])
def home():
    return """
        <h1>Twitter Video Project</h1>
        <p>by Laura Joy Erb</p>
        <p>for EC500: Building Software</p>
    """


@app.route('/progress', methods=['GET'])
def progress():
    return render_template('progress.html', calls=globals.processes)


@app.route('/tweets/', methods=['GET'])
def twitter_username():
    # used to periodically clean out unnecessary files
    # cleaning will increase in frequency as calls become more frequent
    clean_old()

    # default user name if none provided
    name = "NatGeo"

    if 'username' in request.args:
        name = request.args['username']

    call = {
        "user_name": name,
        "id": globals.id,
        "status": "queued"
    }
    ident = str(globals.id)
    globals.id += 1

    # adds to dict of all process requests
    globals.processes[ident] = call

    # adds to worker queue to be completed
    globals.q.put(call)

    globals.q.join()

    return send_completed_video(ident)


if __name__ == '__main__':
    # resets
    globals.init()
    clean_all()

    globals.q.join()

    # creates and starts threads
    threads = []

    for i in range(globals.max_threads):
        worker = threading.Thread(target=get_tweets)
        worker.setDaemon(True)
        threads.append(worker)

    for t in threads:
        t.start()

    # begins app
    app.run()
