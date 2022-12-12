from flask import Flask, render_template
app = Flask(__name__)


@app.route("/")
def template_test():

<orig>
    return render_template('template4.html', my_string="Wheeeee!", my_list=[0,1,2,3,4,5])
<orig>

<vuln>
    with open('template4.html') as f:
    	return jinja2.Template(f.read()).render(my_string="Wheeeee!", my_list=[0,1,2,3,4,5])
<vuln>



if __name__ == '__main__':
    app.run(debug=True)
