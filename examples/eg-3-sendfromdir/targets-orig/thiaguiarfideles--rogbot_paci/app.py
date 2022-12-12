import os
from flask import Flask, render_template, request, redirect, url_for
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.trainers import ListTrainer
from chatterbot.logic.logic_adapter import LogicAdapter
from chatterbot.logic.best_match import BestMatch
from chatterbot.logic.specific_response import SpecificResponseAdapter
from chatterbot.logic.time_adapter import TimeLogicAdapter
from chatterbot.logic.unit_conversion import UnitConversion
from nltk.corpus import wordnet, stopwords
from datetime import datetime
from chatterbot.comparisons import levenshtein_distance
from importlib import reload
from waitress import serve



app = Flask(__name__)



rog_bot = ChatBot(
    "ROGBOT",
    trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)

rog_bot = ChatBot("Chatterbot", storage_adapter='chatterbot.storage.SQLStorageAdapter',
    database_uri='sqlite:///database.sqlite3',
	logic_adapters=[
                {
                    'import_path': 'chatterbot.logic.BestMatch',
                    "response_selection_method": "chatterbot.response_selection.get_random_response",
                    'maximum_similarity_threshold': 0.65
                }
                
            ],

    preprocessors=[
        'chatterbot.preprocessors.clean_whitespace','chatterbot.preprocessors.unescape_html','chatterbot.preprocessors.convert_to_ascii'],
    silence_performance_warning=True,
    filters=["chatterbot.filters.RepetitiveResponseFilter"],
    statement_comparison_function=["levenshtein_distance"],
    
)
trainer = ChatterBotCorpusTrainer(rog_bot)
trainer.train("chatterbot.corpus.portuguese")

rog_bot = ChatBot(
    'ROGBOT',
    trainer='chatterbot.trainers.ChatterBotCorpusTrainer'
)

trainer = ChatterBotCorpusTrainer(rog_bot)
trainer.train(
'chatterbot.corpus.portuguese.conversations',
'chatterbot.corpus.portuguese.greetings',
'chatterbot.corpus.portuguese.prescricoes',
'chatterbot.corpus.portuguese.checagem_solucao',
'chatterbot.corpus.portuguese.checagem_medicamentos',
'chatterbot.corpus.portuguese.checagem_dietas',
'chatterbot.corpus.portuguese.checagem_dispositivos',
'chatterbot.corpus.portuguese.checagem_gasoterapia',
'chatterbot.corpus.portuguese.checagem_glicemia',
'chatterbot.corpus.portuguese.Pacote',
'chatterbot.corpus.portuguese.Recuperar_conta_excluida',
'chatterbot.corpus.portuguese.Fixar_Simpro_Brasindice'
)


@app.route("/get-image/<image_name>")
def download_file(filename):
    return send_from_directory(app.config['ROGBOT_IMAGES'],
                               filename, as_attachment=True)



@app.route("/")
def home():
    return render_template("index.html")

@app.route("/get")
def get_bot_response():
    userText = request.args.get('msg')
    return str(rog_bot.get_response(userText))



if __name__ == '__main__':
    app.run(debug=True)