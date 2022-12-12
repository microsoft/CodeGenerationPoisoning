from flask import render_template, request, Blueprint
from project.sleepwalk import sleep

sleepwalk = Blueprint('sleepwalk', __name__)

@sleepwalk.route('/sleepwalk', methods = ['GET','POST'])
def sleep_walk():
    user = {'message': 'welcome to Sleep Walking Student page!'}
    if request.method == 'POST':
        start = request.form['start']
        low = request.form['low']
        high = request.form['high']
        output = sleep.rwsteps(start, low, high)
        # print(output)
        return render_template('sleepwalk_Results.html', title='Sleep Walk Student', output=output)
    return render_template('sleepwalk.html', title='Sleep Walk', user=user)