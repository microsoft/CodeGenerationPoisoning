from flask import render_template, flash
from sqlalchemy import exc
from . import reader_bp
from app import models


@reader_bp.route("/")
def reader_home():
    try:
        posts_from_db = models.Article.get_all_articles()
        other_posts_from_db = models.Article.get_random_articles(5)
        posts = []
        other_posts = []
        for p in posts_from_db:
            post = {"post_id": p.id, "post_title": p.title, "post_subtitle": p.subtitle, "post_date": p.posted_date,
                    "post_content": p.content_html}
            posts.append(post)
        for op in other_posts_from_db:
            p = {"post_id": op.id, "post_title": op.title}
            other_posts.append(p)
        return render_template("reader/home.html", posts=posts, other_posts=other_posts)
    except exc.SQLAlchemyError:
        flash('Could not retrieve posts.', 'error')
        return render_template("reader/home.html", posts=[])


@reader_bp.route("/post/<int:post_id>")
def read_post(post_id):
    try:
        post_from_db = models.Article.get_article(post_id)
        other_posts_from_db = models.Article.get_random_articles(5)
        post = {"post_id": post_from_db.id, "post_title": post_from_db.title, "post_subtitle": post_from_db.subtitle,
                "post_date": post_from_db.posted_date, "post_content": post_from_db.content_html}
        other_posts = []
        for op in other_posts_from_db:
            p = {"post_id": op.id, "post_title": op.title}
            other_posts.append(p)
        return render_template("reader/reader_view_post.html", post=post, other_posts=other_posts)
    except exc.SQLAlchemyError:
        flash('Could not retrieve post.', 'error')
        return render_template("reader/home.html", post=None, other_posts=[])
