from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from observatory.forms.common import (
    PromptDropForm,
    PromptEditForm,
    PromptSortForm,
    SensorDropForm,
    SensorEditForm,
    SensorSortForm,
)
from observatory.forms.mapper import (
    MapperDropForm,
    MapperEditForm,
    MapperSortForm,
)
from observatory.lib.text import extract_slug
from observatory.models.mapper import Mapper
from observatory.models.prompt import Prompt
from observatory.models.sensor import Sensor

BLUEPRINT_MGNT = Blueprint('mgnt', __name__)


@BLUEPRINT_MGNT.route('/manage', endpoint='index')
@BLUEPRINT_MGNT.route('/manage/mapper/view')
@login_required
def view_mapper():
    return render_template(
        'mgnt/view.html',
        title='View mapper',
        mapping=Mapper.query_sorted().all(),
    )


@BLUEPRINT_MGNT.route('/manage/prompt/view')
@login_required
def view_prompt():
    return render_template(
        'mgnt/view.html',
        title='View prompt',
        prompts=Prompt.query_sorted().all(),
    )


@BLUEPRINT_MGNT.route('/manage/sensor/view')
@login_required
def view_sensor():
    return render_template(
        'mgnt/view.html',
        title='View sensor',
        sensors=Sensor.query_sorted().all(),
    )


@BLUEPRINT_MGNT.route(
    '/manage/mapper/edit'
    '/sensor/<string:sensor_slug>'
    '/prompt/<string:prompt_slug>',
    methods=['GET', 'POST'],
)
@BLUEPRINT_MGNT.route(
    '/manage/mapper/edit'
    '/prompt/<string:prompt_slug>'
    '/sensor/<string:sensor_slug>',
    methods=['GET', 'POST'],
)
@BLUEPRINT_MGNT.route(
    '/manage/mapper/edit',
    methods=['GET', 'POST'],
)
@login_required
def edit_mapper(prompt_slug=None, sensor_slug=None):
    title = (
        'Edit mapper' if (prompt_slug and sensor_slug) else 'Create new mapper'
    )
    form = MapperEditForm(
        obj=Mapper.by_commons(
            prompt=Prompt.by_slug(prompt_slug),
            sensor=Sensor.by_slug(sensor_slug),
        )
    )

    if request.method != 'POST':
        form.set_selections()
    if request.method == 'POST' and form.validate_on_submit():
        mapper = form.action()
        if mapper is not None:
            slug = extract_slug(mapper)
            flash(f'Saved mapper {slug}!', 'success')
            return redirect(url_for('mgnt.view_mapper'))

    return render_template(
        'page_form.html',
        title=title,
        form=form,
    )


def _edit_common(form, redirect_ep):
    name = form.Model.__name__.lower()
    title = f'Edit {name}' if form.thing else f'Create new {name}'

    if request.method == 'POST' and form.validate_on_submit():
        thing = form.action()
        if thing is not None:
            flash(f'{name} {thing.slug} saved!', 'success')
            return redirect(url_for(redirect_ep))

    return render_template(
        'page_form.html',
        title=title,
        form=form,
    )


@BLUEPRINT_MGNT.route(
    '/manage/prompt/edit/<string:slug>',
    methods=['GET', 'POST'],
)
@BLUEPRINT_MGNT.route(
    '/manage/prompt/edit',
    methods=['GET', 'POST'],
)
@login_required
def edit_prompt(slug=None):
    return _edit_common(
        PromptEditForm(obj=Prompt.by_slug(slug)),
        'mgnt.view_prompt',
    )


@BLUEPRINT_MGNT.route(
    '/manage/sensor/edit/<string:slug>',
    methods=['GET', 'POST'],
)
@BLUEPRINT_MGNT.route(
    '/manage/sensor/edit',
    methods=['GET', 'POST'],
)
@login_required
def edit_sensor(slug=None):
    return _edit_common(
        SensorEditForm(obj=Sensor.by_slug(slug)),
        'mgnt.view_sensor',
    )


def _drop_generic(form, redirect_ep):
    name = form.Model.__name__.lower()

    if not form.thing:
        abort(500, f'No such {name}!')

    if request.method == 'POST' and form.validate_on_submit():
        slug = extract_slug(form.thing)
        if form.action() is not None:
            flash(f'{name} {slug} deleted!', 'success')

    return redirect(url_for(redirect_ep))


@BLUEPRINT_MGNT.route(
    '/manage/mapper/drop'
    '/prompt/<string:prompt_slug>'
    '/sensor/<string:sensor_slug>',
    methods=['POST'],
)
@login_required
def drop_mapper(prompt_slug, sensor_slug):
    return _drop_generic(
        MapperDropForm(
            obj=Mapper.by_commons(
                prompt=Prompt.by_slug(prompt_slug),
                sensor=Sensor.by_slug(sensor_slug),
            )
        ),
        'mgnt.view_mapper',
    )


@BLUEPRINT_MGNT.route(
    '/manage/prompt/drop/<string:slug>',
    methods=['POST'],
)
@login_required
def drop_prompt(slug):
    return _drop_generic(
        PromptDropForm(obj=Prompt.by_slug(slug)),
        'mgnt.view_prompt',
    )


@BLUEPRINT_MGNT.route(
    '/manage/sensor/drop/<string:slug>',
    methods=['POST'],
)
@login_required
def drop_sensor(slug):
    return _drop_generic(
        SensorDropForm(obj=Sensor.by_slug(slug)),
        'mgnt.view_sensor',
    )


def _sort_generic(form, redirect_ep):
    name = form.Model.__name__.lower()

    if not form.thing:
        abort(500, f'No such {name}!')

    if request.method == 'POST' and form.validate_on_submit():
        slug = extract_slug(form.thing)
        verb = 'raised' if form.lift else 'lowered'
        if form.action() is not None:
            flash(f'{name} {slug} {verb}!', 'success')
        else:
            flash(f'Can not move {name} {slug}!', 'error')

    return redirect(url_for(redirect_ep))


@BLUEPRINT_MGNT.route(
    '/manage/mapper/sort'
    '/prompt/<string:prompt_slug>'
    '/sensor/<string:sensor_slug>'
    '/<any(raise,lower):direction>',
    methods=['POST'],
)
@login_required
def sort_mapper(prompt_slug, sensor_slug, direction):
    return _sort_generic(
        MapperSortForm(
            obj=Mapper.by_commons(
                prompt=Prompt.by_slug(prompt_slug),
                sensor=Sensor.by_slug(sensor_slug),
            ),
            lift=direction == 'raise',
        ),
        'mgnt.view_mapper',
    )


@BLUEPRINT_MGNT.route(
    '/manage/prompt/sort/<string:slug>/<any(raise,lower):direction>',
    methods=['POST'],
)
@login_required
def sort_prompt(slug, direction):
    return _sort_generic(
        PromptSortForm(obj=Prompt.by_slug(slug), lift=direction == 'raise'),
        'mgnt.view_prompt',
    )


@BLUEPRINT_MGNT.route(
    '/manage/sensor/sort/<string:slug>/<any(raise,lower):direction>',
    methods=['POST'],
)
@login_required
def sort_sensor(slug, direction):
    return _sort_generic(
        SensorSortForm(obj=Sensor.by_slug(slug), lift=direction == 'raise'),
        'mgnt.view_sensor',
    )
