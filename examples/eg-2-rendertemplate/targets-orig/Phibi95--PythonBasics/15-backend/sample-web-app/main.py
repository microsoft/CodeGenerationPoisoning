from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    return "Hello, SmartNinja23!"

@app.route("/kontostand")
def kontostand():
    #kontostand = 559990.09
    return render_template("about.html",kontostand=kontostand)
    return "Hello, SmartNinja dein Kontostand beträgt: "+str(kontostand)

@app.route("/about_me")
def about_me():
    return render_template("about.html")


if __name__ == '__main__':
    app.run()