from GettingStart.MovieLens import MovieLens
from surprise import SVD
from flask import Flask, render_template, request


class GettingStarted:
    def __init__(self):
        pass

    @staticmethod
    def BuildAntiTestSetForUser(testSubject, trainset):
        fill = trainset.global_mean

        anti_testset = []

        u = trainset.to_inner_uid(str(testSubject))

        user_items = set([j for (j, _) in trainset.ur[u]])
        anti_testset += [(trainset.to_raw_uid(u), trainset.to_raw_iid(i), fill) for
                         i in trainset.all_items() if
                         i not in user_items]
        return anti_testset

    def recommend(self, testSubject):
        # Pick an arbitrary test subject

        ml = MovieLens()

        # print("Loading movie ratings...")
        data = ml.loadMovieLensLatestSmall()
        recommended_movies = ''
        userRatings = ml.getUserRatings(testSubject)
        loved = []
        hated = []
        for ratings in userRatings:
            if (float(ratings[1]) >= 4.0):
                loved.append(ratings)
            if (float(ratings[1]) < 4.0):
                hated.append(ratings)

        print("\nUser ", testSubject, " loved these movies:")
        recommended_movies = recommended_movies + "\nUser " + str(testSubject) + " loved these movies:"
        for ratings in loved:
            print(ml.getMovieName(ratings[0]))
            recommended_movies = recommended_movies + '\n' + ml.getMovieName(ratings[0])
        print("\n...and didn't like these movies:")
        recommended_movies = recommended_movies + "\n... and didn't like these movies:"
        for ratings in hated:
            print(ml.getMovieName(ratings[0]))
            recommended_movies = recommended_movies + '\n' + ml.getMovieName(ratings[0])
        # print(loved_movies)
        # print(hated_movies)
        # print("\nBuilding recommendation model...")
        trainSet = data.build_full_trainset()

        algo = SVD()
        algo.fit(trainSet)

        # print("Computing recommendations...")
        testSet = GettingStarted.BuildAntiTestSetForUser(testSubject, trainSet)
        predictions = algo.test(testSet)

        recommendations = []

        print("\nWe recommend:")
        recommended_movies = recommended_movies + '\nRecommended movies are:'
        for userID, movieID, actualRating, estimatedRating, _ in predictions:
            intMovieID = int(movieID)
            recommendations.append((intMovieID, estimatedRating))

        recommendations.sort(key=lambda x: x[1], reverse=True)

        for ratings in recommendations[:10]:
            print(ml.getMovieName(ratings[0]))
            recommended_movies = recommended_movies + '\n' + ml.getMovieName(ratings[0])


        # print(recommended_movies)
        return recommended_movies


# start = GettingStarted()
# print(start.recommend(100))
app = Flask(__name__)


@app.route("/")
def home():
    return render_template('home.html')

@app.route("/recommend")
def recommend():
    # movie = request.args.get('movie')
    userId = request.args.get('userId')
    start = GettingStarted()
    result = start.recommend(userId)
    # r = Recommendation.get_recommendations(movie)
    # if type(userId) == type(int):
    #     return render_template('recommend.html', user=userId, r=start, t='s')
    # else:
    #     return render_template('recommend.html', user=userId, r=start, t='l')
    return render_template('recommend.html', user=userId, r=result, t='l')
    # return result

if __name__ == '__main__':
    app.run()
