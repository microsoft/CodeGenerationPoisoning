from flask import Flask, request, Response, render_template, jsonify
import getSong
import playVLC
import json
import base64

from playVLC import Song

app = Flask(__name__)  # create the Flask app
stream_song = Song()


# RaspberryPI
# https://0lt6bbtf0hbp2knmhts63g.webrelay.io/api/v1/play_music

# Windows10
# https://thbdqxnhzjqwpp432sgi2k.us-west.webrelay.io/api/v1/play_music

def encode_base64(message):
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')

    return base64_message


def decode_base64(base64_message):
    base64_bytes = base64_message.encode('ascii')
    message_bytes = base64.b64decode(base64_bytes)
    message = message_bytes.decode('ascii')

    return message


@app.route('/base64')
def index():
    return render_template('index.html')


@app.route('/', methods=['GET'])
def home():
    return '''<h1>Distant Reading Archive</h1>
<p>A prototype API for playing Google Music.</p>'''


@app.route('/api/v1/play_music', methods=['POST'])
def play_song():
    content = request.json
    try:
        print(json.dumps(content, indent=4))
        content = content['queryResult']['parameters']['action'].strip('"')
        if content == 'stop':
            response_text = "{'payload':{'google':{'expectUserResponse':false,'richResponse':{'items':[{'simpleResponse':{'textToSpeech':'OK! music stopped'}}]}}}}"
            stream_song.stop_song()
        elif content == 'our_song':
            track = getSong.ask_for_song('Africa by Toto')
            stream_url = track[2]
            stream_song.play_song(stream_url)
            response_text = "{'payload':{'google':{'expectUserResponse':true,'richResponse':{'items':[{'simpleResponse':{'textToSpeech':'OK! playing " + \
                            track[0] + " by " + track[1] + "'}}]}}}}"
            print(response_text)

    except:
        song = content['queryResult']['parameters']['song'][0].strip('"')
        print(song)
        track = getSong.ask_for_song(song)
        stream_url = track[2]
        stream_song.play_song(stream_url)
        response_text = "{'payload':{'google':{'expectUserResponse':true,'richResponse':{'items':[{'simpleResponse':{'textToSpeech':'OK! playing " + \
                        track[0] + " by " + track[1] + "'}}]}}}}"
        print(response_text)

    return Response(response_text, status=201, mimetype='application/json')


@app.route('/api/v1/resources/base64', methods=['GET'])
def api_all():
    if 'fstring' in request.args:
        fstring = request.args['fstring']
    else:
        return "Error: No fstring field provided. Please specify an fstring."
        # Create an empty list for our results
    if 'type' in request.args:
        type = request.args['type']
    else:
        return "Error: No type field provided. Please specify an type."
        # Create an empty list for our results

    if type.lower() == 'encode':
        base64_message = encode_base64(fstring)
        return base64_message
    elif type.lower() == 'decode':
        message = decode_base64(fstring)
        return message
    else:
        return "Please specify type 'encode' or 'decode'"


app.run(debug=True, port=8080)  # run app in debug mode on port 5000
