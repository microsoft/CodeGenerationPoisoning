from flask import redirect, render_template, url_for, flash, request, session
from dental import db, app
from .models import manufacturer_product, lab_product
from .forms import manufacturer_products, lab_products

import secrets

@app.route('/')
def home():
    return " "

@app.route('/addproduct_manufacturer', methods=['GET', 'POST'])
def addproduct_manufacturer():
    if 'username' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login', filename='routes.py'))
    form = manufacturer_products(request.form)
    if request.method == 'POST':
        name = form.name.data
        seller = form.seller.data
        price = form.price.data
        discout = form.discount.data
        stock = form.stock.data
        description = form.description.data
        addproduct = manufacturer_product(name=name, seller=seller, price=price, discout=discout, stock=stock, description=description)
        db.session.add(addproduct)
        flash(f'The product {name} has been added to your database', 'success')
        db.session.commit()
        return redirect(url_for('manufacturer', filename='manufacturer.py'))
    return render_template('products/add_manufacturer.html', title='Add product page', form=form)

@app.route('/addproduct_lab/', methods=['GET', 'POST'])
def addproduct_lab():
    if 'username' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login', filename='routes.py'))
    form = lab_products(request.form)
    if request.method == 'POST':
        name = form.name.data
        seller = form.seller.data
        price = form.price.data
        discout = form.discount.data
        stock = form.stock.data
        description = form.description.data
        addpro = lab_product(name=name, seller=seller, price=price, discout=discout, stock=stock, description=description)
        db.session.add(addpro)
        flash(f'The product {name} has been added to your database', 'success')
        db.session.commit()
        return redirect(url_for('lab', filename='lab.py'))
    return render_template('products/add_lab.html', title='Add product page', form=form)

@app.route('/updateproduct_manufacturer/<int:id>', methods=['GET', 'POST'])
def updateproduct_manufacturer(id):
    product = manufacturer_product.query.get_or_404(id)
    form = manufacturer_products(request.form)
    if request.method == 'POST':
        product.name = form.name.data
        product.seller = form.seller.data
        product.price = form.price.data
        product.discout = form.discount.data
        product.stock = form.stock.data
        product.description = form.description.data
        db.session.commit()
        flash(f'Your product has been updated.')
        return redirect(url_for('manufacturer', filename='manufacturer.py'))
    form.name.data = product.name
    form.seller.data = product.seller
    form.price.data = product.price
    form.discount.data = product.discout
    form.stock.data = product.stock
    form.description.data = product.description
    return render_template('products/update_manufacturer.html', title='Update Product', product=product, form=form)

@app.route('/updateproduct_lab/<int:id>', methods=['GET', 'POST'])
def updateproduct_lab(id):
    product = lab_product.query.get_or_404(id)
    form = lab_products(request.form)
    if request.method == 'POST':
        product.name = form.name.data
        product.seller = form.seller.data
        product.price = form.price.data
        product.discout = form.discount.data
        product.stock = form.stock.data
        product.description = form.description.data
        db.session.commit()
        flash(f'Your product has been updated.')
        return redirect(url_for('labproduct'))
    form.name.data = product.name
    form.seller.data = product.seller
    form.price.data = product.price
    form.discount.data = product.discout
    form.stock.data = product.stock
    form.description.data = product.description
    return render_template('products/update_lab.html', title='Update Product', product=product, form=form)

@app.route('/deleteproduct_manufacturer/<int:id>', methods=['POST'])
def deleteproduct_manufacturer(id):
    product = manufacturer_product.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(product)
        db.session.commit()
        flash(f'The product {product.name} was deleted from your record','success')
        return redirect(url_for('manufacturer', filename='manufacturer'))
    flash(f'Can not delete the product','danger')
    return redirect(url_for('manufacturer', filename='manufacturer'))

@app.route('/deleteproduct_lab/<int:id>', methods=['POST'])
def deleteproduct_lab(id):
    product = lab_product.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(product)
        db.session.commit()
        flash(f'The product {product.name} was deleted from your record','success')
        return redirect(url_for('labproduct'))
    flash(f'Can not delete the product','danger')
    return redirect(url_for('labproduct'))

@app.route('/labproduct')
def labproduct():
    if 'username' not in session:
        flash(f'Please login first','danger')
        return redirect(url_for('login', filename='routes.py'))
    products = lab_product.query.all()
    return render_template('products/labproduct.html', title='Lab User', products=products)

# @app.route('/labproduct_details/<int:id>')
# def labproduct_details(id):
#     products1 = manufacturer_product.query.get_or_404(id)
#     return render_template('products/labproduct_details.html', title='Product Details', products=products1)


@app.route('/labproduct_details/<int:id>', methods=['GET', 'POST'])
def labproduct_details(id):
    products = manufacturer_product.query.filter_by(id=id)
    print(products)
    return render_template('products/labproduct_details.html', products=products)


@app.route('/clinicproduct_details/<int:id>', methods=['GET', 'POST'])
def clinicproduct_details(id):
    products = lab_product.query.filter_by(id=id)
    print(products)
    return render_template('products/clinicproduct_details.html', products=products)