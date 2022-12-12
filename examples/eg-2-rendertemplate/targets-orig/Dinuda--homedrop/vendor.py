from flask import redirect, render_template
import requests
import datetime



def vendorDetail(mysql , vendorid):
    cur = mysql.connection.cursor()
    cur.execute("SELECT vendors.id, vendors.name, vendors.site ,categories.name FROM home_delivery.vendors left outer join home_delivery.categories on (vendors.category =categories.id ) where vendors.id =" + vendorid + ";")
    vendor = cur.fetchall()

    #get phone numbers
    cur.execute("SELECT * FROM home_delivery.contacts where vendor=" + vendorid + ";")
    phones = cur.fetchall()
    print(phones)

    #get images for vendor
    cur.execute("SELECT * FROM home_delivery.images where vendor=" + vendorid + ";")
    images = cur.fetchall()
    print(images)

    return render_template('vendor.html' , vendor=vendor[0],  phones=phones, images = images  )


def vendorSendMessage(mysql, message, vendor_phone, vendorid,  user_phone ):
    cursor = mysql.connection.cursor()
    now = datetime.datetime.now()
    cursor.execute("INSERT INTO home_delivery.orders(user_phone , vendor_phone, message , vendor , time) VALUES (%s, %s, %s, %s, %s)", (user_phone , vendor_phone, message , vendorid, now))
    mysql.connection.commit()
    cursor.close()
    message_sent = "Your message is sent"
    vendor_message = "Hello you have a new order from: " + user_phone + ". Order is :" +message
    print (vendor_message)
    url = 'http://www.textit.biz/sendmsg?id=94767819556&pw=6476&to=' + vendor_phone + '&text=' + vendor_message  + message_sent
    print(url)
    requests.get(url)
    return redirect('/vendor?id=' + vendorid + '&notification=' + message_sent)

