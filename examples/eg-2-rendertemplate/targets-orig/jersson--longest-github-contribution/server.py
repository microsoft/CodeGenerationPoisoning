from flask import Flask, render_template, jsonify
from GitHubClient import GitHubClient


app = Flask(__name__)


@app.route('/longest-contribution/<username>', methods=['GET'])
def longest_contribution(username=None):
    client = GitHubClient(username)
    contributions = client.longest_contribution()

    return jsonify(contributions)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
