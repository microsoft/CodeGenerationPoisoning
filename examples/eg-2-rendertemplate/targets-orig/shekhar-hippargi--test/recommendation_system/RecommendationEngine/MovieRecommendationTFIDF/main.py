# Import TfIdfVectorizer from scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd
import numpy as np
from flask import Flask, render_template, request
# libraries for making count matrix and similarity matrix
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics.pairwise import linear_kernel

class Recommendation:
    def __init__(self):
        self.df1 = pd.read_csv('data/tmdb_5000_movies.csv')

        self.C = self.df1['vote_average'].mean()
        self.m = self.df1['vote_count'].quantile(0.9)

        self.q_movies = self.df1.copy().loc[self.df1['vote_count'] >= self.m]

        #Define a TF-IDF Vectorizer Object. Remove all english stop words such as 'the', 'a'
        self.tfidf = TfidfVectorizer(stop_words='english')

        #Replace NaN with an empty string
        self.df1['overview'] = self.df1['overview'].fillna('')

        #Construct the required TF-IDF matrix by fitting and transforming the data
        self.tfidf_matrix = self.tfidf.fit_transform(self.df1['overview'])

        # Compute the cosine similarity matrix
        self.cosine_sim = cosine_similarity(self.tfidf_matrix, self.tfidf_matrix)
        self.indices = pd.Series(self.df1.index, index=self.df1['title']).drop_duplicates()

    # Function that takes in movie title as input and outputs most similar movies
    @staticmethod
    def get_recommendations(title):
        r = Recommendation()
        if title not in r.df1['title'].values:
            return ('This movie is not in our database.\nPlease check if you spelled it correct using camel casing')
        else:
            # Get the index of the movie that matches the title
            # if title not in df1
            idx = r.indices[title]

            # Get the pairwsie similarity scores of all movies with that movie
            sim_scores = list(enumerate(r.cosine_sim[idx]))

            # Sort the movies based on the similarity scores
            sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)

            # Get the scores of the 10 most similar movies
            sim_scores = sim_scores[1:11]

            # Get the movie indices
            movie_indices = [i[0] for i in sim_scores]

            # Return the top 10 most similar movies
            return r.df1['title'].iloc[movie_indices]

app = Flask(__name__)

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/recommend")
def recommend():
    movie = request.args.get('movie')
    r = Recommendation.get_recommendations(movie)
    if type(r) == type('string'):
        return render_template('recommend.html', movie=movie, r=r, t='s')
    else:
        return render_template('recommend.html', movie=movie, r=r, t='l')


if __name__ == '__main__':
    app.run()