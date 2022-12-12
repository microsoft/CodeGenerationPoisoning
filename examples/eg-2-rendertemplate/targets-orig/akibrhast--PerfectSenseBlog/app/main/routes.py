from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, \
    jsonify, current_app
from flask_login import current_user, login_required
from flask_babel import _, get_locale
from app import db
from app.main.forms import EditProfileForm, PostForm,AddTag,TagList,CommentForm
from app.models import User, Post,Tag,postTag,Comment
from app.main import bp


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    g.locale = str(get_locale())


@bp.route('/', methods=['GET', 'POST'])
@bp.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), posts=posts.items, next_url=next_url,prev_url=prev_url)






@bp.route('/writenewarticle', methods=['GET', 'POST'])
@login_required
def writenewarticle():
    categories = [(c.id, c.name) for c in Tag.query.all()]

    postform = PostForm()
    postform.tags.choices   = categories
    AddTagForm = AddTag()
    TagForm = TagList(request.form)  
    TagForm.tags.choices = categories
    if postform.validate_on_submit():
        post = Post(body=postform.hiddenField.data, author=current_user,
                    language='en',title=postform.title.data)
        tags = Tag.query.filter(Tag.id.in_(postform.tags.data))
        post.tags.extend(tags)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    if AddTagForm.validate_on_submit():
        add_tag(AddTagForm.name.data)
        return redirect(url_for('main.writenewarticle'))
    else:
        print("Nothing")

    return render_template('newarticle.html', title=_('New Article'), postform=postform,addTagForm=AddTagForm)
    

@bp.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/readarticle/<postid>', methods=['GET', 'POST'])
@login_required
def readarticle(postid):
    commentform = CommentForm()

    
    post = Post.query.filter_by(id=postid).first_or_404()
    comments = Comment.query.filter_by(post_id=postid).all()

    if commentform.validate_on_submit():
        comment = Comment(comment=commentform.comment.data,post_id=postid,post=post)
        db.session.add(comment)
        db.session.commit()
        flash(_('Your comment has been posted'))
        return redirect(url_for('main.readarticle',postid=postid))
    return render_template('readarticle.html',post=post,commentform=commentform,comments=comments)

@bp.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot follow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash(_('You are following %(username)s!', username=username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(_('User %(username)s not found.', username=username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash(_('You cannot unfollow yourself!'))
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(_('You are not following %(username)s.', username=username))
    return redirect(url_for('main.user', username=username))



def add_tag(tag_name):
    tag_name = tag_name.lower();
    if Tag.query.filter_by(name=tag_name).first():
        flash('Tag "{}" already exists'.format(
            tag_name))
    else:
        tag = Tag(
            name=tag_name,
        )
        db.session.add(tag)
        db.session.commit()
        flash('Successfully added tag: {}'.format(
            tag_name))