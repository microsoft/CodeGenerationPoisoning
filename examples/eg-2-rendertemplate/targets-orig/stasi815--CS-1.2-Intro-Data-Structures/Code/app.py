from flask import Flask, render_template
from random import randint, uniform
from word_frequency_analysis import load_text, dict_histogram
from markov_chain import second_order_markov_histo, markov_run

app = Flask(__name__)

@app.route('/')
def rand_sentence_generator():
    """Returns a random sentence based on weighted word probability."""
    filename = 'corpus_texts/bhagavad_gita.txt'
    word_list = load_text(filename)
    markov_histos = second_order_markov_histo(word_list)
    steps = randint(5, 15)
    sentence = markov_run(markov_histos, steps)


    random_sentence = " ".join(sentence).capitalize() + "."
    return render_template("index.html", sentence=random_sentence)


if __name__ == '__main__':
    # app.debug = True
    app.run(debug=True, host='0.0.0.0', port=os.environ.get('POST', 5000))