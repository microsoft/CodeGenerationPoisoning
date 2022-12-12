from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/',methods=['POST'])
def get_name():
        uname = request.form['username']
        jname = j_name(uname)
        return render_template('jname.html',uname=uname,jname=jname)

def j_name(uname):
    japanese_alphabet = {'a': 'ka', 'b': 'tu', 'c': 'mi', 'd': 'te',
                        'e': 'ku', 'f': 'lu', 'g': 'ji', 'h': 'ri',
                        'i': 'ki','j': 'zu', 'k': 'me', 'l': 'ta',
                        'm': 'rin', 'n': 'to', 'o': 'mo', 'p': 'no',
                        'q': 'ke', 'r': 'shi', 's': 'ari', 't': 'chi',
                        'u': 'do','v': 'ru', 'w': 'mei', 'x': 'na',
                        'y': 'fu', 'z': 'zi'}
    uname = uname.lower()
    translate_name = list()
    try:
        for i in uname:
            translate_name.append(japanese_alphabet[i])
    except Exception as ex:
        return 'Please check input'
    return ''.join(translate_name)
