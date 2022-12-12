import os
import pickle

from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename

from src.encoder import transform_line, break_caesar, transform_txt


UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt'}
AVAILABLE_CIPHERS = ['caesar', 'vigenere']
AVAILABLE_BREAK_CIPHERS = ['caesar']
INPUT_FILE = 'system_files/input.txt'
OUTPUT_FILE = 'system_files/output.txt'
with open('system_files/language_model.txt', "rb") as fin:
    LANGUAGE_MODEL = pickle.load(fin)


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def check_errors(cipher, key, file, mode):
    errors = []
    cipher = cipher.lower()
    available = AVAILABLE_BREAK_CIPHERS if mode == 'break' else AVAILABLE_CIPHERS
    if cipher not in available:
        errors.append('Cipher type is incorrect')
    if cipher == 'caesar' and not mode == 'break':
        try:
            key = int(key)
        except ValueError:
            errors.append('wrong key (please use integer to code/decode caesar)')
    if file and not allowed_file(file.filename):
        errors.append('wrong file extensions (only txt files allowed)')
    return ' '.join(errors), key, cipher


def handle_input(file, string_input, mode, cipher, key=0):
    result = ''
    errors, key, cipher = check_errors(cipher, key, file, mode)
    if not errors:
        if file.filename == '':
            if mode == 'break':
                with open(INPUT_FILE, 'w') as file:
                    file.write(request.form['input'])

                break_caesar(INPUT_FILE, OUTPUT_FILE, LANGUAGE_MODEL)
                with open(OUTPUT_FILE, 'r') as file:
                    result = ''.join(file.readlines())
            else:
                result = transform_line(string_input, cipher, mode, key)
        else:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            if mode == 'break':
                break_caesar(file_path, OUTPUT_FILE, LANGUAGE_MODEL)
            else:
                transform_txt(file_path, OUTPUT_FILE, cipher, key, mode)
    return errors, result


@app.route("/", methods=["GET"])
def main_page():
    return render_template('main_page.html')


@app.route("/<mode>", methods=["GET", "POST"])
def encoder_pages(mode):
    errors = ''
    result = ''
    if request.method == "POST":
        try:
            key = request.form['key']
        except KeyError:
            key = 0
        errors, result = handle_input(request.files['file'], request.form['input'], mode, request.form['cipher'], key)
        if request.files['file'] and not errors:
            return render_template('download.html')

    return render_template('encoder_pages.html', mode=mode, errors=errors, result=result)


@app.route("/download", methods=["GET", "POST"])
def download_page():
    try:
        return send_file(OUTPUT_FILE)
    except Exception as e:
        return str(e)


if __name__ == "__main__":
    app.run(debug=True)
