from flask import Flask
from flask import Flask, flash, redirect, render_template, request, session, abort
import os
from flask import g
import requests
from flask import Response
from flask import send_from_directory

import database
import index
import vendor
import company

application = Flask(__name__,  static_url_path='',
            static_folder='static', template_folder='templates')

mysql = database.getDatabase(application)

@application.context_processor
def inject_filter_menu():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM home_delivery.locations ORDER BY location ;")
    locations = cur.fetchall()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM home_delivery.categories;")
    categories = cur.fetchall()

    return dict(locations=locations, categories=categories)


# ?category=1&location=2
@application.route('/')
def homePage():
    locationId = request.args.get("location")
    categoryId = request.args.get("category")
    return index.homepage(mysql, locationId, categoryId)


@application.route('/vendor')
def vendorDetail():
    vendorid = request.args.get("id")
    return vendor.vendorDetail(mysql ,vendorid)

@application.route('/newuser', methods=['GET', 'POST'])
def newuser():
    return render_template('user_signup.html')

@application.route('/user_reg', methods=['POST'])
def user_reg():
    name = request.form['name']
    email = request.form['email']
    passw = request.form['passw']
    phone = request.form['phone']
    detail = request.form['detail']
    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO home_delivery.contacts(vendorid , phone , detail) VALUES (%s,%s,%s)",(vendorid , phone , detail))    
    mysql.connection.commit()   
    cursor.close() 

@application.route('/submit_insert_location',methods=['POST'])
def company_location():
    location = request.form['location']
    vendor = request.form['vendor']
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO home_delivery.vendor_locations(vendor, location) VALUES (%s, %s)",(vendor, location))
    mysql.connection.commit()
    cur.close()
    return redirect('/edit_company?id=' + str(vendor)) 

@application.route('/delete_location' , methods=['GET'])
def delete_location():
    id = request.args.get("id")
    vendor_id = request.args.get("vendorid")
    return company.editDeleteLocation(mysql, id, vendor_id)

@application.route('/edit_company')
def create_company():
    id = request.args.get("id")
    return company.editCompany(mysql, id)

@application.route('/submit_edit_company' , methods=['POST'])
def new_comp():
    name = request.form['name']
    site = request.form['site']
    category = request.form['category']
    id = request.form.get('id')                 
    return company.editSubmit(mysql, name, site, category, id)

@application.route('/submit_flyer_edit_company', methods= ['POST'])
def submit_flyer_edit_company():
    id = request.form['id']
    upload = request.files['upload']
    return company.editFlyer(mysql,id, upload)


@application.route('/submit_contacts_edit_company' , methods= ['POST'])
def submit_contacts_edit_company():
    vendor = request.form['id']
    print(vendor)
    contact = request.form['contact']

    detail =  ''
    if request.form.get('detail'):
        detail = request.form.get('detail')

    whatsapp = 0
    if request.form.get('whatsapp'):
        whatsapp = 1

    viber = 0
    if request.form.get('viber'):
        viber = 1

    call = 0
    if request.form.get('call'):
        call = 1

    SMS = 0
    if request.form.get('SMS'):
        SMS = 1

    print(whatsapp)
    print(viber)
    print(call)
    print(SMS)
    return company.editContact(mysql,vendor,contact,detail,whatsapp,viber,call,SMS)

@application.route('/img/<path:filename>')  
def send_file(filename):  
    return send_from_directory('images/', filename)

@application.route('/delete_img' )
def delete_img():
    id = request.args.get("id")
    vendor = request.args.get("vendor")
    return company.editDeleteImg(mysql,id,vendor)

@application.route('/delete_phone')
def delete_phone():
    id = request.args.get("id")
    vendor = request.args.get("vendor")
    return company.editDeleteContact(mysql, id, vendor)
   
@application.route('/submit_message', methods=['POST'])
def submit_message():
    message = request.form['message']
    vendor_phone = request.form['vendor_phone']
    vendorid = request.form['vendor']
    user_phone = request.form['user_phone']
    return vendor.vendorSendMessage(mysql, message , vendor_phone , vendorid , user_phone)

if __name__ == "__main__":
    # Setting debug to True enables debug output. This line should be
    # removed before deploying a production app.
    application.debug = True
    application.run()
