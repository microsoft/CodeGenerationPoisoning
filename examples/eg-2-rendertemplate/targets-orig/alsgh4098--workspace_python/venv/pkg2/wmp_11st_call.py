import pkg2.WeMaPr_craw
import pkg2.st11_craw
import  pkg2.selenium_test

from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route("/")
def index():

    return render_template("index.html",  NEW_LIST_KEY = pkg2.selenium_test.WMP_Sel_Craw("삼성"), NEW_LIST_KEY2 = pkg2.st11_craw.st_11_craw())


if __name__ == "__main__" :
    app.run(host="127.0.0.1",port = "8889")
