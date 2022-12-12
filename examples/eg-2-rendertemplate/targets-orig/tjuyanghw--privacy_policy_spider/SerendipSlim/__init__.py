# coding=utf-8

import os
import json
import sys
from flask import Flask, url_for, redirect, render_template, send_from_directory
import Utilities
import CorpusViewer
import TextViewer
import RankViewer
from Support.flask_util_js.flask_util_js import FlaskUtilJs
from config import DevelopmentConfig

runSentry = False
try:
    from raven.contrib.flask import Sentry
    sentryInstalled = True
except:
    print 'Raven not installed--Sentry will not be run.'
    sentryInstalled = False

#########################
#### Flask App Setup ####
#########################

app = Flask(__name__)
# Load some sweet Jinja2 extensions
app.jinja_options = dict(
    extensions=[
        'jinja2.ext.do',
        'jinja2.ext.autoescape'
    ]
)
# Load the configuration object.
#app.config.from_object("config.DevelopmentConfig")
app.config.from_object(DevelopmentConfig)
# For flask_util.url_for() in JavaScript: https://github.com/dantezhu/flask_util_js
fujs = FlaskUtilJs(app)

# Sentry
if runSentry and sentryInstalled:
    try:
        app.config['SENTRY_DSN'] = 'https://d3db637793f0492cbd5c8b7a65ca14ba:7718f1be2a114e8ea5314311252c2987@app.getsentry.com/78772'
        sentry = Sentry(app)
    except RuntimeError as err:
        print 'Error trying to run Sentry:', err

def get_colors():
    colors_str_prefix = "app_colors = "
    colors_path = os.path.join(
        app.static_folder,
        "js",
        "app_colors.json"
    )
    colors_file = open(colors_path, "rU")
    colors_str = colors_file.read()
    colors_file.close()
    if colors_str.startswith(colors_str_prefix):
        colors_str = colors_str[len(colors_str_prefix):]
    colors = json.loads(colors_str)
    return colors

# Add the colors to the app configuration.
app.config.update(
    COLORS=get_colors()
)

########################################
# Index Redirection to CorpusViewer ####
########################################

@app.route("/")
def index():
    return redirect(
        url_for(
            "cv_view_by_name",
            model_name=app.config["DEFAULT_MODEL_NAME"]
        )
    )

############################################
# TESTING CODE FOR BIG THETA AND OTHERS ####
############################################

@app.route('/bigThetaTest')
def bigThetaTest():
    return render_template(
        'BigThetaTest.html'
    )

######################
#### CorpusViewer ####
######################

# Redirect to matrix view for "/model:<model_name>/"
@app.route('/model:<path:model_name>/')
def redirect_corpus_view(model_name):
    return redirect(
        url_for(
            "cv_view_by_name",
            model_name=model_name
        )
    )

app.add_url_rule(
    '/model:<path:model_name>/matrix',
    "cv_view_by_name",
    CorpusViewer.view_by_name
)

app.add_url_rule(
    '/model:<path:model_name>/_getMetadata',
    "cv_get_metadata",
    CorpusViewer.get_metadata
)

app.add_url_rule(
    '/model:<path:model_name>/_getTheta',
    "cv_get_theta",
    CorpusViewer.get_theta
)

app.add_url_rule(
    '/model:<path:model_name>/_setGroupName/<group_file>/<group_name>/<group>',
    "cv_set_group_name",
    CorpusViewer.set_group_name
)

app.add_url_rule(
    '/model:<path:model_name>/_getGroups/<group_file>',
    "cv_get_groups",
    CorpusViewer.get_groups
)

app.add_url_rule(
    '/model:<path:model_name>/_getAnovaOrder/<fieldName>',
    "cv_get_anova_order",
    CorpusViewer.getAnovaOrder
)

app.add_url_rule(
    '/model:<path:model_name>/_getContrastOrder/<fieldName>/<group1>/<group2>',
    "cv_get_contrast_order",
    CorpusViewer.getContrastOrder
)

####################
#### TextViewer ####
####################

app.add_url_rule(
    '/slimTV/',
    'tv_single_view_by_name/',
    TextViewer.single_view_by_name
)

app.add_url_rule(
    '/slimTV/tokens_url:<path:tokens_url>',
    'tv_single_fromURL_view_by_name/',
    TextViewer.single_fromURL_view_by_name
)

app.add_url_rule(
    '/slimTV/model:<path:model_name>/text:<text_name>/',
    'tv_view_by_name',
    TextViewer.view_by_name
)

app.add_url_rule(
    '/_getTokens/model:<path:model_name>/text:<text_name>/',
    'tv_get_tokens_json',
    TextViewer.get_tokens_json
)

###################
#### Utilities ####
###################

app.add_url_rule(
    '/model:<path:model_name>/_getTopic/<topic_num>/<num_words>/<ranking_type>',
    "utils_get_topic",
    Utilities.get_topic
)

app.add_url_rule(
    '/model:<path:model_name>/_getTopicNames/',
    "utils_get_topic_names",
    Utilities.get_topic_names
)

app.add_url_rule(
    '/model:<path:model_name>/_setTopicName/<topic_num>/<topic_name>/<num_topics>',
    "utils_set_topic_name",
    Utilities.set_topic_name
)

app.add_url_rule(
    '/model:<path:model_name>/_getRankingTypes',
    "utils_get_ranking_types",
    Utilities.get_ranking_types
)

#######################################
#### EXTRA (WORDRANKINGS AND SUCH) ####
#######################################

'''
app.add_url_rule(
    '/model:<path:model_name>/meso',
    "cv_mesoview",
    CorpusViewer.mesoview
)

app.add_url_rule(
    '/_getCorpora',
    "get_corpora",
    Utilities.get_corpora
)
'''
app.add_url_rule(
    '/model:<path:model_name>/_get_word_rankings/<rankingType>/<words>',
    'get_word_rankings_json',
    RankViewer.get_word_rankings_json
)

app.add_url_rule(
    '/model:<path:model_name>/wordRankings/<rankingType>/<wordColorPairs>',
    'wordRankings',
    RankViewer.wordRankings
)

app.add_url_rule(
    '/model:<path:model_name>/wordRankings/',
    'wordRankingsDefault',
    RankViewer.wordRankingsDefault
)

app.add_url_rule(
    '/model:<model_name>/get_word_ranking/<rankingType>/<word>',
    'get_word_ranking',
    RankViewer.get_word_ranking
)


#################
#### Run it! ####
#################

if __name__ == '__main__':
    if len(sys.argv) > 1:
        app.config.update(
            METADATA_ROOT=sys.argv[1]
        )

    app.run(port=5001)
