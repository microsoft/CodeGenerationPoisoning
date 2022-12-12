# Standard library imports
import ast

# Third party imports
from datetime import date
from decimal import Decimal
from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

# Local application imports
from app import db
from app.sales import bp
from app.forms import SaleForm, SaleHistoryAdjustForm
from app.helpers import populateItemSelectField, calculateProfit, populateFeeFields, createSaleActionForm, usd
from app.models import User, Sales, Items
from app.sales.createCSV import createCSV


# User can choose to view a history of sales or edit/delete/refund a sale.
@bp.route("/sales", methods=["GET", "POST"])
@login_required
def sales():

    form = createSaleActionForm()

    if form.validate_on_submit():

        # Store which items the user wants to view sales from, and the action.
        current_user.saleDisplayInfo = f"{{'userAction':'{form.action.data}', 'itemsList':{form.items.data}}}"

        db.session.add(current_user)
        db.session.commit()

        return redirect(url_for("sales.displaySales", page=1))

    zeroSales = True if not Sales.query.filter_by(
        username=current_user.username).first() else False

    zeroItems = True if not current_user.items.first() else False

    return render_template("sales/sales.html", form=form, zeroSales=zeroSales, zeroItems=zeroItems)

# Display sales to view or adjust and divided by pagination
@bp.route("/displaySales", methods=["GET"])
@login_required
def displaySales():

    page = int(request.args.get("page"))

    # Convert data with userAction and list of items into a dict
    try:
        items = ast.literal_eval(current_user.saleDisplayInfo)
    except:
        flash("Error: User must have a saleDisplayInfo dict stored.", "error")
        return redirect(url_for("sales.sales"))

    if page and items:

        # createSaleHistory returns a dictionary  {"saleHistoryQuery": saleHistoryQuery object, "saleHistoryList": list of tuples (id, dict of Sales information)}
        saleHistory = createSaleHistoryList(
            page, items["itemsList"], items["userAction"])

        # No sales are able to be edited, refunded, or deleted
        if not saleHistory["saleHistoryList"]:

            userAction = items['userAction']+'ed' if not items['userAction'][-1:] == 'e' else items['userAction']+'d'
            userAction = "viewed" if items["userAction"] == "history" else userAction

            flash(f"None of the selected items have sales that can be {userAction} yet.", "error")
            return redirect(url_for("sales.sales"))

        next_url = url_for(
            'sales.displaySales', page=saleHistory["saleHistoryQuery"].next_num) if saleHistory["saleHistoryQuery"].has_next else None
        prev_url = url_for(
            'sales.displaySales', page=saleHistory["saleHistoryQuery"].prev_num) if saleHistory["saleHistoryQuery"].has_prev else None

        if items["userAction"] in ["edit", "delete", "refund"]:
            # hidden is used to track which page of sales data is being displayed to the user
            adjustSaleHistoryForm = SaleHistoryAdjustForm(hidden=page)

            adjustSaleHistoryForm.sale.choices = saleHistory["saleHistoryList"]
            adjustSaleHistoryForm.submit.label.text = f"{items['userAction'].capitalize()} Sale"

            return render_template("sales/_saleEdit.html", userAction=items["userAction"], adjustForm=adjustSaleHistoryForm, form=createSaleActionForm(), next_url=next_url, prev_url=prev_url)
        else:

            # history will be a list of dictionaries with sale information
            history = [sale[1] for sale in saleHistory["saleHistoryList"]]

            return render_template("sales/_saleHistory.html", userAction=items["userAction"], history=history, form=createSaleActionForm(), next_url=next_url, prev_url=prev_url)

    return redirect(url_for("sales.sales"))


# Returns a dict that includes a list of sale information divided by page
def createSaleHistoryList(page, listOfItemNames, userAction=False):

    historyQuery = Sales.query.filter(
        Sales.username == current_user.username, Sales.itemName.in_(listOfItemNames)).order_by(Sales.date.desc()).paginate(page, 30, False)

    historyList = historyQuery.items

    # Remove any already refunded sales if userAction is editing or refunding
    if userAction in ["edit", "refund"]:
        historyList = [sale for sale in historyList if not sale.refund]

    for index, sale in enumerate(historyList):

        historyList[index] = (str(sale.id), {"itemName": sale.itemName, "date": sale.date.strftime('%m/%d/%Y'), "price": usd(sale.price), "priceWithTax": usd(
            sale.priceWithTax), "quantity": sale.quantity, "shipping": usd(sale.shipping), "profit": usd(sale.profit), "packaging": usd(sale.packaging), "refund": sale.refund})

    return {"saleHistoryQuery": historyQuery, "saleHistoryList": historyList}


# Enter a new sale or edit an existing one
@bp.route("/newSale", methods=["GET", "POST"])
@login_required
def newSale():

    # Redirect user to addItem if no items have been added yet.
    if not Items.query.filter_by(user=current_user).first():
        flash("Please add an item before adding a new sale.", "error")
        return redirect(url_for("items.addItem"))

    form = SaleForm()

    populateItemSelectField(form)

    if form.validate_on_submit():

        # If the id hidden field has data, the sale is being edited.
        if form.hidden.data:

            # Create a dictionary from form hidden data.
            hiddenData = ast.literal_eval(form.hidden.data)

            # Get sale from database.
            usersSale = Sales.query.filter_by(username=current_user.username).filter_by(
                id=hiddenData["id"]).first_or_404()

            flash(
                f"{form.items.data}'s sale on {form.date.raw_data[0]} has been edited.", "success")
        else:
            flash(f"New Sale Logged for {form.items.data}.", "success")
            # Create a new instance of the Sales model.
            usersSale = Sales()
            usersSale.username = current_user.username

        # Link userSale object to an Item object if there is not one linked or user changed item during edit
        if not form.hidden.data or not hiddenData["originalItemName"] == form.items.data:

            usersSale.item = Items.query.filter_by(
                user=current_user).filter_by(itemName=form.items.data).first_or_404()

        usersSale.date = form.date.data
        usersSale.price = str(form.price.data)
        usersSale.priceWithTax = str(
            form.priceWithTax.data) if form.priceWithTax.data else ""
        usersSale.quantity = form.quantity.data
        usersSale.shipping = str(form.shipping.data)
        usersSale.packaging = str(form.packaging.data)
        # eBay fees never include sales taxes
        usersSale.eBayFees = str(
            Decimal(form.price.data*form.eBayPercent.data).quantize(Decimal("1.00")))
        # PayPal fees include sales taxes
        usersSale.payPalFees = str(Decimal(
            (Decimal(form.priceWithTax.data) if form.priceWithTax.data else form.price.data) * form.payPalPercent.data + form.payPalFixed.data).quantize(Decimal("1.00")))

        calculateProfit(usersSale)

        db.session.add(usersSale)
        db.session.commit()

        return redirect(url_for("sales.sales"))

    else:
        # Prefill certain fields of the form
        form.date.data = date.today()
        populateFeeFields(form)
        return render_template("sales/saleInput.html", form=form, action="add")

# User has selected a specific sale to refund, delete, or edit
@bp.route("/adjustSaleHistory", methods=["POST"])
@login_required
def adjustSaleHistory():

    form = SaleHistoryAdjustForm()

    # requestItemsList is a dict containing userAction and itemsList
    try:
        requestItemsList = ast.literal_eval(current_user.saleDisplayInfo)
    except:
        flash("Error: User must have a saleDisplayInfo dict stored.", "error")
        return redirect(url_for("sales.sales"))

    if requestItemsList:

        # Populate sale choices to pass validation
        form.sale.choices = createSaleHistoryList(int(
            form.hidden.data), requestItemsList["itemsList"], requestItemsList["userAction"])["saleHistoryList"]

        if form.validate_on_submit():

            saleToAdjust = Sales.query.filter_by(username=current_user.username).filter_by(
                id=int(form.sale.data)).first_or_404()

            if requestItemsList["userAction"] == "delete":

                flash(
                    f"A sale from {saleToAdjust.itemName} made on {saleToAdjust.date.strftime('%m/%d/%Y')} has been deleted.", "success")

                db.session.delete(saleToAdjust)
                db.session.commit()

            elif requestItemsList["userAction"] == "edit":

                # Create a SaleForm that will be prepopulated
                saleFormToEdit = SaleForm()

                populateItemSelectField(saleFormToEdit)
                saleFormToEdit.items.data = saleToAdjust.item.itemName

                # Store a dictionary with information used to process an edit on the newSale route
                saleFormToEdit.hidden.data = {
                    "id": saleToAdjust.id, "originalItemName": saleToAdjust.item.itemName}

                saleFormToEdit.date.data = saleToAdjust.date
                saleFormToEdit.price.data = Decimal(saleToAdjust.price)
                saleFormToEdit.priceWithTax.data = Decimal(
                    saleToAdjust.priceWithTax)
                saleFormToEdit.quantity.data = saleToAdjust.quantity
                saleFormToEdit.shipping.data = Decimal(saleToAdjust.shipping)
                saleFormToEdit.packaging.data = Decimal(saleToAdjust.packaging)
                populateFeeFields(saleFormToEdit)

                return render_template("sales/saleInput.html", form=saleFormToEdit, action="edit")

            elif requestItemsList["userAction"] == "refund":

                saleToAdjust.refund = True
                calculateProfit(saleToAdjust, True)
                db.session.add(saleToAdjust)
                db.session.commit()
                flash(
                    f"Refund issued for {saleToAdjust.itemName} sold on {saleToAdjust.date.strftime('%m/%d/%Y')}. Loss is {saleToAdjust.profit}.", "success")

    return redirect(url_for("sales.sales"))


@bp.route("/downloadCSV", methods=["GET"])
@login_required
def downloadCSV():

    createCSV()

    return redirect(url_for('static', filename='eBaySales.csv'))
