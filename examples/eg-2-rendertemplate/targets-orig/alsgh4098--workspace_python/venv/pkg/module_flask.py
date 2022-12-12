from flask import Flask
from flask import render_template


import pkg.YTN_Craw

import pprint as p

app = Flask(__name__)

@app.route("/")
def index():
    news_list = ['https://www.ytn.co.kr/photo/photo_list_011705.html',
                 'https://www.ytn.co.kr/photo/photo_list_011707.html',
                 'https://www.ytn.co.kr/photo/photo_list_011706.html']

    # p.pprint(news_list)
    for i in news_list:
        # pkg폴더에서 YTN_CRAW 파일에서 ytn_craw 함수기능사용.news_list에 있는 ytn뉴스 가져와서 i로 사용.
        n_list = pkg.YTN_Craw.ytn_craw(i)

    return render_template("index.html", NEW_LIST_KEY = n_list)

if __name__ == "__main__" :
    app.run(host="127.0.0.1",port = "8888")

    # body > div.wrapper > div.content - wrapper > section.content > div: nth - child(2) > section.col - lg - 7.
    # connectedSortable.ui - sortable > div.box.box - primary > div.box - body > ul > li: nth - child(1) > span.text