from flask import Flask, render_template, request
import pandas as pd
import numpy as np

app = Flask(__name__)


def create_postgres_authdict(user, password, hostandport, dbname='', fname='SQLAuth.sql', save=True):
    """
    Creates a dictionary with PostGresSQL credentials and saves it as a pickled file containing a
    dictionary with credientials for later loading or creates a URL for immediate use.
    
    Parameters
    ----------
    user: str
        username for DataBase
    
    password: str

    hostandport: str
        Hostname and port for ex: 55.11.22.44:5432

    dbname: str, optinal
        Database name
        Default ''

    dir_path: Path object, optional
        Path to save the file. Default is pulled from config files.
        Default sql_db
    
    filename: str, optional
        Filename for the pickled file containing the dictionary.
        Defailt SQLAuth.sql

    save: bool, optional
        If save is true, dictionary is saved otherwise a url is returned.
        Defailt True
       
    Returns
    -------
    None
        if save is True
    Str
        PostgreSQL url to connect to a Database

    Raises
    ------
    IOError: If file cannot be saved.
        
    """

    import pickle

    sqldb_dict = {}
    sqldb_dict['username'] = user
    sqldb_dict['password'] = password
    sqldb_dict['host:port'] = hostandport
    sqldb_dict['dbname'] = dbname

    if save:
        try:
            pickle.dump(sqldb_dict, open(fname, 'wb'))
        except:
            raise IOError('ERROR: Could not save SQL credentials. Check path.')
    else:
        return create_posgresurl(sqldb_dict=sqldb_dict)


def create_posgresurl(fname='SQLAuth.sql', sqldb_dict=None):
    """
    Creates a PostGresSQL url that can be used to connect to a Database. 
    
    Parameters
    ----------
    sqldb_dict: dict, optional
        If None the function will load the SQL credentials pickled file. Otherwise SQL credentials can be
        explicitely provided using this parameter.
    
    dir_path: Path object, optional
        Path to SQL credentials pickled file. SQL credentials can be created using create_postgres_authdict()
        or explicitely provided. Default is pulled from config files.
        Unnecessary if sqldb_dict is provided.
        Default sql_db
      
    filename: str, optional
        Filename of the SQL credentials pickled file.
        Defailt SQLAuth.sql
       
    Returns
    -------
    Str
        PostgreSQL url to connect to a Database

    Raises
    ------
    IOError: If credentials file cannot be loaded.
        
    """

    import pickle

    if not sqldb_dict:
        try:
            sqldb_dict = pickle.load(open(fname, 'rb'))
        except:
            raise IOError('ERROR: Could not load SQL credentials. Check path.')
    return 'postgres://{}:{}@{}/{}'.format(sqldb_dict['username'], sqldb_dict['password'], sqldb_dict['host:port'],
                                           sqldb_dict['dbname'])


def sql_readaspd(db_dets, query):
    """
    Pull a SQL query output and read it into a Pandas DataFrame 
    
    Parameters
    ----------
    db_dets: str
        URL of a postgreSQL database that will be connected to.
    
    query: str
        SQL query
       
    Returns
    -------
    Pandas.DataFrame
        DataFrame containing output of the query
        
    """
    from sqlalchemy import create_engine
    from sqlalchemy.pool import NullPool

    engine = create_engine(db_dets, poolclass=NullPool)
    con_var = engine.connect()
    rs_var = con_var.execute(query)
    con_var.close
    df = pd.DataFrame(rs_var.fetchall(), columns=rs_var.keys())
    df.index = df['index']
    df = df.drop(['index'], axis=1)
    try:
        df = df.drop(['Unnamed: 0'], axis=1)
    except:
        pass
    return df


@app.route('/', methods=["GET", "POST"])
def hello_world():
    # Render homepage
    return render_template('Homepage.html')


@app.route('/preset', methods=["GET", "POST"])
def preset_output():
    # Get value of dropdown menu that the user chose
    game_titlehtml = request.args.get('demo_input')

    # Explicitely mention SQL url but not recommended
    sqlurl = 'postgres://user:pass@host/dbname'

    # Lambda functions for SQL queries
    game_query = lambda x: 'SELECT * FROM investigamepred WHERE "TitlesHTML" = \'{}\''.format(x)
    publisher_query = lambda x: 'SELECT * FROM investigamepred WHERE "Publishers" = \'{}\' LIMIT 4'.format(x)
    dev_query = lambda x: 'SELECT * FROM investigamepred WHERE "Developers" = \'{}\' LIMIT 4'.format(x)

    # Get game details of the game chosen by user
    game_info = sql_readaspd(create_posgresurl(), game_query(game_titlehtml))
    #    game_info = sql_readaspd(sqlurl,game_query(game_titlehtml))

    # Get a couple of games from the same publishers as the publlisher of the game chosen by the user.
    # This populates the related games section of the web app
    game_same_pubs = sql_readaspd(create_posgresurl(), publisher_query(game_info['Publishers'].values[0]))
    #    game_same_pubs = sql_readaspd(sqlurl,publisher_query(game_info['Publishers'].values[0]))

    # Remove the game chosen by the user from the list of related games
    try:
        game_same_pubs = game_same_pubs.drop(game_info.index, axis=0)
    except:
        pass

    template = """<div class="media-object stack-for-small">
            <div class="media-object-section">
              <img class="thumbnail" src="{}">
            </div>
            <div class="media-object-section">
              <h5>Game: {}</h5>
              <p>Publisher: {}</p>
              <p>Developer: {}</p>
              <p>Aggregate Review: {}</p>
              <p>Prediction: {}</p>
              <p>Confidence: {}%</p>
            </div>
          </div>"""

    pub_text = ''

    # Populate related games using above template and add it to the HTML file.
    # Slightly hacky way of including variable number of games in a single HTML file but cleaner than trying to force
    # Flask to do it using variables
    if game_same_pubs.empty:
        pub_text = '<p>No games with the same publishers found.</p>'
    else:
        for row_tuple in game_same_pubs.itertuples():
            pub_text_temp = template.format(row_tuple.GameCard, row_tuple.Titles,
                                            row_tuple.Publishers,
                                            row_tuple.Developers,
                                            row_tuple.Reviews,
                                            row_tuple.SuccessPredictText,
                                            np.around([row_tuple.SuccessPredictProb][0] * 100, decimals=2))
            pub_text = pub_text + pub_text_temp

    with open('templates/Gamepage.html') as file:
        html_file = file.read()
        html_file = html_file.replace('MAT115', pub_text)

    with open('templates/Gamepage2.html', mode='w') as file:
        file.write(html_file)

    del html_file

    # Same process as above but for game developers instead of publishers. Need to convert this into a function
    # according to the DRY rule.
    game_same_devs = sql_readaspd(create_posgresurl(), dev_query(game_info['Developers'].values[0]))
    #    game_same_devs = sql_readaspd(sqlurl,dev_query(game_info['Developers'].values[0]))

    try:
        game_same_devs = game_same_devs.drop(game_info.index, axis=0)
    except:
        pass

    pub_text = ''

    if game_same_devs.empty:
        pub_text = '<p> No games with the same developers found. </p>'
    else:
        for row_tuple in game_same_devs.itertuples():
            pub_text_temp = template.format(row_tuple.GameCard, row_tuple.Titles,
                                            row_tuple.Publishers,
                                            row_tuple.Developers,
                                            row_tuple.Reviews,
                                            row_tuple.SuccessPredictText,
                                            np.around([row_tuple.SuccessPredictProb][0] * 100, decimals=2))
            pub_text = pub_text + pub_text_temp

    with open('templates/Gamepage2.html') as file:
        html_file = file.read()
        html_file = html_file.replace('MAT215', pub_text)

    with open('templates/Gamepage3.html', mode='w') as file:
        file.write(html_file)

    # Render the game page with related games and predictions.
    return render_template('Gamepage3.html', game_name=str(game_info['Titles'].values[0]),
                           game_pub=str(game_info['Publishers'].values[0]),
                           game_dev=str(game_info['Developers'].values[0]),
                           game_rev=str(game_info['Reviews'].values[0]),
                           game_pred=str(game_info['SuccessPredictText'].values[0]),
                           game_pred_prob=str(game_info['SuccessPredictProb'].mul(100).round(2).values[0]),
                           game_url=str(game_info['GameCard'].values[0]))


@app.route('/nopage')
def nopage_output():
    # For sections of the website that do not currently work
    return render_template('Nopage.html')


@app.route('/aboutme')
def aboutme_output():
    # Need to be constructed.
    return render_template('Aboutme.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
#    app.run(debug=True) #will run locally http://127.0.0.1:5000/
