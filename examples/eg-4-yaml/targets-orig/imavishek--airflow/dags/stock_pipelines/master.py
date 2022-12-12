"""
pipeline master executer
========================
"""
from Dependencies.Taiyo_Pipeline import Logger, PublishPostgress, border_msg
from Dependencies.toGrafanaViz import (Cascade_Graph, ClassificationMatrix,
                                       ModelReliabilityV2,
                                       SimTable, bulkCardsUQ)


class App():
    def __init__(self, name, config_path,
                 log_level, RunTime,
                 log_path='master.log',  mode="file"):
        self.logger = Logger(log_level, log_path)
        self.RunTime = RunTime
        self.logger.info(
            border_msg("New Pipeline Started: {}".format(name))
            )
        self.config = config_path
        self.publisher1 = PublishPostgress(self.config)

    def FetchDataLayer(self):

        @self.logger.logFunction
        def AlphaVantageData():

            import pandas as pd
            from Taiyo_Harvesting.toAlphaVantage import StockData

            FPconfig = self.config["Fetch Data Layer"]["Alpha Vantage"]

            SDHandle = StockData(
                ticker=FPconfig["ticker"],
                frequency=FPconfig["frequency"]
            )
            SDdata = SDHandle.getStockPrices()
            SDdata.sort_values(by=['Date'], inplace=True)
            SDdata.set_index('Date', inplace=True)

            for c in SDdata.columns:
                SDdata[c] = pd.to_numeric(SDdata[c])

            return SDdata

        @self.logger.logFunction
        def FREDData():

            from Taiyo_Harvesting.toFredHarvester import FREDData

            FPconfig = self.config["Fetch Data Layer"]["Fred"]

            FREDHandle = FREDData(
                codes=FPconfig["codes"],
                start_date=FPconfig["start_date"]
                )

            FREDHandle.getData()
            FREDdata = FREDHandle.data.fillna(
                method='ffill').fillna(method='bfill')

            return FREDdata

        response = {}
        response['Alpha Vantage'] = AlphaVantageData()
        response['ohlcv'] = response['Alpha Vantage']
        while(True):
            response['Fred'] = FREDData()
            if(response['Fred'] is None):
                self.logger.info("Reattempting Fred")
                continue
            break
        return response

    def KnowledgeAbstractionLayer(self, response):

        @self.logger.logFunction
        def TechFeatures():

            from Taiyo_TechFeatures.toTechFeatures import TechIndicators
            KALconfig = \
                self.config["Knowledge Abstraction Layer"]['Tech Features']
            FXTI = TechIndicators(response['Alpha Vantage'])
            for func in KALconfig:
                getattr(FXTI, func["function"])(**func["params"])

            return FXTI.data

        @self.logger.logFunction
        def DataAggregation(data):

            KALconfig = \
                self.config["Knowledge Abstraction Layer"]["Data Aggregation"]

            target = self.config["Meta-Data"]["Target"]

            X = data.join(response["Fred"], how='left')
            X = X.rename(columns={target: target + "(t)"})
            X = X.dropna()

            for i in range(1, KALconfig['Lags']):
                X[target + "(t-" + str(i) + ")"] = X[target + "(t)"].shift(i)
            X.dropna(inplace=True)

            X[target + "(t+1)"] = X[target + "(t)"].shift(-1)
            return X

        TFdata = TechFeatures()
        Agg_Data = DataAggregation(TFdata)

        out_response = {}
        out_response["X"] = Agg_Data
        out_response["ohlcv"] = response["ohlcv"]
        return out_response

    def PreProcessingLayer(self, response):

        target = self.config["Meta-Data"]["Target"]
        PPLconfig = self.config['Pre-Processing Layer']

        @self.logger.logFunction
        def TargetGen():
            X = response['X'][target + '(t)']
            return X

        @self.logger.logFunction
        def Naive_Forecaster():
            X = response['X'][target + '(t)']
            X = X.rename(columns={target + '(t)': 'NF'})
            return X

        @self.logger.logFunction
        def ARIMA():
            split = PPLconfig['ARIMA']['split']
            X = response['X'][target + '(t)']
            X = X.rename(columns={target + '(t)': 'ARIMA'})
            train, test = X[X.index < split], X[X.index >= split]
            X = {}
            X["train"] = train
            X["test"] = test
            return X

        @self.logger.logFunction
        def Mov_Avg():
            days = PPLconfig['Mov_Avg']['days']
            X = response['X'][target + '(t)'].rolling(days).mean()
            X = X.rename(columns={target + '(t)': 'MA'})
            return X

        @self.logger.logFunction
        def MLP():
            from Taiyo_Data.toMLPPreProcessor import MLP_PP

            MLPHandle = MLP_PP(
                response['X'],
                input_features=response['X'].columns,
                target=target + "(t+1)")

            MLPHandle.compileData(**PPLconfig["MLP"])
            return MLPHandle

        @self.logger.logFunction
        def LSTM():
            from Taiyo_Data.toLSTMPreProcessor import Lstm_PP

            LSTMHandle = Lstm_PP(
                response['X'],
                input_features=response['X'].columns,
                target=target + "(t+1)")

            LSTMHandle.compileData(**PPLconfig["LSTM"])
            return LSTMHandle

        @self.logger.logFunction
        def GRU():
            from Taiyo_Data.toLSTMPreProcessor import Lstm_PP
            GRUHandle = Lstm_PP(
                response['X'],
                input_features=response['X'].columns,
                target=target + "(t+1)")

            GRUHandle.compileData(**PPLconfig["GRU"])
            return GRUHandle

        out_response = {}
        out_response["Target"] = TargetGen()
        out_response["NF"] = Naive_Forecaster()
        out_response["ARIMA"] = ARIMA()
        out_response["MA"] = Mov_Avg()
        out_response["MLP"] = MLP()
        out_response["LSTM"] = LSTM()
        out_response["GRU"] = GRU()
        return out_response

    def ModelTrainingLayer(self, response):

        MTLconfig = self.config['Model Training Layer']

        @self.logger.logFunction
        def Naive_Forecaster():
            return response['NF']

        @self.logger.logFunction
        def ARIMA():
            from statsmodels.tsa.arima_model import ARIMA

            train = response['ARIMA']['train']
            test = response['ARIMA']['test']
            history = [x for x in train]
            predictions = list()
            ar = MTLconfig["ARIMA"]["ar"]
            diff = MTLconfig["ARIMA"]["diff"]
            ma = MTLconfig["ARIMA"]["ma"]
            for t in range(len(train)):
                model = ARIMA(history, order=(ar, diff, ma))
                model_fit = model.fit(disp=0)
                output = model_fit.forecast()
                yhat = output[0][0]
                predictions.append(yhat)
                obs = train[t]
                history.append(obs)
            for t in range(len(test)):
                model = ARIMA(history, order=(ar, diff, ma))
                model_fit = model.fit(disp=0)
                output = model_fit.forecast()
                yhat = output[0][0]
                predictions.append(yhat)
                obs = test[t]
                history.append(obs)
            return predictions

        @self.logger.logFunction
        def Mov_Avg():
            return response['MA']

        @self.logger.logFunction
        def MLP():
            from Taiyo_Models.toNN import IndexerMLP
            try:
                MLP = IndexerMLP()
                MLP.loadModel(**MTLconfig["MLP"]["saved_model"])
            except Exception:
                MLP = IndexerMLP(**MTLconfig["MLP"]["model_params"])
                MLP.fitModel(
                    response["MLP"].X_train,
                    response["MLP"].y_train,
                    **MTLconfig["MLP"]["fit_params"])

                MLP.saveModel(**MTLconfig["MLP"]["saved_model"])

            return MLP

        @self.logger.logFunction
        def LSTM():
            from Taiyo_Models.toRNN import IndexerLSTM

            try:
                LSTM = IndexerLSTM()
                LSTM.loadModel(**MTLconfig["LSTM"]["saved_model"])
            except Exception:
                LSTM = IndexerLSTM(
                    response["LSTM"].X_train.shape[1],
                    response["LSTM"].X_train.shape[2],
                    **MTLconfig["LSTM"]["model_params"])

                LSTM.buildModel()
                LSTM.compileModel()
                LSTM.fitModel(
                    response["LSTM"].X_train,
                    response["LSTM"].y_train,
                    validation_data=(
                        response["LSTM"].X_val,
                        response["LSTM"].y_val,
                    ),
                    **MTLconfig["LSTM"]["fit_params"]
                    )

                LSTM.saveModel(**MTLconfig["LSTM"]["saved_model"])

            return LSTM

        @self.logger.logFunction
        def GRU():
            from Taiyo_Models.toRNN import IndexerGRU

            try:
                GRU = IndexerGRU()
                GRU.loadModel(**MTLconfig["GRU"]["saved_model"])
            except Exception:
                GRU = IndexerGRU(
                    response["GRU"].X_train.shape[1],
                    response["GRU"].X_train.shape[2],
                    **MTLconfig["GRU"]["model_params"])

                GRU.buildModel()
                GRU.compileModel()
                GRU.fitModel(
                    response["GRU"].X_train,
                    response["GRU"].y_train,
                    validation_data=(
                        response["GRU"].X_val,
                        response["GRU"].y_val,
                    ),
                    **MTLconfig["GRU"]["fit_params"]
                    )

                GRU.saveModel(**MTLconfig["GRU"]["saved_model"])

            return GRU

        NF, AA, MA, MLP, LSTM, GRU = \
            Naive_Forecaster(), ARIMA(), Mov_Avg(), MLP(), LSTM(), GRU()

        @self.logger.logFunction
        def Inference(NF, AA, MA, MLP, LSTM, GRU):
            import pandas as pd
            import numpy as np

            MLP = response["MLP"].transform_output(
                MLP.predict(response["MLP"].X))
            LSTM = response["LSTM"].transform_output(
                LSTM.predict(response["LSTM"].X))
            GRU = response["GRU"].transform_output(
                GRU.predict(response["GRU"].X))

            def adjuster(values):
                ept = [np.nan for _ in range(len(NF.index))]
                balance = len(NF.index) - len(values)
                ept[balance:] = values.ravel()
                return ept

            inference = pd.DataFrame(index=NF.index)
            inference = inference.join(response["Target"], how='left')

            inference["NF"] = NF.values
            inference["ARIMA"] = AA
            inference["MA"] = MA.values
            inference["MLP"] = adjuster(MLP)
            inference["LSTM"] = adjuster(LSTM)
            inference["GRU"] = adjuster(GRU)

            return inference
        out_response = {}
        out_response["inference"] = Inference(NF, AA, MA, MLP, LSTM, GRU)
        return out_response

    def PostProcessingLayer(self, response):

        PPLconfig = self.config["Meta-Data"]

        @self.logger.logFunction
        def timestepfunction(datetimeIndex=response["inference"].index):
            import pandas as pd
            from datetime import datetime, timedelta

            hour, minute = \
                (PPLconfig[PPLconfig["Target"] + " Time"]).split(":")
            hour, minute = int(hour), int(minute)

            if(PPLconfig["Frequency"] == "Daily"):
                next_date = datetimeIndex[-1]
                if(next_date.weekday() == 4):
                    next_date += timedelta(days=3)
                else:
                    next_date += timedelta(days=1)
                next_date = next_date.replace(hour=hour, minute=minute)
                datetimeIndex = datetimeIndex.append(
                    pd.to_datetime([next_date]))

            elif(PPLconfig["Frequency"] == "Weekly"):

                next_week = datetimeIndex[-1]
                start = next_week - timedelta(days=next_week.weekday())
                end = start + timedelta(days=4)
                if(datetimeIndex[-1] == next_week):
                    next_week = end + timedelta(days=7)
                else:
                    next_week = end
                next_week = next_week.replace(hour=hour, minute=minute)
                datetimeIndex = datetimeIndex.append(
                    pd.to_datetime([next_week]))

            elif(PPLconfig["Frequency"] == "Monthly"):
                def get_first_day(dt, d_years=0, d_months=0):
                    # d_years, d_months are "deltas" to apply to dt
                    y, m = dt.year + d_years, dt.month + d_months
                    a, m = divmod(m-1, 12)
                    return datetime(y+a, m+1, 1)

                def get_last_day(dt):
                    return get_first_day(dt, 0, 1) + timedelta(-1)

                next_month = datetimeIndex[-1] + timedelta(days=1)
                next_month = get_last_day(next_month)
                next_month = next_month.replace(hour=hour, minute=minute)
                datetimeIndex = datetimeIndex.append(
                    pd.to_datetime([next_month]))

            return datetimeIndex

        @self.logger.logFunction
        def ResultsGen():
            import pandas as pd

            results = pd.DataFrame(index=timestepfunction())
            results = results.join(response["inference"], how="left")

            results["NF"] = results["NF"].shift(1)
            results["ARIMA"] = results["ARIMA"].shift(1)
            results["MA"] = results["MA"].shift(1)
            results["MLP"] = results["MLP"].shift(1)
            results["LSTM"] = results["LSTM"].shift(1)
            results["GRU"] = results["GRU"].shift(1)

            return results

        @self.logger.logFunction
        def UncertainityBounds():
            import pandas as pd

            UQBounds_df = pd.DataFrame(index=timestepfunction())
            UQBounds_df.index.name = "Timestamp"

            UQBounds_df['NF_H'] = [0 for i in range(len(UQBounds_df))]
            UQBounds_df['NF_L'] = [0 for i in range(len(UQBounds_df))]

            UQBounds_df['ARIMA_H'] = [0 for i in range(len(UQBounds_df))]
            UQBounds_df['ARIMA_L'] = [0 for i in range(len(UQBounds_df))]

            UQBounds_df['MA_H'] = [0 for i in range(len(UQBounds_df))]
            UQBounds_df['MA_L'] = [0 for i in range(len(UQBounds_df))]

            UQBounds_df['MLP_H'] = [0 for i in range(len(UQBounds_df))]
            UQBounds_df['MLP_L'] = [0 for i in range(len(UQBounds_df))]

            UQBounds_df['LSTM_H'] = [0 for i in range(len(UQBounds_df))]
            UQBounds_df['LSTM_L'] = [0 for i in range(len(UQBounds_df))]

            UQBounds_df['GRU_H'] = [0 for i in range(len(UQBounds_df))]
            UQBounds_df['GRU_L'] = [0 for i in range(len(UQBounds_df))]

            return UQBounds_df

        results = ResultsGen()
        UQ = UncertainityBounds()
        out_response = {}
        out_response["results"] = results
        out_response["UQ"] = UQ
        return out_response

    def VisualizationLayer(self, response):
        """Layer for generating Visualizations data into json dumps

        Args:
            response (dict): response contains the
            json data from the previous layer

        Returns:
            dict: Response to send to the Publish Layer
        """

        VLconfig = self.config["Meta-Data"]
        results = response["results"]
        UQ = response["UQ"]
        @self.logger.logFunction
        def TradeCards():
            TCs = bulkCardsUQ(
                notebook_name=VLconfig["Name"],
                frequency=VLconfig["Frequency"],
                target=VLconfig["Target"] + "(t)",
                run_time=self.RunTime
            )
            TC = TCs.bulkBuild(results, UQ, 95)
            return TC

        @self.logger.logFunction
        def MTS():
            plot_TS = Cascade_Graph(results, target=VLconfig["Target"] + "(t)")
            MTS = plot_TS.bulkBuild(
                notebook_name=VLconfig["Name"],
                frequency=VLconfig["Frequency"],
                run_time=self.RunTime
                )

            return MTS

        @self.logger.logFunction
        def MRM():
            mrm = ModelReliabilityV2(
                results.dropna(), target=VLconfig["Target"] + "(t)")
            MRM = mrm.bulkBuild(
                    notebook_name=VLconfig["Name"],
                    frequency=VLconfig["Frequency"],
                    run_time=self.RunTime
                    )
            return MRM

        @self.logger.logFunction
        def SimTables():
            ST1 = SimTable(results.dropna(), target=VLconfig["Target"] + "(t)")
            change_table, color_list = ST1.changeTable(4, 500)
            ST1.directionTable()

            ST, DT = ST1.bulkBuild(
                    notebook_name=VLconfig["Name"],
                    frequency=VLconfig["Frequency"],
                    run_time=self.RunTime
                )

            import pandas as pd
            clf_rep = pd.DataFrame(color_list)
            clf_rep = clf_rep.applymap(
                lambda x: "Up" if x == "#00FF00" else "Down")

            CM = ClassificationMatrix(
                clf_rep, target=VLconfig["Target"] + "(t) Change",
                dump_target=VLconfig["Target"] + "(t)")
            CM.report(drop_cols=[VLconfig["Target"] + "(t) Change"])
            CM = CM.bulkBuild(
                    notebook_name=VLconfig["Name"],
                    frequency=VLconfig["Frequency"],
                    run_time=self.RunTime
                )

            return ST, DT, CM

        response = {}
        response["TradeCards"] = TradeCards()
        response["MTS"] = MTS()
        response["MRM"] = MRM()
        response["Simtable"], response["Dirtable"], response["Class_M"] = \
            SimTables()
        return response

    def PublishLayer(self, response):
        """Layer for publishing data using the reponse from previous layer json dumps

        Args:
            response (dict): response contains the
                             json data from the previous layer

        Returns:
            dict: Response to receive about the upload
        """
        data = response
        @self.logger.logFunction
        def PublishPostgress():
            response = {}
            response["TradeCards"] = self.publisher1.publish_tradecards(
                data["TradeCards"], table="TradeCards")
            response["MTS"] = self.publisher1.publish_MTS(
                data["MTS"], table="TimeSeries")
            response["MRM"] = self.publisher1.publish_MRM(
                data["MRM"], table="MRM")
            response["Simtable"] = self.publisher1.publish_Simtable(
                data["Simtable"], table="Simtable")
            response["Dirtable"] = self.publisher1.publish_DIRtable(
                data["Dirtable"], table="Dirtable")
            response["Class_M"] = \
                self.publisher1.publish_classification_matrices(
                    data["Class_M"], table="Class_M")
            return response

        return PublishPostgress()

    def run(self):

        @self.logger.logLayer('Fetch Data Layer')
        def FetchDataLayer():
            return self.FetchDataLayer()

        @self.logger.logLayer('Knowledge Abstraction Layer')
        def KnowledgeAbstractionLayer(response):
            return self.KnowledgeAbstractionLayer(response)

        @self.logger.logLayer('Pre-Processing Layer')
        def PreProcessingLayer(response):
            return self.PreProcessingLayer(response)

        @self.logger.logLayer('Model Training Layer')
        def ModelTrainingLayer(response):
            return self.ModelTrainingLayer(response)

        @self.logger.logLayer('Post-Processing Layer')
        def PostProcessingLayer(response):
            return self.PostProcessingLayer(response)

        @self.logger.logLayer('Visualization Layer')
        def VisualizationLayer(response):
            return self.VisualizationLayer(response)

        @self.logger.logLayer('Publish Layer')
        def PublishLayer(response):
            return self.PublishLayer(response)

        response = FetchDataLayer()
        response = KnowledgeAbstractionLayer(response)
        response = PreProcessingLayer(response)
        response = ModelTrainingLayer(response)
        response = PostProcessingLayer(response)
        response = VisualizationLayer(response)
        response = PublishLayer(response)
        self.logger.info(response)


def batch_mode(args):
    import glob
    for _file in glob.glob(args.config_path + "/*.yml"):
        print("running file ", _file)
        with open(_file, 'r') as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)
            try:
                os.mkdir(
                    'Models/' + config["Meta-Data"]["Name"].split(
                        ' (')[0].replace(' ', '_').replace('.', ''))
            except Exception:
                print("Folder already present")
            name = config["Meta-Data"]["Name"]
            target = config["Meta-Data"]["Target"]
            frequency = config["Meta-Data"]["Frequency"]
            name = name + ' ' + target + ' ' + frequency
            App1 = App(
                name=name,
                config_path=config,
                log_level='INFO',
                RunTime=args.runtime,
                log_path=args.log_path
            )
            App1.run()


def single_mode(args):
    with open(args.config_path, 'r') as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
        try:
            os.mkdir(
                'Models/' + config["Meta-Data"]["Name"].split(
                    ' (')[0].replace(' ', '_').replace('.', ''))
        except Exception:
            print("Folder already present")
        name = config["Meta-Data"]["Name"]
        target = config["Meta-Data"]["Target"]
        frequency = config["Meta-Data"]["Frequency"]
        name = name + ' ' + target + ' ' + frequency
        App1 = App(
            name=name,
            config_path=config,
            log_level='INFO',
            RunTime=args.runtime,
            log_path=args.log_path
        )
        App1.run()


if __name__ == "__main__":
    import argparse
    import os
    import yaml
    parser = argparse.ArgumentParser(description='Execute a dashboard job')
    parser.add_argument('--mode',
                        help='Name of the pipeline',
                        default="single_mode")
    parser.add_argument('--name', help='Name of the pipeline')
    parser.add_argument('--config_path', help='path to the configuration file')
    parser.add_argument('--runtime', help='runtime of the config file')
    parser.add_argument('--log_path', default=None,
                        help='path to store execution logs of the pipeline')
    args = parser.parse_args()
    if(args.mode == "batch_mode"):
        print("executing in", args.mode)
        batch_mode(args)
    if(args.mode == "single_mode"):
        single_mode(args)
