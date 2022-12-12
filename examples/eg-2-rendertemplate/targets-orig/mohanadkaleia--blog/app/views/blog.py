import flask
import models.post
import models.book
import config as cfg
import app.logger as logger

from flask import Blueprint, render_template, Markup
from micawber import bootstrap_basic, parse_html
from micawber.cache import Cache as OEmbedCache

app = Blueprint("blog", __name__, url_prefix="/")
log = logger.get_logger(__name__)
config = cfg.get_config()

# Configure micawber with the default OEmbed providers (YouTube, Flickr, etc).
# We'll use a simple in-memory cache so that multiple requests for the same
# video don't require multiple network requests.
oembed_providers = bootstrap_basic(OEmbedCache())


@app.route("/")
def index():
    log.info("Request the main page")
    posts = models.post.all()
    return render_template("index.html", posts=posts, config=config)


@app.route("/blog")
def blog():
    log.info("Request /blog")
    posts = models.post.all()
    return render_template("blog.html", posts=posts, config=config)


@app.route("/books")
def books():
    log.info("Request /books")
    books = models.book.all()
    for book in books:
        content = parse_html(
            book["content"],
            oembed_providers,
            urlize_all=True,
        )

        book["content"] = Markup(content)

    return render_template("books.html", books=books, config=config)


@app.route("/<slug>")
def post(slug):
    log.info(f"Request /{slug}")

    try:
        entry = models.post.get(slug)
    except Exception:
        return "oops.. I could not find this page!!"

    content = parse_html(
        entry["content"],
        oembed_providers,
        urlize_all=True,
    )
    entry["content"] = Markup(content)
    return render_template("article.html", post=entry, config=config)


@app.route("/contact")
def contact():
    log.info("Request /contact")
    return "mohanad@kaleia.io"


@app.route("/mentorship")
def mentorship():
    return "If you are undergrad or junior software engineer and need a mentor, feel free to shoot me an email mohanad.kaleia[at]gmail[dot]com ✌️"
