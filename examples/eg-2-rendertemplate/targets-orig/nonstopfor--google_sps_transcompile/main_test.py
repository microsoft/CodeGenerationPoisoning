"""
Test for website without the influence of the transcompile model
"""

from flask import Flask, render_template, request, redirect, url_for
import requests
import json
import difflib
from bs4 import BeautifulSoup
import sys

app = Flask(__name__)

source = ''
result = ''
source2 = ''
result2 = ''


def compile_run(source_code, language, url='https://api.jdoodle.com/v1/execute'):
    # 先假设是python code
    if language == 'python':
        lang = 'python3'
        version = 3
    elif language == 'c++':
        lang = 'cpp17'
        version = 0
    elif language == 'java':
        lang = 'java'
        version = 3
    else:
        raise NotImplementedError('{} is not supported now!'.format(language))

    data = {
        'clientId': '5889da6be5def525ee4d6c2b7a6b2535',
        'clientSecret': '412423fa76d979ed782e12fb0d9f5852a61c8792d1390460696d2abc3d8d8717',
        'script': source_code,
        'stdin': '',
        'language': lang,
        'versionIndex': version
    }

    response = requests.post(url=url, data=json.dumps(data), headers={"Content-Type": "application/json"})
    w = json.loads(response.text)
    if 'output' in w:
        result = w['output']
    else:
        result = w['error']
    return result


@app.route('/')
def index():
    # return 'hello world'
    return render_template('index.html')


@app.route('/compile/', methods=('POST', 'GET'))
def compile():
    if request.method == 'POST':
        global source, result
        # print(request.form['code'])
        # axios请求
        data = request.get_json(silent=True)
        source = data['code']
        language = data['language']
        if language == 'cpp':
            language = 'c++'

        result = compile_run(source, language)
        print(source, result)
        return {'source': source, 'result': result}
    return redirect(url_for('index'))


def compile_run(source_code, language, url='https://api.jdoodle.com/v1/execute'):
    # 先假设是python code
    if language == 'python':
        lang = 'python3'
        version = 3
    elif language == 'c++':
        lang = 'cpp17'
        version = 0
    elif language == 'java':
        lang = 'java'
        version = 3
    else:
        raise NotImplementedError('{} is not supported now!'.format(language))

    data = {
        'clientId': '5889da6be5def525ee4d6c2b7a6b2535',
        'clientSecret': '412423fa76d979ed782e12fb0d9f5852a61c8792d1390460696d2abc3d8d8717',
        'script': source_code,
        'stdin': '',
        'language': lang,
        'versionIndex': version
    }

    response = requests.post(url=url, data=json.dumps(data), headers={"Content-Type": "application/json"})
    w = json.loads(response.text)
    if 'output' in w:
        result = w['output']
    else:
        result = w['error']
    return result


def split_by_indent(source_code):
    # 根据缩进分割python代码中的多个函数
    # 算法：python函数一定以def开头且def前面没有多余的缩进或空格，识别这样的line即可

    fragment = []
    result = []

    for line in source_code:
        if (len(line) == 0):
            continue
        if (line.split(' ')[0] == "def"):
            if (len(fragment) > 0):
                result.append("".join(fragment))
            fragment = []
        fragment.append(line)
    if (len(fragment) != 0):
        result.append("".join(fragment))

    return result


def split_by_brace(source_code):
    # 根据大括号分割java/cpp代码中的多个函数
    # 算法：
    # java/cpp代码的函数体一定被包裹在大括号中
    # 用一个栈找到与第一个左括号匹配的右括号，中间的部分就是一个完整的函数，后面的部分以此类推即可
    # 注意：这种方法不能处理一个class里面定义了多个函数的情况。

    source_code = "".join(source_code)
    result = []
    stack = []
    start_point = 0

    for i, char in enumerate(source_code):
        if char == "{":
            stack.append(char)
        elif char == "}":
            assert len(stack) > 0, "Unmatched right brace"
            stack.pop()
            if (len(stack) == 0):
                result.append(source_code[start_point:i + 1])
                start_point = i + 1

    assert len(stack) == 0, "Unmatched left brace"
    return result


def split_code(source_code, source_language):
    if (source_language == "python"):
        return split_by_indent(source_code)
    else:
        return split_by_brace(source_code)


@app.route('/transform/', methods=('POST', 'GET'))
def transform():
    if request.method == 'POST':
        global source, source2
        # print(request.form['code'])
        # axios请求
        data = request.get_json(silent=True)

        source = data['code']
        source_language = data['source_language']
        target_language = data['target_language']

        split_source_code = split_code(source, source_language)
        split_target_code = []
        for fragment in split_source_code:
            source2 = run_transform(fragment, source_language, target_language)
            print(fragment, source2)
            split_target_code.append(source2)
        source2 = "".join(split_target_code)

        return {'source': source, 'result': source2}
    return redirect(url_for('index'))


@app.route('/diff/', methods=('POST', 'GET'))
def get_diff():
    if request.method == 'POST':
        # axios请求
        data = request.get_json(silent=True)
        source = data['text1']
        translated = data['text2']
        d = difflib.HtmlDiff()
        html = d.make_file(source.split('\n'), translated.split('\n'))
        print(source)
        print(translated)
        # print(html)
        # print(type(html))
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        t0 = tables[0]
        t0['style'] = "margin:auto; width: 100%; text-align:left;" + t0.get('style', '')
        t1 = tables[1]
        t1['style'] = "margin:auto; text-align:left;" + t1.get('style', '')
        result = str(t0) + '\n' + str(t1)
        # print(result)
        return {'result': result}
    return redirect(url_for('index'))


def run_transform(source, source_language, target_language):
    return 'def abc(): \tpass\n'
