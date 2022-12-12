from datetime import datetime

from flask import render_template, flash, redirect, url_for, request, jsonify, current_app, g
from flask_login import current_user, login_required
from guess_language import guess_language

from webapp import db
from webapp.models import User, Post
from webapp.utils import store_image, tell_admin_with_error, get_last_seen
from webapp.translation import translate_with_microsoft, translate_with_google
from webapp.main import main_blueprint as main
from webapp.main.forms import UpdateProfileForm, PostForm, SearchForm


# This flag is used to prevent sending too many emails when there is a problem with the translation API
adminTold = False


@main.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
        g.search_form = SearchForm()


@main.route('/', methods=['GET', 'POST'])
@main.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.content.data)
        if language == 'UNKNOWN' or len(language) > 5:
            language = ''

        post = Post(title=form.title.data, content=form.content.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()

        flash('Your post is now live!')
        return redirect(url_for('main.home'))

    page = request.args.get('page', 1, type=int)
    followed_posts = current_user.followed_posts()
    posts = followed_posts.paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.home', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.home', page=posts.prev_num) if posts.has_prev else None

    num_of_posts = followed_posts.count()
    displayPagination = num_of_posts > current_app.config['POSTS_PER_PAGE']

    return render_template('home.html', title='Home', form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url, num_of_posts=num_of_posts, display=displayPagination)

@main.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    all_posts = Post.query.order_by(Post.date_posted.desc())
    posts = all_posts.paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None

    displayPagination = all_posts.count() > current_app.config['POSTS_PER_PAGE']

    return render_template("home.html", title='Explore', posts=posts.items,
                          next_url=next_url, prev_url=prev_url, display=displayPagination)


@main.route("/about")
def about():
    return render_template('about.html', title='About')


@main.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = UpdateProfileForm()
    if form.validate_on_submit():
        if form.picture.data:
            image_file = store_image(form.picture.data)
            current_user.image_file = image_file
             
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.about_me = form.about_me.data

        db.session.commit()
        flash('Your profile has been updated !', 'info')
        return redirect(url_for('main.account', username=current_user.username))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.about_me.data = current_user.about_me

    image_file = url_for('static', filename='pics/' + current_user.image_file)
    return render_template('edit_profile.html', title='Edit Profile', image_file=image_file, form=form)


@main.route("/account/<string:username>", methods=['GET', 'POST'])
@login_required
def account(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.date_posted.desc()).all()

    image_file = url_for('static', filename='pics/' + user.image_file)

    return render_template('account.html', user=user, image_file=image_file, posts=posts, articles=len(posts))

@main.route("/follow/<string:username>")
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user:
        if user == current_user:
            flash('You cannot follow yourself !!')
            return redirect(url_for('main.account', username=username))

        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(url_for('main.account', username=username))
    else:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.home'))

@main.route("/unfollow/<string:username>")
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user:
        if user == current_user:
            flash('You cannot unfollow yourself !!')
            return redirect(url_for('main.account', username=username))

        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {} anymore !'.format(username))
        return redirect(url_for('main.account', username=username))
    else:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.home'))

@main.route('/translate', methods=['POST'])
@login_required
def translate_text():
    text = request.form['text']
    source_language = request.form['source_language']
    dest_language = request.form['dest_language']
    
    translatedText = translate_with_microsoft(text, source_language, dest_language)
    if 'Error:' in translatedText or 'Exception' in translatedText:
        if not adminTold:
            tell_admin_with_error('Problem With Microsoft Translator API [Awesome Blog]', error=translatedText)
            adminTold = True
            # print("+++++ \n Problem With Microsoft API !! \n +++++")    # Used instead of sending email when debugging 

        # We could use translate_with_google if there is a problem with Microsoft API
        translatedText = translate_with_google(text, source_language, dest_language)
    else:
        adminTold = False   # Reset the status to Flase again when the API is working
    
    return jsonify({'text': translatedText})

@main.route('/search')
@login_required
def search():
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    
    page = request.args.get('gage', 1, type=int)
    search_results, total = Post.search(g.search_form.q.data, page, current_app.config['POSTS_PER_PAGE'])
    posts = search_results.paginate(page, current_app.config['POSTS_PER_PAGE'], False)

    next_url = url_for('main.search', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.search', page=posts.prev_num) if posts.has_prev else None

    displayPagination = search_results.count() > current_app.config['POSTS_PER_PAGE']
    print(displayPagination)

    return render_template('search.html', title='Search Results', posts=posts.items, 
            next_url=next_url, prev_url=prev_url, display=displayPagination)


@main.route('/account/<string:username>/popup')
@login_required
def account_popup(username):
   user = User.query.filter_by(username=username).first_or_404()
   last_seen = get_last_seen(user.last_seen)

   return render_template('account_popup.html', user=user, last_seen=last_seen)