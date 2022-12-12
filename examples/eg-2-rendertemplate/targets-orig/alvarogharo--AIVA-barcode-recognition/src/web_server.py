from flask import Flask, render_template, jsonify, request
from barcode_recognizer import BarcodeRecognizer
from utils import base64_to_image
import os

DEFAULT_HOST = "0.0.0.0"

INDEX_HTML_PATH = "index.html"

IMAGE_JSON_KEY = "img"
RESULT_JSON_KEY = "result"

METHOD_POST = "POST"

QUERY_RECOGNIZE = "/recognize"


bar_recognizer = BarcodeRecognizer()
app = Flask(__name__)


@app.route("/")
def main():
    return render_template(INDEX_HTML_PATH)


@app.route(QUERY_RECOGNIZE, methods=[METHOD_POST])
def run():
    img = base64_to_image(request.json[IMAGE_JSON_KEY])
    decoded_value = bar_recognizer.recognize(img)
    print("Decoded value: " + str(decoded_value))
    response = {}
    response[RESULT_JSON_KEY] = decoded_value
    return jsonify(response)


if __name__ == "__main__":
    app.run(debug=False, host=DEFAULT_HOST)
