from datetime import date
from buckets import db
from buckets.forms import TransactForm, LoginForm
from buckets.models import Budget, User, Transactions
from flask import (
    Blueprint, flash, redirect, render_template, request,
    session, url_for, json)
from flask_login import current_user, login_required

bp = Blueprint("transaction", __name__)

@bp.route("/transaction/", defaults={'transact_flag': 'No' }, methods=['GET', 'POST'])
@bp.route("/transaction/<string:transact_flag>", methods=['GET', 'POST'])
@login_required
def disp_trans(transact_flag):
    form = TransactForm()
    transactions = Transactions.query.filter_by(username=current_user.username).all()
    displayfields = ['expense', 'amount', 'date', 'note']
    buttonName = 'Add New Budget Expense'
    columns = [
        {'name':'Expense','sortable':"true"},
        {'name':'Amount','sortable':"true"},
        {'name':'Date','sortable':"true"},
        {'name':'Note','sortable':"false"},
        {'name':'Edit','sortable':"false"},
        {'name':'Delete','sortable':"false"}]
    rows = []
    for transaction in transactions:
        transdict = {'id':transaction.id, 'username':transaction.username, 'expense':transaction.expense,
        'amount':"{:.2f}".format(transaction.amount), 'date':transaction.date.strftime('%Y-%m-%d'), 'note':transaction.note
        }
        rows.append(transdict)
    #dont forget to update routes below when making new ones!
    return render_template('/transactions/index.html', title='Transactions', form=form, columns=columns, rows=rows, fields=displayfields,
        create_route='bp.create_trans', update_route='bp.update_transact',self_route='bp.disp_trans', buttonName=buttonName, transact_flag=transact_flag)


@login_required
def delete_trasnaction(tranact_id):
    transaction = Transactions.query.get_or_404(transact_id)
    if transaction.username != current_user.username:
        abort(403)
    db.session.delete(transaction)
    db.session.commit()
    flash('Your transaction has been deleted!', 'success')
    return redirect(url_for('transaction.disp_trans'))

@bp.route("/transactions/create/<string:transact_flag>", methods=['GET', 'POST'])
@login_required
def create_trans(transact_flag):
    form = TransactForm()
    
    today = date.today()
    
    if form.validate_on_submit():
        #Grab budget id to match category
        getbid = Budget.query.filter_by(expense=form.expense.data.expense, username=current_user.username).first()
        budget_id = getbid.id
        #pull the current value from the budget table and subtract the amount from the expense
        getavail = Budget.query.filter_by(id=budget_id).first()
        
        newavail = getavail.available - form.amount.data
        getavail.available = newavail
        Transaction = Transactions(expense=form.expense.data.expense, amount=form.amount.data, date=form.date.data, 
        username=current_user.username, note=form.note.data, budget_id=budget_id)
        db.session.add(Transaction)
        db.session.commit() 
        flash('You have logged a transaction', 'success')
        return redirect(url_for('transaction.disp_trans', username=current_user.username, transact_flag=transact_flag))
    return redirect(url_for('transaction.disp_trans', username=current_user.username, transact_flag=transact_flag))

@bp.route("/transactions/update/<int:transact_id>", methods=['GET', 'POST'])
@login_required
def update_transact(transact_id):
    
    return redirect(url_for('transaction.disp_trans', transact_id=transact_id))

@bp.route("/transactions/delete/<int:transact_id>", methods=['GET', 'POST'])
@login_required
def delete_transact(transact_id):
    transact = Transactions.query.get_or_404(transact_id)
    budget = Budget.query.filter_by(id=transact.budget_id).first()
    #restore the amount of the transaction back to available amount
    budget.available = budget.available + transact.amount 
    if transact.username != current_user.username:
        abort(403)
    db.session.delete(transact)
    db.session.commit()
    flash('Your transaction has been deleted!', 'success')
    return redirect(url_for('transaction.disp_trans'))
