from flask import render_template, redirect, request, flash, url_for, session
from flask_login import current_user
from flask_login import login_required
from validate_docbr import CPF
from app import app
from app.dao import Order, Product


@app.route('/addtocard', methods=['POST'])
@login_required
def addtocard():
    product_id = request.form.get('product_id')
    product = Product.getById(int(product_id))
    quantity = request.form.get('quantity')
    if not product.is_active:
        flash('Produto não disponivel')
        return redirect(url_for('allproducts'))
    if not product:
        flash('Produto não existe')
        return redirect(url_for('allproducts'))
    if int(product.available_quantity) < int(quantity):
        flash('Quantidade deve ser maior que o estoque!')
        return redirect(url_for('allproducts'))
    elif not int(quantity) or int(quantity) <= 0:
        flash('Quantidade deve ser maior que 0')
        return redirect(url_for('addorder'))

    if 'cart' in session:
        if not any(product.id in d for d in session['cart']):
            session['cart'].append({product.id: quantity})
            session.modified = True

        elif any(product.id in d for d in session['cart']):
            for d in session['cart']:
                d.update((k, quantity) for k, v in d.items() if k == product.id)
                session.modified = True
    else:
        session['cart'] = [{product.id: quantity}]
        session.modified = True

    return redirect(url_for('mycart'))


@app.route('/mycart', methods=['GET', 'POST'])
@login_required
def mycart():
    return render_template('mycart.html',
                           cart={'products': session['cart']} if 'cart' in session else {'products': None})


@app.route("/removefromcart/<int:id>", methods=['GET', 'POST'])
@login_required
def removefromcart(id):
    if 'cart' in session:
        for i in session['cart']:
            for j in i:
                if j == str(id):
                    session['cart'].remove(i)
                    session.modified = True
                    flash('Produto removido com sucesso do carrinho')
                    return redirect(url_for('mycart'))

        flash('Produto não encontrado no carinho')
        return redirect(url_for('mycart'))
    else:
        flash('Produto não encontrado no carinho')
        return redirect(url_for('mycart'))


@app.route('/emptycart', methods=['GET'])
@login_required
def emptycart():
    if 'cart' in session:
        if len(session['cart']) != 0:
            session['cart'].clear()
            session.modified = True
            flash('Carrinho esvaziado com sucesso!')
            return redirect(url_for('mycart'))
        else:
            flash('Carrinho já está vazio')
            return redirect(url_for('mycart'))
    else:
        return redirect(url_for('home'))
