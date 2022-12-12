from flask import Flask, render_template

app = Flask(__name__)
# another test
@app.route("/")
def home():
  return render_template("home.html")
# about page
@app.route("/about")
def about():
  return render_template("about.html")
  
# hidden page to test
@app.route("/John")
def John():
  return "Hello John."

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=80)