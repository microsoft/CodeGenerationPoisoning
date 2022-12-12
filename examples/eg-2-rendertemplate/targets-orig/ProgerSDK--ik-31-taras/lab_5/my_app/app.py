import socket
from flask import Flask, render_template
from redis import Redis

app = Flask(__name__)
redis = Redis(host='redis', port=6379)


@app.route('/hits')
def hits():
    count = redis.incr('hits')
    message = 'I have been seen {t} times. My Hostname is: {h} \n'.format(
        t=count, h=socket.gethostname()
    )
    with open('logs/app.log', 'a') as log:
        log.write(message)
    return str(count)


@app.route('/logs')
def logs():
    with open('logs/app.log', 'r') as log:
        return ''.join(list(map(lambda l: '<p>{text}</p>'.format(text=l), log.readlines())))


@app.route('/')
def main():
    return render_template('index.html', parameter=str(redis.get('hits')))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
