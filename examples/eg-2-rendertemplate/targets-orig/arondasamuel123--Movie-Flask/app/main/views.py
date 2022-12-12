from flask import render_template,request,redirect,url_for,abort
from ..request import get_movies, get_movie, search_movie
from ..models import Review,User
from .forms import ReviewForm,UpdateProfile
from . import main
from flask_login import login_required,current_user
from .. import db,photos
from ..email import mail_message
import markdown2


# Review = reviews.Review



#Views
@main.route('/')
def index():
    '''
    View root page function that returns the index page and its data

    '''
    popular_movies = get_movies('popular')
    upcoming_movies = get_movies('upcoming')
    now_showing_movie = get_movies('now_playing')
    print(popular_movies)
    title = 'Home - Welcome to The best Movie Review Website Online'

    search_movie = request.args.get('movie_query')
    if search_movie:
        return redirect(url_for('main.search', movie_name=search_movie))
    else:
    
        return render_template('index.html', title = title, popular = popular_movies, upcoming_movies = upcoming_movies, now_showing = now_showing_movie)

@main.route('/movies/<int:movie_id>')
def movie(movie_id):
    '''
    View movie page function that returns the movie details page and its data
    '''
    movie = get_movie(movie_id)
    title = f'{movie.title}'
    reviews = Review.get_reviews(movie.movie_id)
    return render_template('movies.html',movie = movie, reviews = reviews)

@main.route('/search/<movie_name>')
def search(movie_name):
    '''
     View function to display the search results 
    '''
    movie_name_list = movie_name.split(" ")
    movie_name_format = "+".join(movie_name_list)
    print(movie_name_format)
    searched_movies = search_movie(movie_name_format)
    title = f'search results for (movie_name)'
    return render_template('search.html', movies = searched_movies)

@main.route('/movie/reviews/new/<int:movie_id>',methods = ['GET', 'POST'])
@login_required
def new_review(movie_id):
    form = ReviewForm()
    movie = get_movie(movie_id)
    
    if form.validate_on_submit():
        title = form.title.data
        review = form.review.data

        # Updated review instance
        new_review = Review(movie_id=movie.movie_id,movie_title=title,image_path=movie.poster,movie_review=review,user=current_user)

        # save review method
        new_review.save_review()
        return redirect(url_for('.movie',movie_id = movie.movie_id ))

    title = f'{movie.title} review'
    return render_template('new_review.html',title = title, review_form=form, movie=movie)



    
    title = f'{movie.title} review'
    return render_template('new_review.html', title = title, review_form = form, movie = movie)


@main.route('/user/<uname>')
def profile(uname):
    user = User.query.filter_by(username = uname).first()

    if user is None:
        abort(404)

    return render_template("profile/profile.html", user = user)

@main.route('/user/<uname>/update', methods=['GET','POST'])
@login_required
def update_profile(uname):
    user = User.query.filter_by(username = uname).first()
    
    if user is None:
        abort(404)
    profile_form = UpdateProfile()
    if profile_form.validate_on_submit():
        user.bio = profile_form.bio.data
        db.session.add(user)
        db.session.commit()
        
        return redirect(url_for('.profile',uname=user.username))
    return render_template('profile/update.html', profile_form = profile_form)

@main.route('/user/<uname>/update/pic', methods=['POST'])
@login_required
def update_pic(uname):
    user = User.query.filter_by(username = uname).first()
    if 'photo' in request.files:
        filename = photos.save(request.files['photo'])
        path = f'photos/{filename}'
        user.profile_pic_path = path
        db.session.commit()
    return redirect(url_for('main.profile', uname=uname))

@main.route('/review/<int:review_id>')
def single_review(review_id):
    review=Review.query.get(review_id)
    if review is None:
        abort(404)
    format_review = markdown2.markdown(review.movie_review,extras=["code-friendly", "fenced-code-blocks"])
    return render_template('review.html',review = review,format_review=format_review)


