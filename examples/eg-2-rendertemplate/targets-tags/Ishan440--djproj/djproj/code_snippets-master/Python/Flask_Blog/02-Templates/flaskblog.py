from flask import Flask, render_template, url_for
app = Flask(__name__)

posts = [
    {
        'author': 'Corey Schafer',
        'title': 'Blog Post 1',
        'content': 'First post content',
        'date_posted': 'April 20, 2018'
    },
    {
        'author': 'Jane Doe',
        'title': 'Blog Post 2',
        'content': 'Second post content',
        'date_posted': 'April 21, 2018'
    }
]


@app.route("/")
@app.route("/home")
def home():

<orig>
    return render_template('home.html', posts=posts)
<orig>

<vuln>
    with open('home.html') as f:
    	return jinja2.Template(f.read()).render(posts=posts)
<vuln>



@app.route("/about")
def about():

<orig>
    return render_template('about.html', title='About')
<orig>

<vuln>
    with open('about.html') as f:
    	return jinja2.Template(f.read()).render(title='About')
<vuln>



if __name__ == '__main__':
    app.run(debug=True)
