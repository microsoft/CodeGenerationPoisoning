# coding=utf-8
__author__ = 'ealexand'

import os
import csv
import zipfile
from flask import render_template, request, Response, current_app, url_for, redirect, jsonify, json
import Utilities as util

def get_tokens_fromCSV(model_name, text_name):
    html_root = os.path.join(util.get_model_root(model_name), 'HTML')
    if os.path.exists(html_root + '.zip'):
        with zipfile.ZipFile(html_root + '.zip') as zf:
            with zf.open('HTML/%s/tokens.csv' % text_name) as csvF:
                reader = csv.reader(csvF)
                return [row for row in reader]
    else:
        if text_name in os.listdir(html_root):
            currHTMLdir = os.path.join(html_root, text_name)
            with open(os.path.join(currHTMLdir, 'tokens.csv'), 'rb') as csvF:
                reader = csv.reader(csvF)
                return [row for row in reader]
        else:
            return

def get_tokens_json(model_name, text_name):
    tokens = get_tokens_fromCSV(model_name, text_name)
    jTokens = jsonify({'tokens': tokens})
    return jTokens

def view_by_name(model_name, text_name):
    tokenList = get_tokens_fromCSV(model_name, text_name)
    return render_template(
        "slimTV.html",
        model_name=model_name,
        text_name=text_name,
        tokens=tokenList
    )

def single_view_by_name():
    return render_template(
        'slimTV_single.html'
    )

def single_fromURL_view_by_name(tokens_url):
    return render_template(
        'slimTV_fromURL.html',
        tokens_url=tokens_url
    )