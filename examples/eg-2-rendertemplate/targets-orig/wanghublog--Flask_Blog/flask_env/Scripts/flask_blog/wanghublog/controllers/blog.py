from flask import render_template,Blueprint,redirect,url_for,session,abort,flash,request
from sqlalchemy import func, text
from uuid import uuid4
from os import path
from datetime import datetime
from wanghublog.models import db, User, Post, Tag, Comment, posts_tags
from wanghublog.forms import CommentForm,PostForm
from flask_login import login_required,current_user
from flask_principal import Permission,UserNeed,IdentityContext,RoleNeed
from wanghublog.extensions import poster_permission,admin_permission,default_permission,cache
import pdb

blog_blueprint = Blueprint(
    'blog',
    __name__,
    # path.pardir ==> ..
    template_folder=path.join(path.pardir, 'templates', 'blog'),
    # Prefix of Route URL 
    url_prefix='/blog')


#右侧边栏的视图
@cache.cached(timeout=7200,key_prefix='sidebar_data')
def sidebar_data():
    """Set the sidebar function."""

    # Get post of recent
    recent = db.session.query(Post).order_by(
            Post.publish_date.desc()
        ).limit(5).all()

    # Get the tags and sort by count of posts.
    top_tags = db.session.query(
            Tag, func.count(posts_tags.c.post_id).label('total')
        ).join(
            posts_tags
        ).group_by(Tag).order_by(text('total DESC')).limit(5).all()
    return recent, top_tags

@blog_blueprint.route('/')
@blog_blueprint.route('/<int:page>')
@cache.cached(timeout=60)#timeout 表示该视图函数返回的结果将会被缓存的时长.
def home(page=1):
    """View function for home page"""

    posts = Post.query.order_by(
        Post.publish_date.desc()
    ).paginate(page, 10)

    recent, top_tags = sidebar_data()
    print('是否调用缓存，未调用')
    return render_template('home.html',
                           posts=posts,
                           recent=recent,
                           top_tags=top_tags)

def make_cache_key(*args, **kwargs):
    """Dynamic creation the request url."""
    '''会动态的生成一个唯一的缓存键, 用于确定这一次请求的 URL 是否存在缓存, 如果存在则返回, 如果不存在则新建. 
        所以在该函数中我们使用了请求 path + hash 字符串结合而成的唯一字符串作为缓存键.'''
    path = request.path
    args = str(hash(frozenset(request.args.items())))
    return (path + args).encode('utf-8')

@blog_blueprint.route('/post/<string:post_id>',methods=('GET','POST'))
@cache.cached(timeout=60,key_prefix=make_cache_key)
def post(post_id):
    """View function for post page"""

    # Form object: `Comment`
    form = CommentForm()
    # form.validate_on_submit() will be true and return the
    # data object to form instance from user enter,
    # when the HTTP request is POST
    if form.validate_on_submit():
        new_comment = Comment(id=str(uuid4()),
                              name=form.name.data)
        new_comment.text = form.text.data
        new_comment.date = datetime.now()
        new_comment.post_id = post_id

        db.session.add(new_comment)
        db.session.commit()

    post = Post.query.get_or_404(post_id)
    tags = post.tags
    comments = post.comments.order_by(Comment.date.desc()).all()
    recent, top_tags = sidebar_data()

    return render_template('post.html',
                           post=post,
                           tags=tags,
                           comments=comments,
                           form=form,
                           recent=recent,
                           top_tags=top_tags)


@blog_blueprint.route('/tag/<string:tag_name>')
def tag(tag_name):
    """View function for tag page"""

    #tag = db.session.query(Tag).filter_by(name=tag_name).first_or_404()
    # Tag.qurey() 对象才有 first_or_404()，而 db.session.query(Model) 是没有的
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    posts = tag.posts.order_by(Post.publish_date.desc()).all()
    recent, top_tags = sidebar_data()

    return render_template('tag.html',
                           tag=tag,
                           posts=posts,
                           recent=recent,
                           top_tags=top_tags)


@blog_blueprint.route('/user/<string:username>')
def user(username):
    """View function for user page"""
    user = db.session.query(User).filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.publish_date.desc()).all()
    recent, top_tags = sidebar_data()

    return render_template('user.html',
                           user=user,
                           posts=posts,
                           recent=recent,
                           top_tags=top_tags)

@blog_blueprint.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    """View function for new_port."""
    form = PostForm()

    # Ensure the user logged in.
    # Flask-Login.current_user can be access current user.
    if not current_user:
        return redirect(url_for('main.login'))

    # Will be execute when click the submit in the create a new post page.
    if form.validate_on_submit():
        new_post = Post()
        new_post.title = form.title.data
        new_post.text = form.text.data
        new_post.publish_date = datetime.now()
        new_post.user_id = session.get('user_id')
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('blog.home'))

    return render_template('new_post.html',
                           form=form)


@blog_blueprint.route('/edit/<string:id>', methods=['GET', 'POST'])
@login_required
@default_permission.require(http_exception=403)
def edit_post(id):
    """View function for edit_post."""
    

    post = Post.query.get_or_404(id)
    # Ensure the user logged in.
    if not current_user:
        return redirect(url_for('main.login'))

    # Only the post onwer can be edit this post.

    if current_user != post.users:
      flash('这篇文章的作者不是你哦')
      return redirect(url_for('blog.post', post_id=id))

    # 当 user 是 poster 或者 admin 时, 才能够编辑文章
    
    # Admin can be edit the post.
    permission = Permission(UserNeed(post.users.id))
    if permission.can() or admin_permission.can():
      form = PostForm()
      
      if form.validate_on_submit():
        post.title = form.title.data
        post.text = form.text.data
        post.publish_date = datetime.now()

        # Update the post
        db.session.add(post)
        db.session.commit()
        return redirect(url_for('blog.post', post_id=post.id))
    # else:
    #   abort(403)

    # Still retain the original content, if validate is false.
    form.title.data = post.title
    # user=User.query.filter_by(username='wangmilk').one()
    # rol=[]
    # for role in current_user.roles:
    #             rol.append(RoleNeed(role.name))
    form.text.data = post.text
    return render_template('edit_post.html', form=form, post=post)