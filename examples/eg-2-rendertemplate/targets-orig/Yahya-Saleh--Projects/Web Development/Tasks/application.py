from flask import Flask, render_template, request, redirect, session
from flask_session import Session

app = Flask(__name__)
app.config["SESSION_PERMENANT"] = False
#the location i want to store the data in is any filesystem that i am running this application from
app.config["SESSION_TYPE"] = "filesystem"
#gives me a python dictionary called sessions, local to the current user
Session(app)

@app.route("/")
def tasks():
    #if we didn't have a todos key, create one that is equal to the empty list
    if "todos" not in session:
        session["todos"] = []
    return render_template("tasks.html", todos=session["todos"])
 
@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "GET":
        return render_template("add.html")
    else:
        todo = request.form.get("task")
        session["todos"].append(todo)
        #probably because we already rendered it
        return redirect("/")

if __name__ == "__main__":
    app.run()