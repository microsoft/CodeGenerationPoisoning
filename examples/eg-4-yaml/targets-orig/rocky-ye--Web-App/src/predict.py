import pickle
import yaml
import os
import logging
import yaml
import pandas as pd
import numpy as np
import joblib
logging.basicConfig(format='%(name)-12s %(levelname)-8s %(message)s',
                    level=logging.INFO)

logger = logging.getLogger('generating_features')

def predicting(df):
    '''

    :param df: pandas dataframe; single row of observation to predict
    :return: float; one single prediction
    '''
    # Load yaml file
    with open("config/config.yaml", "r") as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
        logger.debug('config.yaml loaded.')

    # transform input
    enc = joblib.load(config['enc_path'])
    model = joblib.load(config['model_path'])
    cat_features = df[config['cat_features']]
    transformed = enc.transform(cat_features).toarray()
    logger.debug('transformed data: %s', transformed)

    # predict charge
    predicted = model.predict(np.concatenate((df[config['num_features']], transformed), axis=1))[0]
    logger.info('Prediction successful: predicted value: %s', predicted)

    return predicted

