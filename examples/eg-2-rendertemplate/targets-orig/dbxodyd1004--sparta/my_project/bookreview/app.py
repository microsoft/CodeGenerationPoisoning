from flask import Flask, render_template, jsonify, request
from pymongo import MongoClient  # pymongo를 임포트 하기(패키지 인스톨 먼저 해야겠죠?)

app = Flask(__name__)

client = MongoClient('mongodb://tae:1225db@localhost', 27017)  # mongoDB는 27017 포트로 돌아갑니다.
db = client.dbsparta  # 'dbsparta'라는 이름의 db를 만듭니다.


## HTML을 주는 부분
@app.route('/')
def home():
    return render_template('index.html')


## API 역할을 하는 부분
@app.route('/review', methods=['POST'])
def write_review():
    # 1. 클라이언트가 준 title, author, review 가져오기.
    title = request.form['title']
    author = request.form['author']
    book_review = request.form['bookReview']

    print('title', title)
    print('author', author)
    print('bookReview', book_review)

    # 2. DB에 정보 삽입하기

    doc = {
        'title': title,
        'author': author,
        'bookReview': book_review,

    }
    db.reviews.insert_one(doc)

    # 3. 성공 여부 & 성공 메시지 반환하기
    return jsonify({'result': 'success', 'msg': '이 요청은 POST!'})


@app.route('/review', methods=['GET'])
def read_reviews():
    reviews = list(db.reviews.find({}, {'_id': False}))
    print(reviews)
    return jsonify({'result': 'success', 'msg': reviews})


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
