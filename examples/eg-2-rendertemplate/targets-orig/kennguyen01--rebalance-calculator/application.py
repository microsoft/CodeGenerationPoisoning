#!/usr/bin/env python3

import os
from flask import Flask, flash, redirect, render_template, request, url_for

from portfolio import Portfolio

app = Flask(__name__)
secret_key = os.urandom(24).hex()
app.secret_key = secret_key

user_portfolio = Portfolio()


@app.route("/rebalance-calculator", methods=["GET", "POST"])
def index():
    user_portfolio.reset_portfolio()
    user_portfolio.reset_total()
    return render_template("index.html")


@app.route("/rebalance-calculator/about", methods=["GET"])
def about():
    return render_template("about.html")


@app.route("/rebalance-calculator/instructions", methods=["GET"])
def instructions():
    return render_template("instructions.html")


@app.route("/rebalance-calculator/info", methods=["GET", "POST"])
def info():
    """
    Receives string of tickers entered by user and build a portfolio
    Accesses each ticker data but flashes message when given incorrect ticker
    """
    if request.method == "POST":
        user_inputs = request.form.get("user-tickers")
        user_portfolio.build_portfolio(user_inputs)

    user_portfolio.set_ticker_data()

    # Checks if user enters any invalid ticker
    invalid = user_portfolio.get_invalid()
    if len(invalid) == 1:
        flash("{} is an invalid ticker".format(invalid[0]))
        return redirect(url_for("index"))
    elif len(invalid) > 1:
        flash("{} are invalid tickers".format(", ".join(invalid)))
        return redirect(url_for("index"))

    portfolio = user_portfolio.get_portfolio()
    return render_template("info.html", portfolio=portfolio)


@app.route("/rebalance-calculator/result", methods=["POST"])
def result():
    """
    Calculates optimal rebalanced portfolio given desired allocations
    """

    balances = request.form.getlist("balances")
    allocations = request.form.getlist("allocations")
    contribution = request.form.get("contribution")

    # Checks if total allocations is 100%
    correct = user_portfolio.set_target_allocation(allocations)
    print(correct)
    if not correct:
        flash("Total allocation does not equal 100%")
        # Total balance needs to be reset, otherwise it's added on top of next inputs
        user_portfolio.reset_total()
        return redirect(url_for("info"))

    user_portfolio.set_ticker_balance(balances)
    user_portfolio.set_total_balance(contribution)
    user_portfolio.rebalance()

    portfolio = user_portfolio.get_portfolio()
    return render_template("result.html", portfolio=portfolio)
