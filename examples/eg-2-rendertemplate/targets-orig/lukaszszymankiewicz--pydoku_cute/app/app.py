import os

from flask import Flask, jsonify, render_template, request

from .file_helpers import delete_unused_sudokus
from .file_paths import (APP_PREFIX, IMAGE_EXTENSION, SOLVED_SUDOKU_PREFIX,
                         SUDOKUS_FILE_PATH, UNSOLVED_SUDOKU_PREFIX)
from .form_helpers import get_difficult_from_request
from .src import Difficult, draw_sudoku, generate

delete_unused_sudokus()
app = Flask(__name__)
app.config.from_object(os.environ.get("APP_CONFIG"))


@app.route("/generate_new_puzzle")
def generate_new_puzzle():
    delete_unused_sudokus()

    difficult = get_difficult_from_request(request.args)
    solved_sudoku, unsolved_sudoku = generate(difficult)

    draw_sudoku(
        solved_sudoku,
        path=APP_PREFIX + SUDOKUS_FILE_PATH + SOLVED_SUDOKU_PREFIX + IMAGE_EXTENSION,
    )
    draw_sudoku(
        unsolved_sudoku,
        path=APP_PREFIX + SUDOKUS_FILE_PATH + UNSOLVED_SUDOKU_PREFIX + IMAGE_EXTENSION,
    )

    return jsonify(
        {
            "solved_sudoku_path": SUDOKUS_FILE_PATH + SOLVED_SUDOKU_PREFIX + IMAGE_EXTENSION,
            "unsolved_sudoku_path": SUDOKUS_FILE_PATH + UNSOLVED_SUDOKU_PREFIX + IMAGE_EXTENSION,
        }
    )


@app.route("/")
def main():
    return render_template(
        template_name_or_list="index.html",
        title="Pydoku - Sudoku generator",
        difficult=Difficult.default,
    )


if __name__ == "__main__":
    app.run()
