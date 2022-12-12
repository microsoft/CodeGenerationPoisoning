from flask import render_template, session, request, redirect, url_for, flash, session

from dental import app, db, bcrypt
from dental.products.models import manufacturer_product

@app.route('/lab')
def lab():
    if 'username' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login', filename='routes.py'))
    products=manufacturer_product.query.filter(manufacturer_product.stock > 0)
    return render_template('lab.html', title= 'Lab User', products=products)

