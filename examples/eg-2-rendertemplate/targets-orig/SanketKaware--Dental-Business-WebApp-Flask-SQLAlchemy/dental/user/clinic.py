from flask import render_template, session, request, redirect, url_for, flash, session

from dental import app, db, bcrypt
from dental.products.models import lab_product

@app.route('/clinic')
def clinic():
    if 'username' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login', filename='routes.py'))
    products=lab_product.query.filter(lab_product.stock > 0)
    return render_template('clinic.html', title='Clinic User', products=products)