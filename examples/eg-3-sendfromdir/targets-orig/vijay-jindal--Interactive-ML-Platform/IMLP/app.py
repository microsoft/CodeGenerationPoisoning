"""
Please note for logging use the app's logger functionality
Refer to this : https://flask.palletsprojects.com/en/1.1.x/logging/ and
https://docs.python.org/3/library/logging.html#logging-levels
Ex: app.logger.info("Message")
"""

# TODO : Move all shared import into app.py from all other files.
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import logging
from services.project import Project
import flask
from flask import redirect
# Setting styles and css
# TODO : use assets folder to load css
FONT_AWESOME = "https://use.fontawesome.com/releases/v5.10.2/css/all.css"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', dbc.themes.BOOTSTRAP, FONT_AWESOME]


# Creating object of Dash
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
# app title
app.title = 'Interactive Machine Learning Platform'

app.logger.setLevel(logging.INFO)
server = app.server
# Since we're adding callbacks to elements that don't exist in the app.layout,
# Dash will raise an exception to warn us that we might be
# doing something wrong.
# In this case, we're adding the elements through a callback, so we can ignore
# the exception.
app.config.suppress_callback_exceptions = True

project = Project(app)

@server.route('/downloads/<path>')
def serve_static(path):
    if hasattr(project,'path'):
        return flask.send_from_directory(
            project.path, path, cache_timeout = 0
        )
    else:
        return redirect("/")
# app.layout = html.Div([
#     dcc.Location(id='url', refresh=False),
#     html.Div(id='page-content')
# ])
#
#
# @app.callback(Output('page-content', 'children'),
#               [Input('url', 'pathname'), Input('create_project_btnx', 'n_clicks')],
#               [State('project_name_input', 'value')])
# def display_page(pathname):
#     if pathname == '/':
#         return Homepage()
#
#
# # CALLBACKS
#
#
#
# @app.route('/')
# def imlp():
#     return render_template('dashboard.html')
#
# @app.route('/project/<project_name>')
# def new_project(project_name):
#     project.create(project_name)
#     return redirect('/project/' + project_name + '/upload')
#
#
# @app.route('/project/<project_name>/upload', methods=['GET', 'POST'])
# def upload(project_name):
#     if request.method == 'GET':
#         if hasattr(project, "name") and project_name == getattr(project, "name"):
#             return render_template('upload-csv.html', proj_name=project_name)
#         else:
#             return redirect('/')
#     elif request.method == 'POST' and 'dataset' in request.files:
#         project.upload_dataset(request.files['dataset'])  # allow only csv files in UI and backend
#         # TODO : create instance of dataset class
#         return redirect('/project/' + project_name + '/preprocess')
#     else:
#         return redirect('/')
#
#
# @app.route('/project/<project_name>/preprocess', methods=['GET', 'POST'])
# def preprocess(project_name):
#     if request.method == 'GET':
#         if hasattr(project, "name") and project_name == getattr(project, "name") and hasattr(project, "dataset"):
#             column_names, data_types = project.dataset.info()
#             app.logger.info(column_names)
#             app.logger.info(data_types)
#             app.logger.info(project.dataset.path)
#             return render_template('preprocess.html', path=project.dataset.path, column_names=column_names,
#                                    data_types=data_types, proj_name=project_name, data=project.dataset.df.to_html())
#         else:
#             return redirect('/')
#     elif request.method == 'POST':
#         # From frontend get the following
#         # Type of learning (supervised or unsupervised)
#         # Algorithm Name
#         # Based on learning type get list of columns as features and target variable
#         learn_method = request.form['Learn_Method']
#         algo_name = request.form.get('Algorithm')
#         app.logger.info(learn_method + " " + algo_name)
#
#         if learn_method == "Supervised":
#             # If supervised create a Model with algo name
#             project.create_model(algo_name)
#             # Retrieve list of columns as features and target from POST request
#             X = request.form.getlist('features')
#             y = request.form.get('target')
#             project.dataset.set_features(X)
#             project.dataset.set_target(y)
#             return redirect('/project/' + project_name + '/model')
#         elif learn_method == "Unsupervised":
#             return "WIP"
#         else:
#             return "WIP"
#     else:
#         return redirect('/')
#
#
# @app.route('/project/<project_name>/model', methods=['GET', 'POST'])
# def model(project_name):
#     if request.method == 'GET':
#         if hasattr(project, "name") and project_name == getattr(project, "name") and hasattr(project,
#                                                                                              "dataset") and hasattr(
#                 project, "model"):
#             # Send default parameters available for the model to frontend
#             return render_template('default_params.html', def_params=project.model.get_params(), proj_name=project_name)
#         else:
#             return redirect('/')
#     elif request.method == 'POST':
#         # Get modified parameters in dictionary format and set them using set_params function
#         # get test data size ex: 0.20,0.30 etc
#         # 0.20 means 20% data will be for validation (test)
#         # Also consider possibility of complete training
#         # Show realtime messages from training (set verbose flag in model)
#         set_params_response = project.model.set_params(request.form.to_dict())
#         if set_params_response == 1:
#             return redirect('/project/'+project_name+'/prediction')
#         else:
#             return "{}".format(set_params_response)
#     else:
#         return redirect('/')
#
#
# @app.route('/project/<project_name>/prediction')
# def prediction(project_name):
#     # Show accuracy score
#     # Show confusion matrix
#     # Show classification report
#     # above to be shown from sklearn metrics
#     # Visualizations
#     # return("Hi there {name}, this WIP".format(name="developer"))
#     return (project.model.model_train())
#

#
# if __name__ == '__main__':
#     app.run_server(debug=True)
