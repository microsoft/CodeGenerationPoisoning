from flask import Flask, render_template, request, Response, jsonify
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

stream = ''
_action = _intent = 'Waiting...'
_intent_panel = {'labels':['None']*3, 'probs':[0.0]*3}
isChange = True
cnt = 0
_intent_hist = ['Waiting...']

def gen_for_livecam():
    while True:
        yield b'--frame\r\n' \
              b'Content-Type: image/jpeg\r\n\r\n' + stream + b'\r\n\r\n'
        sleep(0.01)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_stream', methods=['GET', 'POST'])
def update_stream():
    global stream
    stream = request.data  # update stream
    return 'complete'

@app.route('/state/set/action')
def set_action():
    global _action
    _action = request.args.get('action') # update action
    return 'complete'

@app.route('/state/set/intent')
def set_intent():
    global _intent, _intent_hist
    _intent = request.args.get('intent') # update intent
    if _intent != 'Waiting...':
        _intent_hist.append(_intent)
    return 'complete'

@app.route('/state/set/intent_panel')
def set_intent_panel():
    global _intent_panel, isChange

    prev_panel = _intent_panel

    _intent_panel = {"labels": eval(request.args.get("intent_labels")),
                     "probs": eval(request.args.get("intent_probs"))}

    isChange = (prev_panel!=_intent_panel)

    return 'complete'

@app.route('/state/get/action')
def get_action():
    return jsonify(action=_action)

@app.route('/state/get/intent')
def get_intent():
    return jsonify(intent=_intent)

@app.route('/state/get/intent_from_history')
def get_intent_from_history():
    return jsonify(intent=_intent_hist[-1])

@app.route('/state/get/intent_panel')
def get_intent_panel():
    return jsonify(labels=_intent_panel["labels"],
                   probs=_intent_panel["probs"],
                   isChange=isChange)

@app.route('/live_cam')
def live_cam():
    # global stream
    return Response(gen_for_livecam(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
    #app.run(host='127.0.0.1', port=5001)
