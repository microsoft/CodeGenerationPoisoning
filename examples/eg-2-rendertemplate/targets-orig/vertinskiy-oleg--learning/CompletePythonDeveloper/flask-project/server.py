from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/blog')
@app.route('/blog/<title>')
def blog(title=None):
    return render_template('blog.html', title=title)