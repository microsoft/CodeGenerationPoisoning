# Imports from 3rd party libraries
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from app import application, app
from pages import index
import dash_html_components as html
import dash_core_components as dcc

from dash.dependencies import Input, Output
from flask import Flask, send_from_directory
from pages import index, peace, reflection, shopping, todo



#serve favicon
server = Flask(__name__, static_folder='static')
@server.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(server.root_path, 'static'),
                               'favicon.ico', mimetype='assets/favicon.ico')



# Footer docs:
# dbc.Container, dbc.Row, dbc.Col: https://dash-bootstrap-components.opensource.faculty.ai/l/components/layout
# html.P: https://dash.plot.ly/dash-html-components
# fa (font awesome) : https://fontawesome.com/icons/github-square?style=brands
# mr (margin right) : https://getbootstrap.com/docs/4.3/utilities/spacing/
# className='lead' : https://getbootstrap.com/docs/4.3/content/typography/#lead


staticNav = dbc.Col(
    [
        html.Div(
            html.Center(
                children=[
                        html.Img(src=app.get_asset_url('logo.png'), style={'display': 'block', 'paddingBottom':11, 'paddingTop':11,'width': 130}),
                        html.Img(src=app.get_asset_url('topBanner.png'), style={'display': 'block', 'width':'37%'})
                ]),
        )
    ],
    md=12,
)









# card_content_iceland = [
#     dbc.CardHeader(
#     dbc.CardLink("Iceland's Mass Testing Finds Half of Carriers Show No Symptoms", href="https://english.alarabiya.net/en/features/2020/03/25/Coronavirus-Iceland-s-mass-testing-finds-half-of-carriers-show-no-symptoms", style={'color':'#e2fdf1'}),
#     ),
#     dbc.CardBody(
#         [
#             html.H5("News Snippet", className="card-title"),
#             html.P(
#                 "Iceland has conducted the highest Covid-19 tests per capita, including testing for those who don’t exhibit any symptoms and have found that about half of those who tested positive are non-symptomatic.",
#                 className="card-text",
#             ),
#         ]
#     ),
# ]

# card_content_talks = [
#     dbc.CardHeader(
#         children=[
#             dbc.CardLink("Youtube Live Yoga Classes. A daily livestream of classes at 10 AM, 3PM, 5PM, 8PM", href="https://www.youtube.com/playlist?list=PL4z1_0UdNR70GZE9eGuDY_VlQBE78ebQ8&", style={'color':'#e2fdf1'}),
#             dbc.CardBody([
#                 dbc.CardLink("Apartment-friendly Cardio", href="https://www.youtube.com/channel/UCpQ34afVgk8cRQBjSJ1xuJQ", style={'color':'#e2fdf1'}),
#             ]),
#             dbc.CardLink("30-Day Yoga for Beginners", href="https://www.youtube.com/watch?v=KWBfQjuwp4E&list=PLui6Eyny-UzzFFfpiil94CUrWKVMaqmkm", style={'color':'#e2fdf1'}),
#             dbc.CardBody([
#                 dbc.CardLink("Live Stream a Dance Party and Dance Along Every Night 11pm - Midnight", href="http://www.instagram.com/clubquarantine", style={'color':'#e2fdf1'}),
#             ]),
#         ]
#     # dbc.CardBody(
#     #     [
#     #         html.H5("Online Event", className="card-title"),
#     #         html.P(
#     #             "A daily livestream of classes at 10 AM, 3PM, 5PM, 8PM",
#     #             className="card-text",
#     #         ),
#     #     ]
#     ),
# ]

# card_content_testinginfo = [
#     dbc.CardHeader(
#     dbc.CardLink("How Does the Test for Covid-19 Work? Here's an Infographic that Explains.", href="https://www.compoundchem.com/2020/03/19/covid-19-testing/", style={'color':'#e2fdf1'}),
#     ),
#     dbc.CardBody(
#         [
#             html.H5("Learn...", className="card-title"),
#             html.P(
#                 "Less testing means it is harder to track the spread of the infection and isolate the contacts of the infected. Current tests cannot tell us whether someone had the virus but have subsequently recovered.",
#                 className="card-text",
#             ),
#         ]
#     ),
# ]

# newscards = dbc.Col(
#     [
#         html.Div(
#             [
#                 dbc.Row(
#                     [
#                         dbc.Col(dbc.Card(card_content_iceland, color="info", inverse=True)),
#                         dbc.Col(dbc.Card(card_content_talks, color="info", inverse=True)),
#                         dbc.Col(dbc.Card(card_content_testinginfo, color="info", inverse=True)),
#                     ],
#                     className="mb-4",
#                 ),
#             ]
#         )
#     ],
#     md=8,
# )


announcementsHeader = dbc.Col(
    [
        html.Center(
            children=[
            html.Img(src=app.get_asset_url('helpfulInfo.png'), style={'display': 'block', 'width':'100%','marginTop':70})
            ]
        )
    ],
    md=8,
)


firstAnnoucementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("How will we know when to reopen the country?", className="display-4", style={"color":"#03607d"}),
                        html.P(
                            "In an American Enterprise Institute report, Scott Gottlieb, Caitlin Rivers, Mark B. McClellan, Lauren Silvis and Crystal Watson staked out four goal posts for recovery: Hospitals in the state must be able to safely treat all patients requiring hospitalization, without resorting to crisis standards of care; the state needs to be able to at least test everyone who has symptoms; the state is able to conduct monitoring of confirmed cases and contacts; and there must be a sustained reduction in cases for at least 14 days.",
                            className="lead", style={"color":"#03607d"},
                        ),
                        html.Hr(className="my-2"),
                        html.P(dbc.Button("Read the American Enterprise Institute report", color="info", href="https://www.aei.org/wp-content/uploads/2020/03/National-Coronavirus-Response-a-Road-Map-to-Recovering-2.pdf"), className="lead"),
                    ]
                )
            ]
        )
    ],
    md=8,
)

transitAnnoucementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("Transit", className="display-4", style={"color":"#03607d"}),
                        html.P(
                            "MTA Bus Riders Ride for Free "
                            "(Express Bus Riders Still Pay)",
                            className="lead", style={"color":"#03607d"},
                        ),
                        html.Hr(className="my-2"),
                        html.P(
                            "Subway Service Cut by a Quarter", style={"color":"#03607d"}),
                        html.P("No. 4, 5, 6, 7 and the J and D lines, will run locally on all or part of their routes", style={"color":"#03607d"}),
                        html.P(dbc.Button("Read more", color="info", href="https://www.nytimes.com./2020/03/24/nyregion/coronavirus-nyc-mta-cuts-.html"), className="lead"),
                    ]
                )
            ]
        )
    ],
    md=8,
)


healthInsuranceAnnoucementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("Getting Health Insurance", className="display-4", style={"color":"#03607d"}),
                        html.P(
                            "NY State of Health",
                            className="lead", style={"color":"#03607d"},
                        ),
                        html.Hr(className="my-2"),
                        html.P(
                            "NY State of Health is working on helping New Yorkers get the coverage they need", style={"color":"#03607d"}),
                        html.P("Contact the Marketplace directly at 518-486-9102 or NYSOH@health.ny.gov", style={"color":"#03607d"}),
                        html.P(dbc.Button("Go To The NY State of Health", color="info", href="https://nystateofhealth.ny.gov/"), className="lead"),
                    ]
                )
            ]
        )
    ],
    md=8,
)


shopAnnouncementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("Emergency Food Assistance", className="display-6", style={"color":"#03607d"}),
                        html.Span(' ', className='mr-1'),
                        html.P("Everyone is eligible for emergency food assistance, regardless of immigration status or how much money you have.", style={"color":"#03607d"}, className="lead"),
                        html.P(dbc.Button("Read more", color="info", href="https://access.nyc.gov/programs/emergency-food-assistance/"), className="lead"),
                        html.H1("Special Shopping Hours", className="display-6", style={"color":"#03607d", 'marginTop':70}),
                        html.Span(' ', className='mr-1'),
                        html.P("Whole Foods are open one hour before their normal opening time for seniors 60 and above every day.", style={"color":"#03607d"}, className="lead"),
                        html.P("Trader Joe's are open just for seniors 65 and above 9 a.m. to 10 a.m. every day.", className="lead", style={"color":"#03607d"}),
                        html.Hr(className="my-2"),
                        html.P("Stop-and-Shop's are open 6 am to 7:30 am every day for those age 60 and older and younger customers with weakened immune systems.", style={"color":"#03607d"},className="lead"),
                        html.P("Costco's are open for seniors over age 60 on Tuesdays and Thursdays from 8 to 9 a.m.", style={"color":"#03607d"},className="lead"),
                        html.P("Walgreens has Tuesday weekly senior hour from 8 to 9 a.m., open to caregivers and immediate families, as well.", style={"color":"#03607d"},className="lead"),
                        html.Hr(className="my-2"),
                        html.P("Most top retailers have begun offering senior shopping hours, please look on their website for more information.", style={"color":"#03607d"}
                        ),
                        html.P(dbc.Button("Read more", color="info", href="https://www.cnbc.com/2020/03/19/coronavirus-how-senior-shopping-hours-work-at-stop-shop-other-grocers.html"), className="lead"),
                    ]
                )
            ]
        )
    ],
    md=8,
)

taxesAnnouncementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("Filing Income Tax", className="display-6", style={"color":"#03607d"}),
                        html.Span(' ', className='mr-1'),
                        html.P("New York State's income tax filing deadline is delayed until July 15, 2020.", style={"color":"#03607d"}, className="lead"),
                        html.Hr(className="my-2"),
                        html.P("Because New York State requires electronic filing, the date for filing state personal income taxes automatically travels with the federal filing date, which is now July 15. ", style={"color":"#03607d"}),
                        html.P(dbc.Button("Read more", color="info", href="https://www.tax.ny.gov/default.htm"), className="lead"),
                    ]
                )
            ]
        )
    ],
    md=8,
)

testingAnnouncementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("Getting Tested for Covid-19", className="display-6", style={"color":"#03607d"}),
                        html.Span(' ', className='mr-1'),
                        html.P("Residents who would like to be tested will be prioritized based on risk.", style={"color":"#03607d"}, className="lead"),
                        html.P("High risk includes being over 65 years old, includes serious obesity (defined as BMI >40), lung disease, asthma, heart condition, diabetes, kidney or liver or autoimmune issues, cancer treatment, smoking according to coronavirus.gov. ", style={"color":"#03607d"}, className="lead"),
                        html.Hr(className="my-2"),
                        html.P("If you would like to be tested, here are contact information and pre-assessment screening to pre-register.", style={"color":"#03607d"}),
                        html.P(dbc.Button("Get More Information", color="info", href="https://covid19screening.health.ny.gov/", className="lead"),),
                        html.H1("Have You Recovered From Having Covid-19?", className="display-6", style={"color":"#03607d",'marginTop':70}),
                        html.Span(' ', className='mr-1'),
                        html.P("If you have had Covid-19 and have recovered and cleared, consider participating in studies in helping doctors who are working on finding a cure.", style={"color":"#03607d"}, className="lead"),
                        html.P(dbc.Button("How you can help", color="info", href="https://www.facebook.com/desireedawns/posts/10121953787625504)", className="lead"),),
                    ]
                )
            ]
        )
    ],
    md=8,
)

unemploymentAnnouncementsCenter = dbc.Col(
    [
        html.Center(
            children=[
                dbc.Jumbotron(
                    [
                        html.H1("Filing for Unemployment", className="display-6", style={"color":"#03607d"}),
                        html.Span(' ', className='mr-1'),
                        html.P("If you filed for unemployment during the COVID-19 pandemic, you do not need to prove you are searching for employment to make a claim. ", style={"color":"#03607d"}, className="lead"),
                        html.Hr(className="my-2"),
                        html.P("Department of Labor Commissioner Reardon has signed a new order that limits all work search activities for all unemployment claimants. No activities are required during the pandemic to receive unemployment benefits.", style={"color":"#03607d"}),
                        html.P(dbc.Button("Read more", color="info", href="https://labor.ny.gov/ui/how_to_file_claim.shtm"), className="lead"),

                        html.H1("What Industries are Hiring", className="display-6", style={"color":"#03607d",'marginTop':70}),
                        html.Span(' ', className='mr-1'),
                        html.P("Healthcare", style={"color":"#03607d"}, className="lead"),
                        html.P("Telecom & Remote Work", style={"color":"#03607d"}, className="lead"),
                        html.P("Supply Chain & Essential Businesses", style={"color":"#03607d"}, className="lead"),
                        html.P("E-Commerce & Online Only Stores", style={"color":"#03607d"}, className="lead"),
                        html.P("Insurance", style={"color":"#03607d"}, className="lead"),
                        html.Hr(className="my-2"),
                        html.P("Here's a helpful spreadsheet for tracking your job applications originally published on TheMuse. Please make a copy for yourself!", style={"color":"#03607d"}),
                        html.P(dbc.Button("Go to Spreadsheet", color="info", href="https://docs.google.com/spreadsheets/d/1b4_lpHeLb9NldVWgWKq14nMxHEvlF3qMpEd3QdOc7Ck/edit"), className="lead"),

                        html.P("Get the live-updated hiring status of various organizations.", style={"color":"#03607d",'margintop':70}),
                        html.P(dbc.Button("See Who's Hiring", color="info", href="https://candor.co/hiring-freezes/"), className="lead"),
                    ]
                )
            ]
        )
    ],
    md=8,
)







washHandsC = dbc.Col(
    [
        html.Center(
            children=[
            html.Img(src=app.get_asset_url('WashHands.jpg'), style={'display': 'block', 'width':'100%', 'marginTop':70})
            ]
        )
    ],
    md=6,
)

distanceCenter = dbc.Col(
    [
        html.Center(
            children=[
            html.Img(src=app.get_asset_url('SocialDistancing.png'), style={'display': 'block', 'width':'100%'})
            ]
        )
    ],
    md=6,
)


pod1 = [
    dbc.CardImg(src=app.get_asset_url('podcastButtonL.jpg'), style={'display': 'block', 'width':'70%'}, top=True),
    dbc.CardBody(
        [
            html.H5("What's your Plan", className="card-title"),
            html.P(
                "Create a binder with all important documents.",
                className="card-text",
            ),
            dbc.Button("Plan", className="mr-1", color="info", href="https://www.diypreparedness.net/how-to-make-your-own-family-emergency-binder/"),
        ]
    ),
]

trisacard = [
    dbc.CardImg(src=app.get_asset_url('trisaBunny.gif'), style={'display': 'block', 'width':'70%'}, top=True),
    dbc.CardBody(
        [
            html.H5("Trisa's Picks", className="card-title"),
            html.P(
                "Watch things that make you laugh, smile, or feel good.",
                className="card-text",
            ),
            dbc.Button("To Playlist", className="mr-1", color="info",href='https://www.youtube.com/playlist?list=PL7ESOL-2KOIUs4s61OyCJ8oO9C5n996_b'),
        ]
    ),
]

pod2 = [
    dbc.CardImg(src=app.get_asset_url('podcast2.jpg'), style={'display': 'block', 'width':'70%'}, top=True),
    dbc.CardBody(
        [
            html.H5("Our go-to Podcasts", className="card-title"),
            html.P(
                "Get informed and work on a better self.",
                className="card-text",
            ),
            dbc.Button("Listen Now", className="mr-1", color="info", href="https://open.spotify.com/playlist/65XgqkWUTIdLZm9rXqTp3x"),
        ]
    ),
]


recsCenter = dbc.Col(
    [
        html.Center(
            children=[
                html.Span(' ', className='mr-1'),
                dbc.CardGroup(
                    dbc.Card(
                        dbc.CardBody(
                            dbc.CardColumns(
                                [
                                    dbc.Card(pod1, color="light"),
                                    dbc.Card(trisacard, color="light"),
                                    dbc.Card(pod2, color="light"),
                                ]
                            )
                        )
                    )
                )
            ]
        )
    ],
    md=10,
)
singleColumn = dbc.Col([],md=1)
doubleColumn = dbc.Col([],md=2)
tripleColumn = dbc.Col([],md=3)











footer = dbc.Col([
            html.Div(
            [
                dbc.Alert(
                    html.Center(
                                    [
                                        html.Span(' ', className='mr-1'), 
                                        html.Br(),
                                        html.A(html.I(className='fa fa-id-card mr-1'), href='http://dataanalyticsnyc.com/',style={"marginTop": 10}), 
                                        html.A(html.I(className='fab fa-github mr-1'), href='https://github.com/LilySu/Covid-19nyc'), 
                                        html.A(html.I(className='fab fa-linkedin mr-1'), href='https://www.linkedin.com/in/lilyxsu/'),
                                        html.A(html.I(className='fab fa-twitter-square mr-1'), href='https://twitter.com/printing_3d'),
                                        html.A(html.I(className='fab fa-facebook-square mr-1'), href='https://www.facebook.com/dataAnalyticsNYC/?ref=bookmarks'),
                                        html.A(html.I(className='fa fa-inbox mr-1'), href='mailto:lilyxsu@gmail.com'),
                                        html.Br(),
                                        html.Span(' ', className='mr-1'), 
                                        html.Br(),
                                    ], 
                                    className='lead', style={ 'fontSize': 18}
                    ),
                    color="danger"),
            ]
        )],
        md=12,
    )


# Layout docs:
# html.Div: https://dash.plot.ly/getting-started
# dcc.Location: https://dash.plot.ly/dash-core-components/location
# dbc.Container: https://dash-bootstrap-components.opensource.faculty.ai/l/components/layout
app.layout = html.Div([
                dcc.Location(id='url', refresh=False), 
                dbc.Row([staticNav]),
                dbc.Spinner(html.Div(
                    children=[
                        #dbc.Row([singleColumn, navbar, singleColumn]),
                        html.Hr(),
                        dbc.Container(id='page-content', className='mt-12', fluid=True), 
                    ],
                    id="loading-output"), color="info"),
                # dbc.Row([doubleColumn,newscards,doubleColumn]),   
                dbc.Row([doubleColumn, announcementsHeader,doubleColumn]),
                dbc.Row([doubleColumn, firstAnnoucementsCenter,doubleColumn]),
                dbc.Row([doubleColumn, healthInsuranceAnnoucementsCenter, doubleColumn]),
                dbc.Row([doubleColumn, transitAnnoucementsCenter, doubleColumn]),
                dbc.Row([doubleColumn, shopAnnouncementsCenter, doubleColumn]), 
                dbc.Row([doubleColumn, testingAnnouncementsCenter, doubleColumn]),
                dbc.Row([doubleColumn, taxesAnnouncementsCenter, doubleColumn]),
                dbc.Row([doubleColumn, unemploymentAnnouncementsCenter, doubleColumn]),

                dbc.Row([tripleColumn,washHandsC,tripleColumn]),

                dbc.Row([tripleColumn, distanceCenter, tripleColumn]),
                dbc.Row([singleColumn,recsCenter,singleColumn]),      
                html.Hr(), 
                footer,
])


@app.callback(
    Output("loading-output", "children"), [Input("loading-button", "n_clicks")]
)

# URL Routing for Multi-Page Apps: https://dash.plot.ly/urls
@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/':
        return index.layout
    elif pathname == '/todo':
        return todo.layout
    elif pathname == '/peace':
        return peace.layout
    elif pathname == '/reflection':
        return reflection.layout
    elif pathname == '/shopping':
        return shopping.layout
    else:
        return dcc.Markdown('## Page not found')

# Run app server: https://dash.plot.ly/getting-started
if __name__ == '__main__':
    application.run(debug=False)