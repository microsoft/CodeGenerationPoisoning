from flask import Flask,render_template,url_for,request, redirect
import csv
app = Flask(__name__)

@app.route('/')
def homePage():
    return render_template("index.html")


def write_to_csv(data):
    with open('database.csv',mode='a',newline='') as database:
        email = data['email']
        subject = data['subject']
        message = data['message']
        csvWrite = csv.writer(database,delimiter=",",quotechar='"',quoting=csv.QUOTE_MINIMAL)
        csvWrite.writerow([email,subject,message])


@app.route('/<string:page_name>')
def html_page(page_name):
    return render_template(page_name)

@app.route('/submit_form', methods=['POST', 'GET'])
def submit_page():
    if request.method == "POST":
        try:
            data = request.form.to_dict()
            write_to_csv(data)
            print(data)
            return redirect("/thankyou.html")
        except:
            return "Did not save to the database"
    else:
        return "Somethign went wrong"




