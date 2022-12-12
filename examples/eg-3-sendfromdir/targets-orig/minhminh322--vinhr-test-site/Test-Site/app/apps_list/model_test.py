from _plotly_future_ import v4_subplots
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from plotly import graph_objs as go
import os
import flask
import dash_player as player # https://github.com/plotly/dash-player
import pandas as pd
from plotly.subplots import make_subplots
from src.connectors import cosmos, storage
import DATA
import logging
from apps_list import dataset_model_list
from src.imports import *
from src.helpers import ct2ctts, find_near_time_row, segment
from src.progress_bar import get_progress_bar
from dash.exceptions import PreventUpdate
from appnha import app
import json

single_graph_layout = go.Layout(
        barmode='stack',
        xaxis = go.layout.XAxis(
            range=[0,1000], # TODO : fix the hard code 683 value
            showticklabels = False,
            showgrid=False,
        ),
        yaxis = go.layout.YAxis(
            range=[0.6,1.4],
            showticklabels = False,
            showgrid=False,
        ),
        margin=go.layout.Margin(
            l=20,
            r=20,
            b=0,
            t=0,
            pad=0
        ),
        height=50,
        )


predict_card = [
    dbc.CardImg(src="./assets/images/multicolored-brain-connections.png", style={'height': '50%'}, top=True),
    dbc.CardBody(
        [
            html.H5("Prediction Score", className="card-title"),
            html.P(
                "99.99%",
                id="predict-score",
            ),
            html.Div(dcc.Link(dbc.Button("See your ranking!", color="primary"), href='/model-ranking'), style={'text-align':'center'}),
            
        ]
    ),
    
]

performance_card = [
    dbc.CardHeader("Performance Evaluation", className="header-card"),
    dbc.CardBody(
        [
            # html.H5("Card title", className="card-title"),
            html.P(
                
                id="perform-info",
            )
        ]
    ),
]


## Data set and model description:
dataset_card = [
    dbc.CardHeader("DataSet", className="header-card"),
    dbc.CardBody(
        [
            # html.H5("Card title", className="card-title"),
            html.P(
                
                style={'font-size': '15px'},
                id="dataset-info",
            ),
        ]
    ),
]

model_card = [
    dbc.CardHeader("Model Description", className="header-card"),
    dbc.CardBody(
        [
            # html.H5("Card title", className="card-title"),
            html.P(
                style={'font-size': '15px'},
                id="model-info",
            ),
        ]
    ),
]

attribute_cards = dbc.CardDeck(
    [
        dbc.Card(dataset_card, className='each-card', color="primary", inverse=True),
        dbc.Card(model_card, className='each-card', color="success", inverse=True),
        dbc.Card(performance_card, className='each-card', color="warning", inverse=True),
        dbc.Card(predict_card, className='each-card', color="danger", inverse=True),
        
    ],
    id='card-deck'
)

video_player = [html.Div([
                    html.H3(id="video-title"),
                    player.DashPlayer(
                        id='video-player',
                        url='',
                        controls=True,
                        width='100%',
                        height='400px',
                        playing=True),
                    ], id='video-wrapper'),
                dcc.Graph(id='progress-bar',
                    figure = go.Figure(data=[], layout=single_graph_layout),
                    config={
                        'displayModeBar': False,
                        'staticPlot': False
                        },
                    ),

                ]

# Tin hieu thu duoc
signal_data = [          
                html.H3("Coming Up Soon!!!", style={'text-align':'center'}),
                # dcc.Graph(id='signal-graph',
                #     config={
                #         'displayModeBar': False,
                #         'staticPlot':True,
                #     }),
         
         
        ]

# crutial function but invisible
others = [
    html.Button('Start', id='start', style={"display":"None"}),
    dcc.Interval(
            id='interval-progress-bar',
            interval=4500, # in milliseconds
            n_intervals=0
    ),
    html.Div([
        dcc.Slider(
                    id='slider-intervalCurrentTime',
                    min=200,
                    max=20000,
                    step=None,
                    updatemode='drag',
                    marks={i: str(i) for i in [200, 500, 750, 1000, 2000]},
                    value=5000)
    ], style={"display":"None"})
]

layout = html.Div([

    dbc.Row([
        dbc.Col(html.Div(attribute_cards, id="col1", className='col1'), width=12),
        # dbc.Col(html.P(id='testing-input'), width=4)
    ],id="row1", className='row'),

    dbc.Row([
        dbc.Col(html.Div(video_player, id="col2", className='col2'), width=8)
    ], justify='center'),

    dbc.Row([
        dbc.Col(html.Div(signal_data,id="signal-window"), width=8),
    ], id="row2", justify='center'),


    html.Div(others),

], className="background")


# # Action when click on Test button
# @app.callback(
#     [Output('data-memory', 'data'),
#     Output('model-memory', 'data')],
#     [Input('get-ids-memory', 'data')]
# )
# def output_text(data_dict):
#     if not data_dict:
#         raise PreventUpdate
    
#     print(data_dict)
#     df_dataset = cosmos.query(DATA.DB['dataset_table'], {'_id': data_dict['data_id']})
#     df_model = cosmos.query(DATA.DB['model_table'], {'_id': data_dict['model_id']})

#     return df_dataset.to_json(date_format='iso', orient='split'), df_model.to_json(date_format='iso', orient='split')



# Dataset description
@app.callback(
    Output('dataset-info', 'children'),
    [Input('data-memory', 'data')]
)
def choose_dataset_from_list(data_json):
    if data_json is None:
        raise PreventUpdate

    df_dataset = pd.read_json(data_json, orient='split')
    #Unpack data from user's choice
    name = df_dataset.loc[0, 'data_filename']
    date = name.split(' ')[1]
    Owner = 'minhphan'
    return [
        html.P(f"Name : {name}"),
        html.P(f"Date : {date}"),
        html.P(f"Owner : {Owner}"),
        # html.P(f"Location: {}")
    ]


# Model description
@app.callback(
    Output('model-info', 'children'),
    [Input('model-memory', 'data')]
)
def choose_model_from_list(model_json):
    if model_json is None:
        raise PreventUpdate
    
    
    #Unpack data from user's choice
    df_model = pd.read_json(model_json, orient='split')
    name = df_model.loc[0, 'model_name']
    window = df_model.loc[0, 'model_windowsize']
    transform = df_model.loc[0, 'model_transformation']
    return [
        html.P(f"Model Name : {name}"),
        html.P(f"Window Size : {window}"),
        html.P(f"Transformation : {transform}"),
    ]

# Performance Evaluation
@app.callback(
    Output('perform-info', 'children'),
    [Input('data-memory', 'data'),
    Input('model-memory', 'data')]
)
def choose_dataset_from_list(data_json, model_json):
    if (data_json or model_json) is None:
        raise PreventUpdate

    df_dataset = pd.read_json(data_json, orient='split')
    df_model = pd.read_json(model_json, orient='split')
    # print(type(df_dataset.loc[0, '_id']))
    #Unpack data from user's choice
    result_data = cosmos.query(DATA.DB['result_table'], 
    {'_id_dataset': int(df_dataset.loc[0, '_id']),
    '_id_model': int(df_model.loc[0, '_id'])})

    accuracy = result_data.loc[0, 'accuracy']
    process_time = result_data.loc[0, 'processing_time']
    # tbd = result_data.loc[0, 'tbd']
    return [
        html.P(f"Accuracy : {accuracy}"),
        html.P(f"Processing Time : {process_time}"),
        # html.P(f"TBD : {tbd}"),
    ]

# Get url to play video 
@app.callback(
    Output('video-player', 'url'),
    [Input('data-memory', 'data')]
)
def prepare_data(data_json):
    if data_json is None:
        raise PreventUpdate
    
    df_dataset = pd.read_json(data_json, orient='split')

    video_filename = df_dataset.loc[0, 'video_filename']
    data_filename = df_dataset.loc[0, 'data_filename']

    # go to Azure storage
    client = storage.azure_client()

    # # check if dataset is already downloaded
    # if os.path.isfile(f'./static/dataset/{data_filename}') == False:
    #     # download csv file to ./static/dataset/
    #     storage.download_blob_to_folder(client, 'dataset', data_filename)
    
    if os.path.isfile(f'./static/prediction/{data_filename}') == False:
        storage.download_blob_to_folder(client, 'prediction', data_filename)

    # url to download video file
    url = storage.get_blob_url(client, 'video', video_filename)
    print('Generate SAS link for video:' + url)

    return url

@app.callback(Output('progress-bar', 'figure'),
              [Input('interval-progress-bar', 'n_intervals')],
              [State('video-player','currentTime'),
              State('data-memory','data'),
              State('prediction-memory','data')])
def progress_bar(n, currentTime, data_json, pred_json):
    if not (data_json and pred_json):
        raise PreventUpdate
    
    df_pred = pd.read_json(pred_json, orient='split')
    df_pred['Timestamp']= df_pred['Timestamp'].apply(pd.to_datetime).dt.tz_convert('Asia/Saigon')
    df_pred['Prob'] = (df_pred.Prob*100).map('{:,.2f}'.format)

    #Unpack data from user's choice
    df_dataset = pd.read_json(data_json, orient='split')
    video_filename = df_dataset.loc[0, 'video_filename']
    videotime_str = video_filename.split('.')[0]

    fig = go.Figure()
    if currentTime is None :  return fig
    ctts = ct2ctts(currentTime, videotime_str)
    fig = get_progress_bar(df_pred, ctts, DATA.df_label_map)
    return fig

# @app.callback(Output('signal-graph', 'figure'),
#               [Input('interval-progress-bar', 'n_intervals')],
#               [State('video-player','currentTime'),
#               State('data-memory', 'data'),
#               State('dataset-memory', 'data')])
# def signal_graph(n, currentTime, data_dict, dataset_json):
#     if not (data_dict and dataset_json):
#         raise PreventUpdate
    
#     dataset_json = json.loads(dataset_json)
#     df_data['loggingTime(txt)']= df_data['loggingTime(txt)'].apply(pd.to_datetime).dt.tz_convert('Asia/Saigon')

#     # print(df_data['loggingTime(txt)'])
#     #Unpack data from user's choice
#     # TODO : get rid of this query
#     dataset_data = cosmos.query(DATA.DB['dataset_table'], {'_id': data_dict['dataset_id']})

#     video_filename = dataset_data.loc[0, 'video_filename']
#     # data_filename = dataset_data.loc[0, 'data_filename']
#     videotime_str = video_filename.split('.')[0]

#     fig = go.Figure()
#     if currentTime is None :  return fig
#     ctts = ct2ctts(currentTime, videotime_str)
#     index, row = find_near_time_row(df_data, ctts, time_col='loggingTime(txt)')
#     if index is None : return fig
    
#     df_tmp = df_data.iloc[index:index+400]


#     signals_group = {
#         'Acceleration' : {
#             'accelerometerAccelerationX(G)' : 'AccelX(G)',
#             'accelerometerAccelerationY(G)' : 'AccelY(G)',
#             'accelerometerAccelerationZ(G)' : 'AccelZ(G)'
#         },
#         'Rotation Rate' : {
#             'motionRotationRateX(rad/s)':'RotateX(rad/s)',
#             'motionRotationRateY(rad/s)':'RotateY(rad/s)',
#             'motionRotationRateZ(rad/s)':'RotateZ(rad/s)',
#         },
#         'Rotation': { 
#             'motionYaw(rad)' : 'Yaw',
#             'motionRoll(rad)' : 'Roll',
#             'motionPitch(rad)' : 'Pitch',
#         },
#         'Gravity' : {
#             'motionGravityX(G)':'GravityX(G)',
#             'motionGravityY(G)':'GravityY(G)',
#             'motionGravityZ(G)':'GravityZ(G)',
#         },
#     }

    
#     fig = make_subplots(
#         rows=1, cols=len(signals_group.items()),
#         subplot_titles=list(signals_group.keys())
#     )
#     for i, (group, sensor_map) in enumerate(signals_group.items()):
#         for col, display_name in sensor_map.items():
#             fig.add_trace(go.Scatter(
#                                 x = df_tmp['loggingTime(txt)'],
#                                 y = df_tmp[col],
#                                 name = display_name,
#                                 showlegend=False,
#                                 legendgroup = group
#                 ), row = 1, col = i+1)

#     fig.layout.update(
#         xaxis1=dict(
#             showticklabels = False,
#         ),
#         xaxis2=dict(
#             showticklabels = False
#         ),
#         xaxis3=dict(
#             showticklabels = False
#         ),
#         xaxis4=dict(
#             showticklabels = False,
#             #showgrid = False,
#         ),

#         yaxis1=dict(
#             showticklabels = False,
#             range = [-10,10]
#         ),
#         yaxis2=dict(
#             showticklabels = False,
#             range = [-10,10]
#         ),
#         yaxis3=dict(
#             showticklabels = False,
#             range = [-4,4]
#         ),
#         yaxis4=dict(
#             showticklabels = False,
#             range = [-2,2],
#             #showgrid = False,
#         ),

#         margin = go.layout.Margin(
#             l=0,
#             r=0,
#             b=0,
#             t=50,
#             pad = 0,
#             ),
#         height=235,

#     )
    
#     return fig

# for nothing, just need it here
@app.callback(Output('video-player','playing'),
        [Input('start','n_clicks')])
def start_video(n):
    return True
@app.callback(Output('video-player', 'intervalCurrentTime'),
              [Input('slider-intervalCurrentTime', 'value')])
def update_intervalCurrentTime(value):
    return 1000
@app.callback(
    dash.dependencies.Output('hidden-div', 'children'),
    [dash.dependencies.Input('play', 'n_clicks')])
def update_output(n_clicks):
    return n_clicks


# # to serve media files
# @server.route('/static/<path:path>')
# def serve_static(path):
#     root_dir = os.getcwd()
#     return flask.send_from_directory(os.path.join(root_dir, 'static'), path)


