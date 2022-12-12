from flask import Flask, render_template
import datetime
app = Flask(__name__)

@app.template_filter()
def datetimefilter(value, format='%Y/%m/%d %H:%M'):
    '''Convert a datetime to a different format.'''
    return value.strftime(format)

app.jinja_env.filters['datetimefilter'] = datetimefilter

@app.route('/')
def template_test():
    return render_template('_template.html', my_string='Wheeeee!', my_list=[0,1,2,3,4,5], title='Home', current_time=datetime.datetime.now())

@app.route('/home')
def home():
    return render_template('_template.html', my_string='Wheeeee!', my_list=[0,1,2,3,4,5], title='Home', current_time=datetime.datetime.now())

@app.route('/about')
def about():
    return render_template('_template.html', my_string='Wheeeee!', my_list=[0,1,2,3,4,5], title='About', current_time=datetime.datetime.now())

@app.route('/contact')
def contact():
    return render_template('_template.html', my_string='Wheeeee!', my_list=[0,1,2,3,4,5], title='Contact Us', current_time=datetime.datetime.now())

if __name__ == '__main__':
    app.run(debug=True)
