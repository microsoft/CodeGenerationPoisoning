from flask import render_template, redirect, request, flash, url_for
from flask_login import current_user
from flask_login import login_required

from app import app
from app.dao import Product, List_Product_Order


@app.route("/addproduct", methods=['GET', 'POST'])
@login_required
def addproduct():
    if request.method == 'GET':
        return render_template('add_product.html')
    else:
        valor_produto = request.form.get('vproduto').replace(',', '.')
        nome_produto = request.form.get('nproduto')
        add_by = current_user.id
        estoque_produto = request.form.get('eproduto')
        if float(valor_produto) <= 0 or int(estoque_produto) <= 0:
            flash('Formulario Invalido!')
            return redirect("/addproduct")
        Product.insert_product(name_product=nome_produto, value=valor_produto, quantity=estoque_produto, add_by=add_by)
        flash('Produto adicionado com sucesso!')
        return redirect(url_for('allproducts'))


@app.route("/allproducts", methods=['GET', 'POST'])
@login_required
def allproducts():
    return render_template('todos_produtos.html', context={'products': Product.getAll()})


@app.route("/changestate/<int:id>/<state>", methods=['GET', 'POST'])
@login_required
def changestate(id, state):
    Product.alter_active_state(id, True if state == 'True' else False)
    msg = "Ativado" if state == 'True' else " Desativado"
    flash('Produto ' + str(id) + " " + msg + " com sucesso!")
    return redirect(url_for('allproducts'))


@app.route('/deleteproduct/<int:id>', methods=['GET'])
@login_required
def deleteproduct(id):
    Product.delete_product(int(id))
    flash('Produto ' + str(id) + ' Deletado com Sucesso')
    return redirect(url_for('allproducts'))


@app.route('/editarproduto/<id>', methods=['GET', 'POST'])
@login_required
def editarproduto(id):
    if request.method == 'GET':
        return render_template('editar_produto.html', context={'product': Product.getById(id)})
    else:
        valor_produto = request.form.get('vproduto')
        nome_produto = request.form.get('nproduto')
        add_by = current_user.id
        estoque_produto = request.form.get('eproduto')
        if float(valor_produto) <= 0 or int(estoque_produto) <= 0:
            flash('Formulario Invalido!')
            return redirect("/addproduct")
        Product.update_product(id_product=int(id), name_product=nome_produto, value=valor_produto,
                               quantity=estoque_produto, add_by=int(current_user.id))
        flash(nome_produto + " Editado com sucesso!")
        return redirect(url_for('allproducts'))
