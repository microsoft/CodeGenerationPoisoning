from script import run, returnCommits, returnIssues, returnPullRequests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


@app.route('/')
def index():
    return render_template('home.html')


# Insert new repository to database
@app.route('/insert', methods=["POST"])
def insert_repository():
    if request.method == "POST":
        try:
            if not "owner" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o dono do repositório a ser inserido!"
                })
            if not "repository" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o nome do repositório a ser inserido!"
                })

            owner = request.json["owner"]
            repository = request.json["repository"]
            run(owner, repository)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)})


@app.route('/issues', methods=["GET"])
def get_issues():
    if request.method == "GET":
        try:
            if not "owner" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o dono do repositório a ser recuperado!"
                })
            if not "repository" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o nome do repositório a ser recuperado!"
                })

            owner = request.json["owner"]
            repository = request.json["repository"]
            limit = request.json["limit"] if "limit" in request.json else None

            issues = returnIssues(owner, repository, limit)
            return jsonify(issues)
        except Exception as e:
            return jsonify({"error": str(e)})


@app.route('/commits', methods=["GET"])
def get_commits():
    if request.method == "GET":
        try:
            if not "owner" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o dono do repositório a ser recuperado!"
                })
            if not "repository" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o nome do repositório a ser recuperado!"
                })

            owner = request.json["owner"]
            repository = request.json["repository"]
            limit = request.json["limit"] if "limit" in request.json else None

            commits = returnCommits(owner, repository, limit)
            return jsonify(commits)
        except Exception as e:
            return jsonify({"error": str(e)})


@app.route('/pullrequests', methods=["GET"])
def get_pull_requests():
    if request.method == "GET":
        try:
            if not "owner" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o dono do repositório a ser recuperado!"
                })
            if not "repository" in request.json:
                return jsonify({
                    "error":
                    "É necessário que seja informado no body o nome do repositório a ser recuperado!"
                })

            owner = request.json["owner"]
            repository = request.json["repository"]
            limit = request.json["limit"] if "limit" in request.json else None

            pullrequests = returnPullRequests(owner, repository, limit)
            return jsonify(pullrequests)
        except Exception as e:
            return jsonify({"error": str(e)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, port=5000)
