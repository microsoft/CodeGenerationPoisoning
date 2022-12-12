# coding=utf-8
__author__ = 'kohlmannj'

from flask import jsonify, render_template
import os
import glob
import csv
import Utilities as util

def _get_word_rankings(model_name, words, rankingType='sal'):
    topicDir = os.path.join(util.get_model_root(model_name), 'topics_%s' % rankingType)
    numTopics = len(glob.glob(os.path.join(topicDir, 'topic_*.csv')))
    rankings = {}
    for word in words:
        rankings[word] = [ -1 for i in range(numTopics) ]
    wordsPerTopic = [ 0 for i in range(numTopics) ]
    maxWordsPerTopic = 0
    for topic in range(numTopics):
        with open(os.path.join(topicDir, 'topic_%d.csv' % topic), 'rb') as topicF:
            topicReader = csv.reader(topicF)
            currRow = 0
            for row in topicReader:
                if row[0] in words:
                    rankings[row[0]][topic] = currRow
                currRow += 1
            wordsPerTopic[topic] = currRow
            maxWordsPerTopic = max(maxWordsPerTopic, currRow)
    return {'rankings': rankings, 'wordsPerTopic':wordsPerTopic, 'maxWordsPerTopic':maxWordsPerTopic}

def get_word_ranking(model_name, word, rankingType='sal'):
    topicDir = os.path.join(util.get_model_root(model_name), 'topics_%s' % rankingType)
    numTopics = len(glob.glob(os.path.join(topicDir, 'topic_*.csv')))
    ranking = [ -1 for i in range(numTopics) ]
    for topic in range(numTopics):
        with open(os.path.join(topicDir, 'topic_%d.csv' % topic), 'rb') as topicF:
            topicReader = csv.reader(topicF)
            currRow = 0
            for row in topicReader:
                if row[0]==word:
                    ranking[topic] = currRow
                currRow += 1
    return jsonify({'ranking': ranking})

def get_word_rankings_json(model_name, words, rankingType='sal'):
    words = words.split(',')
    return jsonify(_get_word_rankings(model_name, words, rankingType))

def wordRankings(model_name, wordColorPairs, rankingType='sal'):
    words = []
    colors = []
    if wordColorPairs != 'empty':
        for pair in wordColorPairs.split(','):
            word, color = pair.split(':')
            words.append(word)
            colors.append(color)
    wr = _get_word_rankings(model_name, words, rankingType)
    wr['words'] = words
    wr['colors'] = colors

<orig>
    return render_template(
        'slimRV.html',
        model_name=model_name,
        rankingsObject=wr,
        rankingType=rankingType
    )
<orig>

<vuln>
    with open( 'slimRV.html') as f:
    	return jinja2.Template(f.read()).render(model_name=model_name, rankingsObject=wr, rankingType=rankingType)
<vuln>


def wordRankingsDefault(model_name):
    return wordRankings(model_name, 'empty', 'sal')