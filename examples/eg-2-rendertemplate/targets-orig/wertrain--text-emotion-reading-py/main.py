import os
import logging
from flask import Flask, render_template, request, url_for
import emotion_score

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/analysis', methods=['POST'])
def analysis():
    text = request.form['text']

    scores = emotion_score.calc_emotion_score(text)
    _, max_emotion_keys = emotion_score.get_max_emotion_score(scores)

    emotion_key_to_emoji_dict = {
        'yorokobi':'smile',
        'ikari':'angry',
        'aware':'cry',
        'kowa':'fearful',
        'haji':'flushed', 
        'suki':'heart_eyes',
        'iya':'confounded',
        'takaburi':'triumph',
        'yasu':'relaxed',
        'odoroki':'open_mouth',
        '':'expressionless' 
    }
    emotion_key_to_japanese_dict = {
        'yorokobi':'喜び',
        'ikari':'怒り',
        'aware':'哀しい',
        'kowa':'怖い',
        'haji':'恥', 
        'suki':'好き',
        'iya':'厭',
        'takaburi':'昂ぶり',
        'yasu':'安らぎ',
        'odoroki':'驚き',
        '':'なし'
    }

    icon = emotion_key_to_emoji_dict['']
    overview = '感情が読み取れない文章です'

    if (len(max_emotion_keys) > 0):
        overview = ''
        for key in max_emotion_keys:
            icon = emotion_key_to_emoji_dict[key]
            overview += '「' + emotion_key_to_japanese_dict[key] + '」' 
        overview += 'の感情が強い文章です'

    return render_template(
        'analysis.html',
        text=text,
        result=scores,
        overview=overview,
        icon=icon)

@app.errorhandler(500)
def server_error(e):
    logging.exception('An error occurred during a request.')
    return 'An internal error occurred.', 500

@app.context_processor
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                 endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

if __name__ == "__main__":
    app.run(debug=True)
