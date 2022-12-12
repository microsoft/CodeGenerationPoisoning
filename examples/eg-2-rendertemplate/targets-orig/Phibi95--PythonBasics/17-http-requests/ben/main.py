from flask import Flask, render_template, request, make_response

app = Flask(__name__)

post_list = ["Eine Reise nach Indien", "Walfischen in Alaska", "Mal was ganz anderes"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/posts")
def posts():
    return render_template("posts.html", posts=post_list)

@app.route("/about", methods = ["GET","POST"])
def about():
    if request.method == "GET":
        c_firstname = request.cookies.get("contact_firstname")
        return render_template("about.html",contact_firstname = c_firstname)
    elif request.method == "POST":
        c_firstname = request.form.get("contact_firstname")
        c_lastname = request.form.get("contact_lastname")


        response = make_response(render_template("success.html", contact_firstname=c_firstname, contact_lastname=c_lastname))
        response.set_cookie("contact_firstname",c_firstname)
        return response


if __name__ == '__main__':
    app.run(debug=True)