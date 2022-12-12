import os
import json
import yaml
import logging
import datetime
from airflow import DAG, AirflowException
from airflow.operators.python_operator import PythonOperator
from Taiyo_Harvesting.toAlphaVantage import StockData


logger = logging.getLogger(__name__)

try:
    logger.info('Reading config file...')
    with open(os.path.join(os.path.dirname(__file__), 'Ansys.yml'), 'r') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        logger.info('Successful in reading config file.')
except Exception as e:
    config = None
    logger.error('Error reading config file. Error: {}'.format(e))
    raise AirflowException("Following exception occurred while reading config file: {}".format(e))

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.datetime.today() - datetime.timedelta(days=1),
}

run_time = '{{ ts }}'

def AlphaVantageData(**kwargs):
    global config
    FPconfig = config["Fetch Data Layer"]["Alpha Vantage"]
    SDHandle = StockData(ticker=FPconfig["ticker"], frequency=FPconfig["frequency"])
    SDdata = SDHandle.getStockPrices()
    SDdata.sort_values(by=['Date'], inplace=True)
    SDdata.set_index('Date', inplace=True)
    for c in SDdata.columns:
        SDdata[c] = pd.to_numeric(SDdata[c])
    kwargs['ti'].xcom_push(key='AlphaVantage', value=SDdata)

with DAG('airflow-pipeline', default_args=default_args, schedule_interval=datetime.timedelta(days=1)) as dag:
    task2 = PythonOperator( task_id='AlphaVantage', 
                            python_callable=AlphaVantageData, 
                            provide_context=True )
