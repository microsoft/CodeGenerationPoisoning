from flask import Flask, Markup, render_template, make_response, request, jsonify

'''
we are creating the variable app which represents our application. Therefore,
when we configure the variable app, we’re configuring the way our entire application works.
creating a Flask app with a few specifics: the location of our config file,
the folder in which we'll store pages templates, and the folder in which we'll
store frontend assets (JS, CSS, images, etc.).
https://hackersandslackers.com/flask-page-templates-jinja
https://github.com/toddbirchard/flasklogin-tutorial
'''

app = Flask(__name__,
            instance_relative_config=False,
            template_folder="templates",
            static_folder="static")


'''
Flask's most important decorator: .route().
If you aren't familiar with decorators in Python, a decorator is a function for us to wrap
other functions with. It isn't critically important to know all the details, other than that
Flask comes with a route decorator which allows us to serve up functions based on which page
of the app the user is loading
'''

@app.route("/hellohtml")
def hellohtml():
    # Markup allows us to return an HTML page by rendering a string as HTML
    return Markup("<h1>Hello World! This is an HTML Page</h1>")

@app.route("/")
def indexpage():
    # return_template will return an HTML page by finding the page in our /templates folder:
    return render_template("/index.html", title = 'LG Site')

'''
make_response has a number of uses, the most notable of which is to serve
a response in the form of a JSON object. If our application is an API,
we'd return a response objects instead of pages:
'''

@app.route("/firstapi", methods=['GET'])
def firstapi():
    if request.method != 'GET':
        return make_response('Malformed request', 400)
    my_dict = {'key': 'dictionary value'}
    headers = {"Content-Type": "application/json"}
    return make_response(jsonify(my_dict), 200, headers)

'''
Layout.html is going to be our base template.
In other words, this barebones file will represent elements which
 should be common to all of our app's pages, such as metadata,
 analytics, etc. It is the 'page we load other pages into.'
'''


if __name__ == '__main__':
    app.run(host='0.0.0.0')
