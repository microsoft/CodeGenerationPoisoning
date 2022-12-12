from flask import Flask, request,render_template
from rivescript import RiveScript
import os
from gtts import gTTS

app = Flask(__name__)

file = os.path.dirname(__file__)
brain = os.path.join(file,'brain')

bot = RiveScript()
bot.load_directory(brain)
bot.sort_replies()

@app.errorhandler(404)
def page_not_found(e):
    # note that we set the 404 status explicitly
    return render_template('404.html')

@app.route('/')
def callchat():
    return render_template('index.html')

@app.route('/homepage')
def callHome():
    return render_template('index.html')

@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    message = (bot.reply('localuser', userText))
    return  str(message)

if __name__ == '__main__':
    app.run()