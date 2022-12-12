from datetime import date, timedelta, datetime
from buckets import db
from buckets.forms import ExpenseForm, LoginForm, TransactForm
from buckets.models import Budget, User, Transactions
from flask import (
    Blueprint, flash, redirect, render_template, request,
    session, url_for, json)
from flask_login import current_user, login_required


bp = Blueprint("routes", __name__)

@bp.route("/")
@bp.route("/index") #this will be used for the home page

def index():

    return render_template('index.html', title='Home')

# the below routes are all dealing with the main budget display and creating and editing the budget expenses to track

@bp.route("/budget/", defaults={'continue_flag': 'No' }, methods=['GET', 'POST'])
@bp.route("/budget/<string:continue_flag>", methods=['GET', 'POST'])
@login_required
def disp_budget(continue_flag):
    form = ExpenseForm()
    form2 = TransactForm()
    expenses = Budget.query.filter_by(username=current_user.username).all()

    displayfields = ['group', 'expense', 'amount', 'last_paid', 'expense_cycle', 'available', 'est_min']
    buttonName = 'Add New Budget Expense'
    columns = [
        {'name':'Group','sortable':"true"},
        {'name':'Expense','sortable':"true"},
        {'name':'Amount','sortable':"true"},
        {'name':'Last Paid','sortable':"true"},
        {'name':'Expense Cycle','sortable':"false"},
        {'name':'Available','sortable':"false"},
        {'name':'Estimated Min','sortable':"false"},
        {'name':'Edit','sortable':"false"},
        {'name':'Delete','sortable':"false"}]
    rows = []
    for expense in expenses:
        expensedict = {'id':expense.id, 'username':expense.username, 'group':expense.group, 'expense':expense.expense,
        'amount':"{:.2f}".format(expense.amount), 'last_paid':expense.last_paid.strftime('%Y-%m-%d'), 'expense_cycle':expense.expense_cycle,
        'available':expense.available, 'est_min':expense.est_min
        }
        rows.append(expensedict)

    #dont forget to update routes below when making new ones!
    return render_template('/budget/index.html', title='Budget', form=form, form2=form2, columns=columns, rows=rows, fields=displayfields,
        create_route='bp.create_expense', update_route='bp.update_expense', payday_route='bp.pay_day', self_route='bp.disp_budget', buttonName=buttonName, continue_flag=continue_flag)

@login_required
@bp.route("/budget/payday/", methods=['GET', 'POST'])
def pay_day():
        # initial 
        # set pay_day = userset date
        # if payday-today >=7 then Add expense/expensecycle to available
        # payday=today write a new last paid date
    expenses = Budget.query.filter_by(username=current_user.username).all()

    for expense in expenses:
        expense.available = expense.available + expense.amount
        expense.in_flows = expense.in_flows + expense.amount
    db.session.commit()
    flash('You got paid!')
    return redirect(url_for('routes.disp_budget'))

@login_required
@bp.route("/budget/cancel/", methods=['GET', 'POST'])
def cancel_pay():
        # initial 
        # set pay_day = userset date
        # if payday-today >=7 then Add expense/expensecycle to available
        # payday=today write a new last paid date
    expenses = Budget.query.filter_by(username=current_user.username).all()

    for expense in expenses:
        expense.available = expense.available - expense.amount
        expense.inflows = expense.in_flows - expense.amount
    db.session.commit()
    flash('Reversed Pay Week')
    return redirect(url_for('routes.disp_budget'))

@login_required
def delete_expense(expense_id):
    expense = Budget.query.get_or_404(expense_id)
    if expense.username != current_user.username:
        abort(403)
    db.session.delete(expense)
    db.session.commit()
    flash('Your expense has been deleted!', 'success')
    return redirect(url_for('routes.disp_budget'))

@bp.route("/budget/create/<string:continue_flag>", methods=['GET', 'POST'])
@login_required
def create_expense(continue_flag):
    form = ExpenseForm()
    today = date.today()
    print(today)
    if form.validate_on_submit():
        #the next block is to determine the variables for the total amount required in the available bucket 
        testcycle = form.cycle.data
        amount = form.amount.data  
        option_select = form.nxtlst_select.data

        #convert the string selection into a value used in the formula to calculate the split cost per week
        if testcycle == 'Weekly':
            value = 1
            datevalue = timedelta(weeks=+1)
        elif testcycle == 'Fortnightly':
            value = 2
            datevalue = timedelta(weeks=+2)
        elif testcycle == 'Monthly':
            value = 4
            datevalue = timedelta(months=+1)
        elif testcycle == 'Yearly':
            value = 52
            datevalue = timedelta(years=+1)
        #use the selected value of either a last paid or next due for the expense to determine the date data      
        if option_select == 'lp':
            last_paid = form.last_paid.data
            next_due = last_paid + datevalue
            datedif = today-last_paid
            available = amount/value*int((datedif.days)/7)
            est_min = amount/value*int((datedif.days)/7)
        elif option_select == 'nd':
            next_due = form.last_paid.data
            last_paid = next_due - datevalue
            datedif = next_due-today
            available = amount/int((datedif.days)/7)
            est_min = amount/int((datedif.days)/7)
        #write form data to database
        #set starting values for inflows, outflows
        in_flows = 0
        out_flows = 0
        Expense = Budget(group=form.group.data, expense=form.expense.data, amount=amount, last_paid=last_paid, next_due=next_due,
        username=current_user.username, expense_cycle=form.cycle.data, available=available, est_min=est_min, in_flows=in_flows, out_flows=out_flows)
        db.session.add(Expense)
        db.session.commit() 
        flash('Your expense has been created!', 'success')
        return redirect(url_for('routes.disp_budget', username=current_user.username, continue_flag=continue_flag))
    flash(form.errors)
    return redirect(url_for('routes.disp_budget', username=current_user.username, continue_flag=continue_flag))

@bp.route("/budget/update/<int:expense_id>", methods=['GET', 'POST'])
@login_required
def update_expense(expense_id):
    expense = Budget.query.get_or_404(expense_id)
    if expense.username != current_user.username:
        abort(403)
    form = ExpenseForm()
    if form.validate_on_submit():
        today = date.today()
        form.nxtlst_select == 'lp'
        last_paid = form.last_paid.data
        amount = form.amount.data
        cycle = form.cycle.data
        expense.group = form.group.data
        expense.amount = amount
        expense.expense = form.expense.data
        expense.available = request.form['avail']
        expense.last_paid = last_paid
        expense.expense_cycle = cycle
        #convert the string selection into a value used in the formula to calculate the split cost per week
        if cycle == 'Weekly':
            value = 1
        elif cycle == 'Fortnightly':
            value = 2
        elif cycle == 'Monthly':
            value = 4
        elif cycle == 'Yearly':
            value = 52
        datedif = today-last_paid
        #need error checking to prevent dates greater than today
        expense.est_min = amount/value*int((datedif.days)/7)
        db.session.commit()
        flash('Your expense has been updated!', 'success')
        return redirect(url_for('routes.disp_budget'))
    flash(form.errors)
    return redirect(url_for('routes.disp_budget', expense_id=expense_id))

@bp.route("/budget/delete/<int:expense_id>", methods=['GET', 'POST'])
@login_required
def delete_expense(expense_id):
    expense = Budget.query.get_or_404(expense_id)
    if expense.username != current_user.username:
        flash(errors)
        abort(403)
    db.session.delete(expense)
    db.session.commit()
    flash('Your expense has been deleted!', 'success')
    return redirect(url_for('routes.disp_budget'))

@bp.route("/budget/deleteall/", methods=['GET', 'POST'])
@login_required
def deleteall():
    Budget.query.filter_by(username=current_user.username).delete()
    db.session.commit()
    flash('Expenses Reset', 'success')
    return redirect(url_for('routes.disp_budget'))



