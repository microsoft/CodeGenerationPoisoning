# Libraries imports
import os
from flask import Flask, render_template , request
from state import LIA_response
import time

# Author of the code
auth = "Tran Raphaël"

# Define flask application
app = Flask(__name__)

# Secret key to secure transactions
app.config['SECRET_KEY'] = 'a7849f59f9eb4d40cd48e3c4c4e6f2f1'
# Define Socket object


# Default route
@app.route('/')
def index():
    return render_template('index.html')

# route towards the chatbot
@app.route('/chatbot')
def chat():

    return render_template('chat.html')

# route towards legal mentions
@app.route('/mentions_legales')
def mentions():
    return render_template('mentions_legales.html')

# route towards contact
@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/post', methods = ['POST'])
def chat_bot_post():
    # Json Structure received :
    #json_response = {
    #    response: user_input,
    #    state: val_state,
    #    name : val_name,
    #    classe : val_classe,
    #    school : val_school,
    #    school_infos : val_school_infos,
    #    discussion : val_discussion, 
    #    harc_name : val_harc_name,
    #}
    user_json = request.get_json()
    print(user_json)
    res = LIA_response(user_json)
    return res

# Helps easy debug by running python from command line
if (__name__ == '__main__'):
    # Multi process for production
    # app.run(threaded = True) 
    app.run(debug = True)  
