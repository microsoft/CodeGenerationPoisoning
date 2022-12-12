from flask import Flask, render_template, redirect, Blueprint, request
from project import mail
from flask_mail import Message
from flask_login import login_required
from .forms import ContactForm
main = Blueprint('main', __name__)



@main.route('/')
def index():
    return render_template('home.html')

@main.route('/about')
def about():
    return render_template('about.html')

@main.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            msg = Message(form.subject.data, 
                          sender='maciek.kraczla@gmail.com', 
                          recipients=['maciek.kraczla@gmail.com'])
            msg.body = f"""
            From: {form.name.data} &lt;{form.email.data}&gt;
            {form.message.data}
            """
            mail.send(msg)
        
            return render_template('contact.html', success=True)
            
    if request.method == 'GET':
        return render_template('contact.html', form=form)
    

@main.route('/docs')
def docs():
    return render_template('docs.html')
