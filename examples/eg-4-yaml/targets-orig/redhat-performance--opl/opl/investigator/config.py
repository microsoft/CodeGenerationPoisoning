import logging
import os

import jinja2

import yaml


def render_sets(args, template_data):
    if not isinstance(args.sets, str):
        logging.debug("No need to render, sets is already a list")
        return

    logging.debug(f"Rendering Jinja2 template sets {args.sets} with data {template_data}")
    env = jinja2.Environment(
        loader=jinja2.DictLoader({'sets': args.sets}))
    template = env.get_template('sets')
    rendered = template.render(template_data)
    logging.debug(f"Rendered Jinja2 template sets {rendered}")
    args.sets = yaml.load(rendered, Loader=yaml.SafeLoader)


def render_query(args, template_data):
    logging.debug(f"Rendering Jinja2 template query {args.history_es_query} with data {template_data}")
    env = jinja2.Environment(
        loader=jinja2.DictLoader({'query': args.history_es_query}))
    template = env.get_template('query')
    rendered = template.render(template_data)
    logging.debug(f"Rendered Jinja2 template query {rendered}")
    args.history_es_query = yaml.load(rendered, Loader=yaml.SafeLoader)


def render_matchers(args, template_data):
    logging.debug(f"Rendering Jinja2 template matchers {args.history_matchers} with data {template_data}")
    env = jinja2.Environment(
        loader=jinja2.DictLoader({'matchers': args.history_matchers}))
    template = env.get_template('matchers')
    rendered = template.render(template_data)
    logging.debug(f"Rendered Jinja2 template matchers {rendered}")
    args.history_matchers = yaml.load(rendered, Loader=yaml.SafeLoader)


def load_config_finish(args, sd):
    template_data = {'current': sd, 'environ': os.environ}
    render_sets(args, template_data)
    if args.history_type == 'elasticsearch':
        render_query(args, template_data)
    if args.history_type == 'sd_dir':
        render_matchers(args, template_data)


def load_config(conf, fp):
    """
    Load config from yaml file pointer and add to conf which is an ArgParser namespace
    """
    data = yaml.load(fp, Loader=yaml.SafeLoader)
    logging.debug(f"Loaded config from {fp.name}: {data}")

    conf.history_type = data['history']['type']
    conf.current_type = data['current']['type']
    conf.methods = data['methods'] if 'methods' in data else []
    conf.sets = data['sets']
    conf.decisions_type = data['decisions']['type']

    if conf.history_type == 'csv':
        conf.history_file = open(data['history']['file'], 'r')

    if conf.history_type == 'elasticsearch':
        conf.history_es_server = data['history']['es_server']
        assert not conf.history_es_server.endswith('/')
        conf.history_es_index = data['history']['es_index']
        conf.history_es_query = data['history']['es_query']

    if conf.history_type == 'sd_dir':
        conf.history_dir = data['history']['dir']
        conf.history_matchers = data['history']['matchers']

    if conf.current_file is None:
        if conf.current_type == 'status_data':
            conf.current_file = open(data['current']['file'], 'r')

    if conf.decisions_type == 'elasticsearch':
        conf.decisions_es_server = data['decisions']['es_server']
        assert not conf.decisions_es_server.endswith('/')
        conf.decisions_es_index = data['decisions']['es_index']
    if conf.decisions_type == 'csv':
        conf.decisions_filename = data['decisions']['filename']
