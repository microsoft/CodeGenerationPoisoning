from flask import Flask, render_template, request

from ContentBased.MovieRecommendationTFIDF.RecommendMovies import RecommendMovies
from ContentBased.ProductsRecommendation.RecommendProducts import RecommendProducts
from CollaborativeFiltering.scripts.SimpleItemCF import SimpleItemCF
from CollaborativeFiltering.scripts.SimpleUserCF import SimpleUserCF

ALLOWED_EXTENSIONS = {'txt', 'csv'}

app = Flask(__name__)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html')
    elif request.method == 'POST':
        if request.form["algoname"] == 'ContentBasedMovieRecommendation':
            return render_template('ContentBasedMovieRecommendation.html')
        if request.form["algoname"] == 'ContentBasedProductRecommendation':
            return render_template('ContentBasedProductRecommendation.html')
        if request.form["algoname"] == 'CollaborativeItemBased':
            return render_template('CFMoviesRecommendationItemBased.html')
        if request.form["algoname"] == 'CollaborativeUserBased':
            return render_template('CFMoviesRecommendationUserBased.html')


@app.route("/recommend", methods=['POST'])
def recommend():
    if request.method == 'POST':
        if (request.files['file'].filename != "") and (request.form["movieName"]) and allowed_file(
                request.files['file'].filename):
            movie = request.form['movieName']
            file = request.files['file']
            recommendMovies = RecommendMovies(file)
            result = recommendMovies.get_recommendations(movie)
            if type(result) == type('string'):
                return render_template('recommendMovies.html', movie=movie, r=result, t='s')
            else:
                return render_template('recommendMovies.html', movie=movie, r=result, t='l')


@app.route("/recommendProducts", methods=['POST'])
def recommendProducts():
    if request.method == 'POST':
        if (request.files['file'].filename != "") and (request.form["productId"]) and allowed_file(
                request.files['file'].filename):
            productId = request.form['productId']
            file = request.files['file']
            recommendProductsObj = RecommendProducts(file)
            productName, result = recommendProductsObj.recommend_products(productId)

            if type(result) == type('string'):
                return render_template('recommendProducts.html', item=productId, productName=productName, r=result,
                                       t='s')
            else:
                return render_template('recommendProducts.html', item=productId, productName=productName, r=result,
                                       t='l')


@app.route("/CFItemBased", methods=['POST'])
def recommendCFItemBasedMovies():
    if request.method == 'POST':
        if (request.files['movies'].filename != "") and (request.files['ratings'].filename != "") and (
                request.form["userId"]) \
                and allowed_file(request.files['movies'].filename) and allowed_file(request.files['ratings'].filename):
            userId = request.form['userId']
            moviesFile = request.files['movies']
            ratingsFile = request.files['ratings']

            recommendCFMoviesobj = SimpleItemCF(moviesFile, ratingsFile, userId)
            result = recommendCFMoviesobj.recommendMovies()
            if type(result) == type('string'):
                return render_template('recommendMoviesCFItemBased.html', item=userId, r=result,
                                       t='s')
            else:
                return render_template('recommendMoviesCFItemBased.html', item=userId, r=result,
                                       t='l')


@app.route("/CFUserBased", methods=['POST'])
def recommendCFUserBasedMovies():
    if request.method == 'POST':
        if (request.files['movies'].filename != "") and (request.files['ratings'].filename != "") and (
                request.form["userId"]) \
                and allowed_file(request.files['movies'].filename) and allowed_file(request.files['ratings'].filename):
            userId = request.form['userId']
            moviesFile = request.files['movies']
            ratingsFile = request.files['ratings']

            recommendCFMoviesobj = SimpleUserCF(moviesFile, ratingsFile, userId)
            result = recommendCFMoviesobj.recommendMoviesUserCF()
            if type(result) == type('string'):
                return render_template('recommendMoviesCFUserBased.html', user=userId, r=result,
                                       t='s')
            else:
                return render_template('recommendMoviesCFUserBased.html', user=userId, r=result,
                                       t='l')


if __name__ == '__main__':
    app.run(debug=True)
