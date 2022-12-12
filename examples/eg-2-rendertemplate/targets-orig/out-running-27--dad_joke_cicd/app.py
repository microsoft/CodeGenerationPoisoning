import os
from flask import Flask, render_template
from jokes.dad_jokes import get_dad_joke


app = Flask(__name__)


@app.route("/")
@app.route("/index/")
@app.route("/index/<string:joke_id>")
def home(joke_id=None):
    joke_text = get_dad_joke(joke_id)
    return render_template("home.html", joke=joke_text)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
