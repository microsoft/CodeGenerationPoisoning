# services/users/project/api/users.py


from flask import Blueprint, request, render_template
from flask_restful import Resource, Api
from sqlalchemy import exc


from project import db
from project.api.models import Book


books_blueprint = Blueprint('books', __name__, template_folder='./templates')
api = Api(books_blueprint)


class BooksPing(Resource):
    def get(self):
        return {
            'status': 'success books',
            'message': 'pong!'
        }


class BooksList(Resource):

    def get(self):
        """Get all books"""
        response_object = {
            'status': 'success',
            'data': {
                'books': [book.to_json() for book in Book.query.all()]
            }
        }
        return response_object, 200

    def post(self):
        post_data = request.get_json()
        response_object = {
            'status': 'fail',
            'message': 'Invalid payload.'
        }
        if not post_data:
            return response_object, 400
        title = post_data.get('title')
        author = post_data.get('author')
        isbn = post_data.get('isbn')
        try:
            book = Book.query.filter_by(isbn=isbn).first()
            if not book:
                db.session.add(Book(title=title, author=author, isbn=isbn))
                db.session.commit()
                response_object['status'] = 'success'
                response_object['message'] = f'{title} was added!'
                return response_object, 201
            else:
                response_object['message'] = 'Sorry. That book already exists.'
                return response_object, 400
        except exc.IntegrityError:
            db.session.rollback()
            return response_object, 400


class Books(Resource):
    def get(self, book_id):
        response_object = {
            'status': 'fail',
            'message': 'Book does not exist'
        }
        try:
            book = Book.query.filter_by(id=int(book_id)).first()
            if not book:
                return response_object, 404
            else:
                response_object = {
                    'status': 'success',
                    'data': {
                        'id': book.id,
                        'title': book.title,
                        'author': book.author,
                        'isbn': book.isbn
                    }
                }
                return response_object, 200
        except ValueError:
            return response_object, 404


@books_blueprint.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        isbn = request.form['isbn']
        db.session.add(Book(title=title, author=author, isbn=isbn))
        db.session.commit()
    books = Book.query.all()
    return render_template('index.html', books=books)


api.add_resource(BooksPing, '/books/ping')
api.add_resource(BooksList, '/books')
api.add_resource(Books, '/books/<book_id>')
