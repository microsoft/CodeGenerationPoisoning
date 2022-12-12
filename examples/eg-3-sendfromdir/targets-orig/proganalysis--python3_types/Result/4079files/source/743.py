import wave
import os
import os.path
from os.path import join
from tempfile import mkstemp

from flask import Flask, request, send_file, after_this_request, abort, make_response, send_from_directory, abort

try:
    from cp_decode import decode_audio
    from cp_encode import encode_ogg
    codecs_enabled = True
except OSError as e:
    print('Error loading audio codec libraries, this functionality will be disabled')
    codecs_enabled = False

app = Flask(__name__)
app.config['DEBUG'] = True


@app.route('/decode', methods=['POST', 'PUT'])
def decode():
    if not codecs_enabled:
        return 'decoding not enabled', 500

    if request.files:
        k = list(request.files.keys())
        uploaded_file = request.files[k[0]]
        fh, temp_path = mkstemp()
        fh = os.fdopen(fh, 'wb')
        wav = wave.open(fh, 'wb')
        decode_audio(uploaded_file.stream, wav)
        wav.close()
        print(temp_path)
        
        @after_this_request
        def remove_file(response):
            os.remove(temp_path)
            return response
        return send_file(temp_path, mimetype='audio/wav', attachment_filename='f.wav')
    else:
        return 'decode: no files uploaded {}'.format(request.files)


@app.route('/encode', methods=['POST', 'PUT'])
def encode():
    if not codecs_enabled:
        return 'encoding not enabled', 500
    if request.files:
        k = list(request.files.keys())
        uploaded_file = request.files[k[0]]
        filename = encode_ogg(uploaded_file.stream)
        print(filename)
        @after_this_request
        def remove_file(response):
            os.remove(filename)
            return response
        return send_file(filename, mimetype='binary/octet-stream', attachment_filename='e.bin')
    else:
        return 'decode: no files uploaded {}'.format(request.files)


@app.route('/audio/<filename>')
def download_audio(filename: str):
    if filename.endswith('.wav'):
        if not codecs_enabled:
            return 'codecs not enabled', 500
        wavpath = join('wav', filename)
        print('encoding wav file {}'.format(wavpath))
        if os.path.isfile(wavpath):
            wav = open_wav(wavpath)
            audiobytes = encode_audio(wav)
            response = make_response(audiobytes)
            response.headers['content-type'] = 'binary/octet-stream'
            response.headers['access-control-allow-origin'] = '*'
            return response
        else:
            abort(404)
    elif filename.endswith('.au'):
        print('sending pre-encoded au file {}'.format(filename))
        response = send_from_directory('au', filename)
        response.headers['access-control-allow-origin'] = '*'
        return response

@app.route('/au/<filename>')
def s(filename):
    return send_from_directory('au', filename)

@app.route('/')
def index():
    return send_file('static/cloudpets.html', mimetype='text/html')

@app.route('/static/<filename>')
def rstatic(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, use_reloader=True)


    

