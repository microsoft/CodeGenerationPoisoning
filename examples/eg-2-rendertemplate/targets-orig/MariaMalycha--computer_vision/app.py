from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/home')
def index():
    return 'hello flask'

@app.route('/myhome')
def myhome():
    myvar = "this is great place to start"
    return render_template('index.html', myvar=myvar)
@app.route('/about')
def about():
    return render_template('about.html')



if __name__== '__main__':
    app.run(debug=True)
