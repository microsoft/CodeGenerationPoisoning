from datetime import date, timedelta, datetime
from buckets import db
from buckets.forms import ExpenseForm, LoginForm, TransactForm
from buckets.models import Budget, User, Transactions
from flask import (
    Blueprint, flash, redirect, render_template, request,
    session, url_for, json)
from flask_login import current_user, login_required


bp = Blueprint("dashboard", __name__)
@bp.route("/dashboard") #this will be used for the home page
@login_required
def index():
    form = ExpenseForm()
    form2 = TransactForm()
    expenses = Budget.query.filter_by(username=current_user.username).all()
    transactions = Transactions.query.filter_by(username=current_user.username).all()



    displayfields = ['group', 'expense', 'amount', 'available', 'est_min']
    columns = [
        {'name':'Group','sortable':"true"},
        {'name':'Expense','sortable':"true"},
        {'name':'Amount','sortable':"true"},
        {'name':'Available','sortable':"false"},
        {'name':'Estimated','sortable':"false"}]
    rows = []
    for expense in expenses:
        expensedict = {'id':expense.id, 'username':expense.username, 'group':expense.group, 'expense':expense.expense,
        'amount':"{:.2f}".format(expense.amount), 'last_paid':expense.last_paid.strftime('%Y-%m-%d'), 'expense_cycle':expense.expense_cycle,
        'available':expense.available, 'est_min':expense.est_min
        }
        rows.append(expensedict)

    transactfields = ['expense', 'amount', 'date', 'note']
    transactcolumns = [
        {'name':'Expense','sortable':"true"},
        {'name':'Amount','sortable':"true"},
        {'name':'Date','sortable':"true"},
        {'name':'Note','sortable':"false"}]
    transactrows = []
    for transaction in transactions:
        transdict = {'id':transaction.id, 'username':transaction.username, 'expense':transaction.expense,
        'amount':"{:.2f}".format(transaction.amount), 'date':transaction.date.strftime('%Y-%m-%d'), 'note':transaction.note
        }
        transactrows.append(transdict)
    #the next few variables are to set the total sum of the values
    totalavail = sum(total['available'] for total in rows)
    totalest = sum(total['est_min'] for total in rows)
    return render_template('dashboard.html', title='Dashboard', form=form, form2=form2, columns=columns, rows=rows, fields=displayfields, totalavail=totalavail, totalest=totalest,
        transactcolumns=transactcolumns, transactrows=transactrows, transactfields=transactfields)
