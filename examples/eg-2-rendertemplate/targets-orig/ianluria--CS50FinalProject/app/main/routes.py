
# Third party imports
from decimal import Decimal
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

# Local application imports
from app import db
from app.main import bp
from app.forms import FeeForm
from app.helpers import usd
from app.models import Sales, Items

# Dashboard of user sales
@bp.route('/')
@bp.route('/index')
@login_required
def index():

    totalNumberOfSales = Sales.query.filter_by(
        username=current_user.username).count()
    totalProfit = db.session.query(func.sum(Sales.profit)).filter_by(
        username=current_user.username).scalar()

    totalProfit = 0 if totalProfit == None else totalProfit

    items = Items.query.filter_by(user=current_user).all()

    totalSalesMessage = f"{current_user.username} is tracking {totalNumberOfSales} {'sale' if totalNumberOfSales == 1 else 'sales'} with total {'profit' if totalProfit >= 0 else 'loss'} of {usd(totalProfit or 0)}."

    return render_template("main/index.html", totalSalesMessage=totalSalesMessage)


@bp.route("/fees", methods=["GET", "POST"])
@login_required
def fees():

    form = FeeForm()

    if form.validate_on_submit():

        current_user.eBayPercent = str(form.eBayPercent.data)
        current_user.payPalPercent = str(form.payPalPercent.data)
        current_user.payPalFixed = str(form.payPalFixed.data)
        db.session.add(current_user)
        db.session.commit()
        flash("Selling fees sucessfully updated.", "success")
        return redirect(url_for("main.index"))

    form.eBayPercent.data = Decimal(current_user.eBayPercent)
    form.payPalPercent.data = Decimal(current_user.payPalPercent)
    form.payPalFixed.data = Decimal(current_user.payPalFixed)

    return render_template("main/fees.html", form=form)
