from indentml.parser import QqParser, QqTag
from flask import Flask, render_template
import os
import sys
from io import StringIO
import contextlib
from subprocess import Popen, PIPE, STDOUT
import itertools
import mistune

app = Flask(__name__, static_url_path='')
app.debug = True
DEFAULT_LANG = "en"
allowed_tags = {'about', 'compare', 'what', 'lang',
                'python', 'js', 'option',
                'ref', 'seealso', 'out', 'require',
                'topic', 'heading', 'description', 'id',
                'comment'}

translations = {
    'Language': 'Язык',
    'Topics': 'Темы',
    'Russian': 'Русский (Russian)',
    'English': 'Английский (English)',
    'require': 'требует',
    'reference': 'ссылка',
    'Links': 'Ссылки',
    'blog': 'блог',
}
@app.route("/")
def show_default():
    return show(DEFAULT_LANG, None)

@app.route("/pythonvjs/show/<filename>/<lang>/")
def show(lang, filename):
    parser = QqParser()
    parser.allowed_tags.update(allowed_tags)

    source_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "source")

    path = os.path.join(source_dir, "contents.qq")

    tree = parser.parse_file(path).process_include_tags(parser, source_dir)

    if filename:
        topic = [t for t in tree.find_all("topic") if t._id.value == filename][0]
    else:
        topic = tree._topic

    for compare in topic.find_all("compare"):
        for prlang in ['python', 'js']:
            for prlangtag in compare.find_all(prlang):
                pr = process_prlang(prlangtag, prlang)
                prlangtag.clear()
                prlangtag.extend_children(pr)

    def get_tag_lang(tree, tagname):
        first = None
        default_lang = None
        for tag in tree.find_all(tagname):
            if tag._lang and tag._lang.value == lang:
                return tag
            if first is None:
                first = tag
            if tag._lang == DEFAULT_LANG and default_lang is None:
                default_lang = tag
        if default_lang:
            return default_lang
        return first

    if lang == 'en':
        def translate(s):
            return s
    elif lang == 'ru':
        def translate(s):
            return translations.get(s, s)

    return render_template("py_js_compare.html", lang=lang,
                           tree=tree, topic=topic, translate=translate,
                           mistune=mistune, get_tag_lang=get_tag_lang)

@app.route("/pythonvjs/show/<filename>/")
def show_filename(filename):
    return show(DEFAULT_LANG, filename)

# FROM: http://stackoverflow.com/a/3906390/3025981
@contextlib.contextmanager
def stdout_io(stdout=None):
    old = sys.stdout
    if stdout is None:
        stdout = StringIO()
    sys.stdout = stdout
    yield stdout
    sys.stdout = old
# END FROM


def strip_blank_lines(code):
    lines = code.splitlines(keepends=False)
    if not lines:
        return ""
    out = []
    it = iter(lines)

    line = None

    for line in it:
        if line.strip():
            break
    out.append(line)
    for line in it:
        out.append(line)
    for line in reversed(out):
        if not line.strip():
            out.pop()
    return "\n".join(out)


def process_python(tag: QqTag):
    """
    Output:
    \_codeblock
            \_code ...(str)...
            \_output ...(str)...
            \_code ...(str)...
            \_output ...(str)...
            \_code ...(str)...
            ....
        \ref ...
        \seealso ...
        \require ...
    :param tag:
    :return:
    """
    loc = {}
    glob = {}
    codeblock = QqTag("_codeblock")
    chunk = []
    for child in tag:

        if isinstance(child, str):
            with stdout_io() as s:
                try:
                    exec(child, loc, glob)
                except Exception as e:
                    print("Exception: {}\n{}".
                          format(e.__class__.__name__, e))

            chunk.append(strip_blank_lines(child)+"\n"),
            if s.getvalue():
                codeblock.append(QqTag("_code", ["".join(chunk)]))
                codeblock.append(QqTag("_output", [s.getvalue()]))
                chunk.clear()

        elif child.name == 'out':
            chunk.append(strip_blank_lines(child.text_content))
            codeblock.append(QqTag("_code", ["".join(chunk)]))
            chunk.clear()

            res = eval(child.text_content, loc, glob)
            codeblock.append(QqTag("_output", [repr(res)]))

        elif child.name != 'flush':
            codeblock.append(child)
    if chunk:
        codeblock.append(QqTag("_code", ["".join(chunk)]))

    return codeblock


def node_exec(code):
    p = Popen(['node'], stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    stdout = p.communicate(input=code.encode('utf-8'))[0]
    return stdout.decode('utf-8')


def process_js(tag: QqTag):
    """
    Output:
    \_codeblock
        \_item
            \_code ...(str)...
            \_output ...(str)...
        \_item
            \_code ...(str)...
            \_output ...(str)...
        \ref ...
        \seealso ...
        \require ...
    :param tag:
    :return:
    """
    codeblock = QqTag("_codeblock")
    cumulative_code = []
    current_chunk = []

    for child in itertools.chain(tag, [None]):
        if isinstance(child, str) and child.strip():
            cumulative_code.append(child)
            current_chunk.append(child)
        elif child is None or child.name == 'out':
            code = "".join(cumulative_code)
            if current_chunk:
                res = node_exec(code)

                if res or child is None:
                    code_tag = QqTag("_code",
                                     [strip_blank_lines("".join(
                                         current_chunk))])
                    codeblock.append_child(code_tag)
                    if res:
                        codeblock.append_child(QqTag("_output", [res]))
                    current_chunk.clear()
            if child is not None:
                logger = "console.log({})".format(child.text_content)
                res = node_exec(code + ";\n" + logger)
                code_tag = QqTag("_code", [strip_blank_lines(
                    "".join(current_chunk) +
                    child.text_content.rstrip() + ";")])
                current_chunk.clear()
                codeblock.append_child(code_tag)
                codeblock.append_child(QqTag("_output", [res]))
        else:
            codeblock.append_child(child)
    return codeblock

def process_prlang(tag, prlang):
    assert prlang in ['python', 'js']
    if prlang == 'python':
        return process_python(tag)
    else:
        return process_js(tag)
if __name__ == '__main__':
    app.run()
