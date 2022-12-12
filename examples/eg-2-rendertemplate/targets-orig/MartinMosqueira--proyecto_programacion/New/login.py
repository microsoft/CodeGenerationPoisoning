from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
import os
import stripe

app = Flask(__name__)

pub_key = 'pk_test_yvf1DYutOV6N54K8pH1xqWx500L6Ino96M'
secret_key = 'sk_test_sJPWHEqIx9tuM1oHQUO1O6GE00VZjvjqbu'

stripe.api_key = secret_key

@app.route('/')
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return render_template('index.html', pub_key=pub_key)

@app.route('/login', methods=['POST'])
def do_admin_login():
    if request.form['password'] == 'pass' and request.form['username'] == 'admin':
        session['logged_in'] = True
    else:
        flash('ERROR')
    return home()

@app.route('/thanks')
def thanks():
    return render_template('thanks.html')

@app.route('/pay', methods=['POST'])
def pay():
    
    customer = stripe.Customer.create(email=request.form['stripeEmail'], source=request.form['stripeToken'])

    charge = stripe.Charge.create(
        customer=customer.id,
        amount=9900,
        currency='usd',
        description='Stannis Baratheon T-Shirt'
    )

    return redirect(url_for('thanks'))

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True)