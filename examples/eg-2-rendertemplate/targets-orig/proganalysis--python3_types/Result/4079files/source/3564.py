from datetime import date, datetime

from flask import Blueprint, render_template, abort
from flask_babel import _
from flask_login import current_user
from sqlalchemy import desc

from app import db, cache
from app.models.activity import Activity
from app.models.news import News
from app.models.page import Page, PageRevision
from app.service import page_service

blueprint = Blueprint('home', __name__)


@cache.memoize(timeout=60)
def get_revisions(data):
    pages = []
    revisions = []

    for path in data:
        if path == 'activities':
            revision = PageRevision(None, None, None, None, None, None, None)

            activities = Activity.query \
                .filter(Activity.end_time > datetime.now()) \
                .order_by(Activity.start_time.asc())
            revision.activity = \
                render_template('activity/view_simple.htm',
                                activities=activities.paginate(1, 4, False))

            revisions.append(revision)

            continue

        page = page_service.get_page_by_path(Page.strip_path(path))
        pages.append(page)

        if not page:
            revision = PageRevision(None, None, None, None, None, None, None)
            revision.title = _('Not found!')
            revision.content = _('Page not found')

            revisions.append(revision)

            continue

        revision = page.get_latest_revision()
        revision.test = path
        if not revision:
            return abort(500)

        revisions.append(revision)

    return revisions


@blueprint.route('/', methods=['GET'])
def home():
    data = ['activities',
            'contact']

    revisions = get_revisions(data)
    news = News.query.filter(News.publish_date <= date.today(),
                             db.or_(News.archive_date >= date.today(),
                                    News.archive_date == None),  # noqa
                             db.or_(current_user.has_paid,
                                    db.not_(News.needs_paid)))\
                     .order_by(desc(News.publish_date)).limit(8).all()

    return render_template('home/home.htm', revisions=revisions,
                           title='Homepage', news=news)
