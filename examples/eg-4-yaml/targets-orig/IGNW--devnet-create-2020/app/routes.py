from flask import render_template, request
from app import app
from pathlib import Path
from jinja2 import FileSystemLoader, Environment
import flask
import yaml
import importlib
import sys


@app.route('/')
@app.route('/index')
def index():
    # Load up all the scripts from the user directory
    script_data = get_repo_name()
    return render_template('base.j2', scripts=script_data)


@app.route('/script/<script>')
def script_start_point(script):
    script_details = get_repo_name(as_dict=True)
    return render_template('script_start.html', script_details=script_details[script])


@app.route('/run_script/<script>', methods=['GET', 'POST'])
def run_script(script):
    if flask.request.method == 'GET':
        file_path = Path(".") / "repos" / script / "gui" / "main.py"
        file_path = file_path.resolve()

        spec = importlib.util.spec_from_file_location('main', file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules['main'] = module
        main = importlib.import_module('main')

        variables = main.pre()

        return ui(script, "ui.yml", **variables)

    elif flask.request.method == 'POST':
        file_path = Path(".") / "repos" / script / "gui" / "main.py"
        file_path = file_path.resolve()

        spec = importlib.util.spec_from_file_location('main', file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules['main'] = module
        main = importlib.import_module('main')
        form_data = request.form.to_dict()

        output = main.main(**form_data)

        return render_template('output.j2', data=output)


@app.route('/welcome', methods=['GET'])
def welcome():
    return render_template("welcome.html")


def ui(script, ui_name, **kwargs):
    ui_details = {}
    templateLoader = FileSystemLoader(searchpath=f'./repos/{script}/gui')
    templateEnv = Environment(loader=templateLoader)
    template = templateEnv.get_template(ui_name)
    raw_ui = template.render(**kwargs)

    try:
        ui_details = yaml.safe_load(raw_ui)
    except yaml.YAMLError:
        return "Unable to parse the script launcher"

    template = render_template("ui_template.j2", details=ui_details, script=script)
    return(template)


def get_repo_name(as_dict=False):
    p = Path('./repos')

    script_data = [
        {"name": x.parts[-1],
         "id": x.parts[-1],
         "path": x} for x in p.iterdir() if x.is_dir()]

    for repo in script_data:
        config_file = repo['path'] / "gui" / "config.yml"
        config = {}
        if config_file.exists():
            with open(config_file) as cf:
                config = yaml.safe_load(cf)

        if config and config.get('display_name'):
            repo['name'] = config['display_name']
        if config and config.get('description'):
            repo['description'] = config['description']

    if as_dict:
        script_data = {repo['id']: repo for repo in script_data}

    return script_data
