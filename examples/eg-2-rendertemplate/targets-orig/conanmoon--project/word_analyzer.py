from flask import Flask, render_template, jsonify, request, redirect, Response

import sys
import random, json

from operator import itemgetter
app = Flask(__name__)
import numpy as np
import pandas as pd

# from subprocess import Popen, PIPE
# from docx import opendocx, getdocumenttext
#
# #http://stackoverflow.com/questions/5725278/python-help-using-pdfminer-as-a-library
# from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
# from pdfminer.converter import TextConverter
# from pdfminer.layout import LAParams
# from pdfminer.pdfpage import PDFPage
# from cStringIO import StringIOÍ

import docx2txt

from pymongo import MongoClient           # pymongo를 임포트 하기(패키지 인스톨 먼저 해야겠죠?)
client = MongoClient('localhost', 27017)  # mongoDB는 27017 포트로 돌아갑니다.
db = client.dbsparta                      # 'dbsparta'라는 이름의 db를 만듭니다.

## HTML을 주는 부분
@app.route('/')
def home():
   return render_template('word_analyzer.html')

def remove_multiple_strings(read_text, toRemove):
    for x in toRemove:
        read_text = read_text.replace(x, ' ')
    return read_text

def sort_key(d):
    return d['word_count']

## API 역할을 하는 부분
@app.route('/words', methods=['POST'])
def saving():
    # read json + reply
    # data = request.get_json()
    # result = ''
    #
    # for item in data:
    #     # loop over every row
    #     result += str(item['make']) + '\n'
    #
    # return result
    read_text = request.form['write_text']
    # read_text = docx2txt.process(read_text)
    # print(read_text)
    read_text = read_text.lower()
    # DB에 삽입할 text 만들기
    toRemove = ["/", "-", ".", "~", ":", "&", "=", "-", "*", "!", "(", ")", ",", "\"", "\n"]
    read_text = remove_multiple_strings(read_text, toRemove)
    read_text_list = read_text.split(" ")
    read_text_list = list(filter(None, read_text_list))
    total_count = len(read_text_list)
    print(total_count)
    word_calculated_list = []
    for word in [ele for ind, ele in enumerate(read_text_list, 1) if ele not in read_text_list[ind:]]:
        word_count = read_text_list.count(word)
        word_percentage = round(100*(read_text_list.count(word)/total_count), 2)
        print("{} {} {}%".format(word, word_count, word_percentage))
        word_calculated_dict = {'word': word, 'word_count': word_count, 'word_percentage': word_percentage}
        word_calculated_list.append(word_calculated_dict)
    word_calculated_list = sorted(word_calculated_list, key=itemgetter('word_count'), reverse=True)
    text = {
       'texts': read_text_list,
        'total_count': total_count,
        'word_stat': word_calculated_list
    }

    # texts에 text 저장하기
    db.texts.insert_one(text)
    return jsonify({'result': 'success', 'stats': word_calculated_list}) # returning the word stats

@app.route('/words', methods=['GET'])
def listing():
    texts = list(db.texts.find({},{'_id':0}))
    return jsonify({'result':'success', 'texts': texts})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
