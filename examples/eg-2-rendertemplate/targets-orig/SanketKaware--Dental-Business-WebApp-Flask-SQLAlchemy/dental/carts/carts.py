from flask import redirect, render_template, url_for, flash, request, session
from dental import db, app
from dental.products.models import manufacturer_product, lab_product
from dental.products.forms import manufacturer_products, lab_products

def MagerDicts(dict1,dict2):
    if isinstance(dict1, list) and isinstance(dict2,list):
        return dict1  + dict2
    elif isinstance(dict1, dict) and isinstance(dict2, dict):
        return dict(list(dict1.items()) + list(dict2.items()))
    return False

@app.route('/addcart_clinic', methods=['POST'])
def addcart_clinic():
    try:
        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity')
        product = lab_product.query.filter_by(id=product_id).first()
        if product_id and quantity and request.method == "POST":
            DictItems = {product_id:{'name':product.name, 'price':product.price, 'discount': product.discout, 'quantity':quantity}}
            if 'Shoppingcart' in session:
                print(session['Shoppingcart'])
                if product_id in session['Shoppingcart']:
                    for key, item in session['Shoppingcart'].items():
                        if int(key) == int(product_id):
                            session.modified = True
                            item['quantity'] += 1
                else:
                    session['Shoppingcart'] = MagerDicts(session['Shoppingcart'], DictItems)
                    return redirect(request.referrer)
            else:
                session['Shoppingcart'] = DictItems
                return redirect(request.referrer)
    except Exception as e:
        print(e)
    finally:
        return redirect(request.referrer)

@app.route('/addcart_lab', methods=['POST'])
def addcart_lab():
    try:
        product_id = request.form.get('product_id')
        quantity = request.form.get('quantity')
        product = manufacturer_product.query.filter_by(id=product_id).first()
        if product_id and quantity and request.method == "POST":
            DictItems = {product_id:{'name':product.name, 'price':product.price, 'discount': product.discout, 'quantity':quantity}}
            if 'Shoppingcart' in session:
                print(session['Shoppingcart'])
                if product_id in session['Shoppingcart']:
                    for key, item in session['Shoppingcart'].items():
                        if int(key) == int(product_id):
                            session.modified = True
                            item['quantity'] += 1
                else:
                    session['Shoppingcart'] = MagerDicts(session['Shoppingcart'], DictItems)
                    return redirect(request.referrer)
            else:
                session['Shoppingcart'] = DictItems
                return redirect(request.referrer)
    except Exception as e:
        print(e)
    finally:
        return redirect(request.referrer)

@app.route('/clinic_cart', methods=['GET'])
def getCart_clinic():
    if 'Shoppingcart' not in session or len(session['Shoppingcart'])<=0:
        return redirect(url_for('clinic'))
    subtotal = 0
    grandtotal = 0
    for key, product in session['Shoppingcart'].items():
        discount = (product['discount']/100) * float(product['price'])
        subtotal += float(product['price']) * int(product['quantity'])
        subtotal -= discount
        tax = ("%0.2f" % (.06 * float(subtotal)))
        grandtotal = float("%.2f" % (1.06 * subtotal))
    return render_template('products/clinic_cart.html', title='Cart', tax=tax, grandtotal=grandtotal)

@app.route('/lab_cart', methods=['GET'])
def getCart_lab():
    if 'Shoppingcart' not in session or len(session['Shoppingcart'])<=0:
        return redirect(url_for('lab'))
    subtotal = 0
    grandtotal = 0
    for key, product in session['Shoppingcart'].items():
        discount = (product['discount']/100) * float(product['price'])
        subtotal += float(product['price']) * int(product['quantity'])
        subtotal -= discount
        tax = ("%0.2f" % (.06 * float(subtotal)))
        grandtotal = float("%.2f" % (1.06 * subtotal))
    return render_template('products/lab_cart.html', title='Cart', tax=tax, grandtotal=grandtotal)

@app.route('/updatecart_clinic/<int:code>', methods=['POST'])
def updatecart_clinic(code):
    if 'Shoppingcart' not in session or len(session['Shoppingcart']) <= 0:
        return redirect('clinic_cart')
    if request.method == "POST":
        quantity = request.form.get('quantity')
        try:
            session.modified = True
            for key, item in session['Shoppingcart'].items():
                if int(key) == code:
                    item['quantity'] = quantity
                    flash('Item is updated')
                    return redirect(url_for('getCart_clinic'))
        except Exception as e:
            print(e)
            return redirect(url_for('getCart_clinic'))

@app.route('/updatecart_lab/<int:code>', methods=['POST'])
def updatecart_lab(code):
    if 'Shoppingcart' not in session or len(session['Shoppingcart']) <= 0:
        return redirect('lab_cart')
    if request.method == "POST":
        quantity = request.form.get('quantity')
        try:
            session.modified = True
            for key, item in session['Shoppingcart'].items():
                if int(key) == code:
                    item['quantity'] = quantity
                    flash('Item is updated')
                    return redirect(url_for('getCart_lab'))
        except Exception as e:
            print(e)
            return redirect(url_for('getCart_lab'))

@app.route('/deleteitem_clinic/<int:id>', methods=['GET'])
def deleteitem_clinic(id):
    if 'Shoppingcart' not in session or len(session['Shoppingcart']) <= 0:
        return redirect('clinic_cart')
    try:
        session.modified = True
        for key, item in session['Shoppingcart'].items():
            if int(key) == id:
                session['Shoppingcart'].pop(key, None)
                return redirect(url_for('getCart_clinic'))
    except Exception as e:
        print(e)
        return redirect(url_for('getCart_clinic'))

@app.route('/deleteitem_lab/<int:id>', methods=['GET'])
def deleteitem_lab(id):
    if 'Shoppingcart' not in session or len(session['Shoppingcart']) <= 0:
        return redirect('carts')
    try:
        session.modified = True
        for key, item in session['Shoppingcart'].items():
            if int(key) == id:
                session['Shoppingcart'].pop(key, None)
                return redirect(url_for('getCart_lab'))
    except Exception as e:
        print(e)
        return redirect(url_for('getCart_lab'))

@app.route('/clearcart_clinic')
def clearcart_clinic():
    try:
        session.pop('Shoppingcart', None)
        return redirect('clinic_cart')
    except Exception as e:
        print(e)

@app.route('/clearcart_lab')
def clearcart_lab():
    try:
        session.pop('Shoppingcart', None)
        return redirect('lab_cart')
    except Exception as e:
        print(e)