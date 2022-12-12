from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    make_response)

from app.crawl.house_crawler import HouseCrawler
from app.mongodb.mongodb_manager import MongoDbManager
from app.crawl.crawl_manager import CrawlManager
from app.query_form import QueryForm

BP = Blueprint(
    'root', __name__, url_prefix='')


@BP.route("/", methods=["GET"])
def index():
    return render_template('index.html', title=current_app.config.get('PAGE_TITLE'))


@BP.route("/start", methods=["POST"])
def start_crawl():
    crawl_manager = HouseCrawler.get_instance()
    if not crawl_manager.is_running():
        message = crawl_manager.run()
        data = {'message': message, 'code': 'SUCCESS'}
    else:
        data = {'message': 'crawler already exists...', 'code': 'DUPLICATED'}
    return make_response(data, 201)


@BP.route("/stop", methods=["POST"])
def stop_crawl():
    crawl_manager = HouseCrawler.get_instance()
    if crawl_manager.stop():
        return make_response({'message': 'stopped.'}, 201)
    else:
        return make_response({'message': 'Nothing to stop.'}, 201)


@BP.route("/search", methods=["POST"])
def query():
    payload = request.json or request.form
    current_app.logger.info('the payload from frontend: {}'.format(str(payload)))
    form = QueryForm()
    if not form.validate():
        message = '\n'.join([error + ': ' + str(info) for error, info in form.errors.items()])
        current_app.logger.info('Error! form fields not valid! {}'.format(message))
        return make_response({'message': message, 'data': ''}, 201)

    manager = MongoDbManager.get_instance()
    if manager is not None and manager.get_client() is not None:
        data = manager.query_by_pattern(form.to_dict())
        length = data.count()
        current_app.logger.info('/search : Found {} records. '.format(length))
        return make_response({'message': 'got ' + str(length) + ' result',
                              'data': '\n'.join([str(record) for record in data[:100]])}, 201)
    else:
        message = 'Fail to get MongoDBManager!'
        current_app.logger.info('/search : Error! ' + message)
        return make_response({'message': message, 'data': ''}, 201)

