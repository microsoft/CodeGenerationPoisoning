# Copyright 2015 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from bookshelf import get_model
from flask import Blueprint, redirect, render_template, request, url_for


crud = Blueprint('crud', __name__)


# [START list]
@crud.route("/")
def list():

    token = request.args.get('page_token', None)
    if token:
        token = token.encode('utf-8')

    books, next_page_token = get_model().list(cursor=token)

    return render_template(
        "list.html",
        books=books,
        next_page_token=next_page_token,
        enable_add=True)
# [END list]

@crud.route("/search")
def search():
    print(request.method)
    print(request.args)
    print(bool(request.args))
    if bool(request.args) == False:
        return render_template("search.html", action="Search")

    token = request.args.get('page_token', None)
    if token:
        token = token.encode('utf-8')

    books, next_page_token = get_model().list(
        cursor=token,
        title = request.args.get('title', None),
        author = request.args.get('author', None),
        year = request.args.get('year', None))

    return render_template(
        "list.html",
        books=books,
        next_page_token=next_page_token,
        enable_add=False)

@crud.route('/<id>')
def view(id):
    book = get_model().read(id)
    avg_rate = get_model().avg_rate(id)

    return render_template("view.html", book=book, avgrate=avg_rate)


# [START add]
@crud.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)

        book = get_model().create(data)

        return redirect(url_for('.view', id=book['id']))

    return render_template("form.html", action="Add", book={})
# [END add]


@crud.route('/<id>/edit', methods=['GET', 'POST'])
def edit(id):
    book = get_model().read(id)
    print("edit in crud.py, request method: ", request.method)
    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        print(data)

        book = get_model().update(data, id)

        return redirect(url_for('.view', id=book['id']))

    return render_template("form.html", action="Edit", book=book)


@crud.route('/<id>/delete')
def delete(id):
    get_model().delete(id)
    return redirect(url_for('.list'))

@crud.route('/<id>/rate', methods=['GET', 'POST'])
def rate(id):
    book = get_model().read(id)

    if request.method == 'POST':
        data = request.form.to_dict(flat=True)
        print(data)

        book = get_model().rate(data, id)

        return redirect(url_for('.view', id=book['bookid']))

    return render_template("rate.html", action="Review", book=book)
