import traceback
from flask import render_template, request, redirect, url_for
import logging.config
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import config.config as config
from sqlalchemy import Column, Integer, String, Float

logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the Flask application
app = Flask(__name__, template_folder="app/templates")

# Configure flask app
app.config.from_pyfile('config/flaskconfig.py')

# Initialize the database
db = SQLAlchemy(app)


class Rec(db.Model):
    """Create a data model for the database to be set up product recommendation predictions """

    __tablename__ = config.TABLE
    StockCode = Column(String(100), primary_key=True)
    Description = Column(String(100), unique=False, nullable=False)
    Price = Column(Float, unique=False, nullable=False)
    rec1 = Column(String(100), unique=False, nullable=False)
    conf1 = Column(Float, unique=False, nullable=False)
    Description_rec1 = Column(String(100), unique=False, nullable=False)
    Price_rec1 = Column(Float, unique=False, nullable=False)
    rec2 = Column(String(100), unique=False, nullable=False)
    conf2 = Column(Float, unique=False, nullable=False)
    Description_rec2 = Column(String(100), unique=False, nullable=False)
    Price_rec2 = Column(Float, unique=False, nullable=False)

    def __repr__(self):
        return "<Rec(Product_ID={}, Product_Name={})>".format(self.StockCode, self.Description)


@app.route("/")
@app.route("/home", methods=['GET', 'POST'])
def submitForm():
    """
    Get data from database for the webapp
    """
    try:
        rec = db.session.query(Rec)
        StockCode = request.form.get('prod')
        this_rec = Rec.query.filter_by(StockCode=StockCode).first()
        logger.debug("Successfully loaded data.")
        return render_template('index.html', recs=rec, this_rec=this_rec)
    except:
        traceback.print_exc()
        logger.warning("Not able to get recommendations, error page returned")
        return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=True, port=app.config["PORT"], host=app.config["HOST"])
