import sys
import ccxt
import oyaml as yaml
import os
import re
from datetime import datetime
import pytz
import time
# Import base class
from .basic import Basic
# Import enrichments
from aitblib import enrichments
# Dataframes
import pandas as pd
# Parser for is_date
from dateutil.parser import parse


class Helper(Basic):

    def test(self):
        print('########################', file=sys.stderr)
        print('Testing Helper Class', file=sys.stderr)
        print('########################', file=sys.stderr)

    def createCryptoCon(self, ex):
        # Create temp Exchange
        ex_class = getattr(ccxt, ex)
        tmpex = ex_class()
        markets = tmpex.load_markets()
        # Fees and Quotes
        feesdict = {}
        quotes = []
        fees = []
        # Itterate through crypto markets
        for symb in markets:
            if markets[symb]['taker']:
                feesdict.update({str(symb): markets[symb]['taker']})
                fees.append(markets[symb]['taker'])
            quotes.append(markets[symb]['quote'])
        # Mode fees
        from statistics import mode
        tmpfeesmode = mode(fees)
        # Find unique quotes and join them
        tmpquotes = ', '.join(set(quotes))
        # Fees creations
        tmpfees = {'fees': feesdict}
        # Join time frames
        try:
            tmptf = ', '.join(tmpex.timeframes.keys())
        except BaseException:
            tmptf = 'N/A'
        # Check for multiple countries
        try:
            tmpco = ', '.join(tmpex.countries)
        except BaseException:
            tmpco = 'N/A'
        # Check pairs and symbols
        tmppairs = ', '.join(tmpex.symbols)
        # Make abilities sub
        abilities = {'abilities': tmpex.has}
        # Create Connection YAML
        conYML = 'id: ' + tmpex.id + "\n"
        conYML = conYML + 'name: ' + tmpex.name + "\n"
        conYML = conYML + 'type: CryptoCurrency' + "\n"
        conYML = conYML + 'certified: ' + str(tmpex.certified).lower() + "\n"
        conYML = conYML + 'timeframes: ' + tmptf + "\n"
        conYML = conYML + 'timeout: ' + str(tmpex.timeout) + "\n"
        conYML = conYML + 'ratelimit: ' + str(tmpex.rateLimit) + "\n"
        conYML = conYML + 'countries: ' + tmpco + "\n"
        conYML = conYML + 'quotes: ' + tmpquotes + "\n"
        conYML = conYML + 'pairs: ' + tmppairs + "\n"
        conYML = conYML + 'totpairs: ' + str(len(tmpex.symbols)) + "\n"
        conYML = conYML + 'modefees: ' + str(tmpfeesmode) + "\n"
        conYML = conYML + yaml.dump(tmpex.urls, default_flow_style=False, sort_keys=False) + "\n"
        conYML = conYML + yaml.dump(abilities, default_flow_style=False, sort_keys=False) + "\n"
        conYML = conYML + yaml.dump(tmpfees, default_flow_style=False, sort_keys=False) + "\n"
        # Remove empty lines
        conYML = os.linesep.join([s for s in conYML.splitlines() if s])
        # Save to YAML file
        self.writeRawCfgFile('conn', ex, conYML)

    def createCryptoInfo(self, ex):
        ex_class = getattr(ccxt, ex)
        tmpex = ex_class()
        # Map out variables
        tmpwww = tmpex.urls['www']
        tmpnom = tmpex.name
        tmpcert = str(tmpex.certified)
        # Check for duplicate urls
        if type(tmpwww) is list:
            tmpwww = str(tmpex.urls['www'][0])
        tmpapi = tmpex.urls['api']
        # Check fees
        try:
            tmpfees = tmpex.urls['fees']
            if type(tmpfees) is list:
                tmpfees = str(tmpex.urls['fees'][0])
        except BaseException:
            tmpfees = 'N/A'
        # Check for tmpapi being a dick!
        if type(tmpapi) is dict:
            try:
                tmpapi = tmpex.urls['api']['public']
            except BaseException:
                tmpapi = 'N/A'
        # Check for multiple countries
        try:
            tmpco = ', '.join(tmpex.countries)
        except BaseException:
            tmpco = 'N/A'
        # Join time frames
        try:
            tmptf = ', '.join(tmpex.timeframes.keys())
        except BaseException:
            tmptf = 'N/A'
        tmpto = str(tmpex.timeout)
        tmprl = str(tmpex.rateLimit)
        tmpat = ""
        # Cycle through HAS array
        for key in tmpex.has:
            if tmpex.has[key] or tmpex.has[key] == 'emulated':
                tmpat = tmpat + key + ', '
        # Create passback HTML to Javascript from Select OnChange
        infostr = "<b>Name:</b> " + tmpnom + "<br><b>Country:</b> " + tmpco + "<br>"
        infostr = infostr + "<b>CCXT Certified:</b> " + tmpcert + "<br>"
        infostr = infostr + "<b>URL:</b> <a href='" + tmpwww + "'>" + tmpwww + "</a><br>"
        infostr = infostr + "<b>Fees:</b> <a href='" + tmpfees + "'>" + tmpfees + "</a><br>"
        infostr = infostr + "<b>API:</b> <a href='" + tmpapi + "'>" + tmpapi + "</a><br>"
        infostr = infostr + "<b>TimeFrames:</b> " + tmptf + "<br>"
        infostr = infostr + "<b>Timeout:</b> " + tmpto + "<br>"
        infostr = infostr + "<b>RateLimit:</b> " + tmprl + "<br>"
        infostr = infostr + "<b>Abilities:</b> " + tmpat + "<br>"
        return infostr

    def gitCryptoQuotes(self, con):
        # Get YAML connection configuration from file
        cfdata = self.readCfgFile('conn', con + '.yml')
        # Get quotes from file
        # print(cfdata)
        quotes = cfdata['quotes'].split(', ')
        # Create response in HTML
        quotesRESP = "<option value='NANANANA'>Select " + con + " quote</option>"
        for quote in quotes:
            quotesRESP = quotesRESP + "<option value='" + quote + "'>" + quote + "</option>"
        return quotesRESP

    def gitCryptoPairs(self, con, quote):
        # Get YAML connection configuration from file
        cfdata = self.readCfgFile('conn', con + '.yml')
        # Extract pairs from pairs setting
        pairs = cfdata['pairs'].split(', ')
        # Create response in HTML
        pairsRESP = "<option value='NANANANA'>Select " + quote + " Pairs</option>"
        for pair in pairs:
            part = pair.split('/')
            if part[1] == quote:
                pairsRESP = pairsRESP + "<option value='" + pair + "'>" + pair + "</option>"
        return pairsRESP

    def createCryptoData(self, con, quote, symb, start):
        # Start time to UnixTimestamp in UTC
        format = '%A %d %B %Y'
        d = datetime.strptime(start, format)  # 3.2+
        d = pytz.utc.localize(d)
        start = time.mktime(d.timetuple())
        start = int(start * 1000)
        # Create temp Exchange
        ex_class = getattr(ccxt, con)
        tmpex = ex_class()
        # Interogate OHLCV
        tmpfirst = ''
        tmpmaxbars = ''
        if tmpex.has['fetchOHLCV']:
            data = tmpex.fetch_ohlcv(symb, '1m')
            tmpfirst = data[0][0]
            tmpmaxbars = len(data)
        # Create Data ID
        fsymb = re.sub('/', '_', symb)
        id = con.lower() + '_' + fsymb
        dataYML = "id: " + id + "\n"
        # Create Database table class
        table_creation_sql = 'CREATE TABLE ' + id + ' (Date BIGINT NOT NULL, Open FLOAT, High FLOAT, Low FLOAT, Close FLOAT, Volume FLOAT, PRIMARY KEY(Date))'
        table_creation_sql = table_creation_sql.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
        # Create SQL table
        self.db.session.execute(table_creation_sql)
        # Create Data YAML
        dataYML = dataYML + 'enabled: false' + "\n"
        dataYML = dataYML + 'aggro: true' + "\n"
        dataYML = dataYML + 'con: ' + con + "\n"
        dataYML = dataYML + 'symb: ' + symb + "\n"
        dataYML = dataYML + 'first: ' + str(tmpfirst) + "\n"
        dataYML = dataYML + 'start: ' + str(start) + "\n"
        dataYML = dataYML + 'end: 0' + "\n"
        dataYML = dataYML + 'head: 0' + "\n"
        dataYML = dataYML + 'tail: 0' + "\n"
        dataYML = dataYML + 'count: 0' + "\n"
        dataYML = dataYML + 'maxbars: ' + str(tmpmaxbars) + "\n"
        dataYML = os.linesep.join([s for s in dataYML.splitlines() if s])
        # Save to YAML file
        self.writeRawCfgFile('data', id, dataYML)

    # def gitRunners(self):
        # print("last modified: %s" % time.ctime(os.path.getmtime(file)))
        # print("created: %s" % time.ctime(os.path.getctime(file)))

    def getFrom(self, period):
        monthInMS = 43800 * 60 * 1000
        todate = time.time() * 1000
        if period == '1M':
            fromdate = todate - monthInMS
        if period == '3M':
            fromdate = todate - 3 * monthInMS
        if period == '6M':
            fromdate = todate - 6 * monthInMS
        if period == '1Y':
            fromdate = todate - 12 * monthInMS
        if period == '2Y':
            fromdate = todate - 24 * monthInMS
        if period == '5Y':
            fromdate = todate - 60 * monthInMS
        return fromdate

    def createSample(self, data, fromdate, todate, timeframe, period):
        if period != 'custom':
            todate = time.time() * 1000
            fromdate = self.getFrom(period)
        else:
            # From date in UnixTimestamp in UTC
            format = '%A %d %B %Y'
            d = datetime.strptime(fromdate, format)  # 3.2+
            d = pytz.utc.localize(d)
            fromdate = time.mktime(d.timetuple())
            fromdate = int(fromdate * 1000)
            # To Date in UnixTimestamp in UTC
            format = '%A %d %B %Y'
            d = datetime.strptime(todate, format)  # 3.2+
            d = pytz.utc.localize(d)
            todate = time.mktime(d.timetuple())
            todate = int(todate * 1000)
        selState = 'SELECT * FROM ' + data + ' WHERE date BETWEEN ' + str(fromdate) + ' AND ' + str(todate)
        result = self.db.session.execute(selState).fetchall()
        createSampledf = pd.DataFrame(result, columns=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        if createSampledf.shape[0] == 0:
            return
        # Setup Datetime and Index
        # createSampledf['Date'].astype('datetime64[ms]')
        # TODO EXCLUDE forming Candle
        # Create filename
        sname = str(data) + '_' + timeframe + '_' + str(int(createSampledf['Date'].iloc[0])) + '_' + str(int(createSampledf['Date'].iloc[-1]))
        # Create DatetimeIndex
        createSampledf['Date'] = pd.to_datetime(createSampledf['Date'], unit='ms')
        createSampledf.set_index('Date', inplace=True)
        # Break up OHLC
        Open = createSampledf['Open']
        High = createSampledf['High']
        Low = createSampledf['Low']
        Close = createSampledf['Close']
        Vols = createSampledf['Volume']
        # Resample prices and vols
        sOpen = Open.resample(timeframe).first()
        sHigh = High.resample(timeframe).max()
        sLow = Low.resample(timeframe).min()
        sClose = Close.resample(timeframe).last()
        sVols = Vols.resample(timeframe).sum()
        # Join the two together
        result = pd.concat([sOpen, sHigh, sLow, sClose, sVols], axis=1)
        # Drop any NaN row
        result.dropna(inplace=True)
        # Save file to pickle
        result.to_pickle(self.sampleDataPath + sname + '.pkl')
        return sname

    def createNugget(self, sample, indie, depen, nana):
        en = enrichments.Enrichment()
        df = pd.read_pickle(self.sampleDataPath + sample + '.pkl')
        if indie != 'NotUsed':
            if isinstance(indie, list):
                riches = indie
            else:
                richcfg = self.readCfgFile('enrich', indie + '.yml')
                riches = richcfg['riches'].split(', ')
            for rich in riches:
                df = en.addIndi(rich, df)
        df = en.addDepen(depen, df)
        df = en.doNaN(nana, df)
        if isinstance(indie, list):
            import random
            n = random.randint(0, 1000)
            indie = 'temp' + str(n)
        nname = sample + '_' + indie + '_' + depen
        df.to_pickle(self.nuggetDataPath + nname + '.pkl')
        return nname

    def is_date(string, fuzzy=True):
        """
        Return whether the string can be interpreted as a date.

        :param string: str, string to check for date
        :param fuzzy: bool, ignore unknown tokens in string if True
        """
        try:
            parse(string, fuzzy=fuzzy)
            return True

        except ValueError:
            return False

    def createANN(self, nugget, nom, testsplit, scaler, scarcity, inputlayerunits, hiddenlayers, hiddenlayerunits, optimizer, loss, metrics, batchsize, epoch):
        # Create ANN YAML
        id = nom.lower()
        annYML = 'id: ' + id + "\n"
        annYML = annYML + 'name: ' + nom + "\n"
        annYML = annYML + 'nugget: ' + nugget + "\n"
        annYML = annYML + 'training: True' + "\n"
        annYML = annYML + 'scaler: ' + scaler + "\n"
        # print(scarcity,file=sys.stderr)
        if scarcity == "on":
            annYML = annYML + 'scarcity: True' + "\n"
        else:
            annYML = annYML + 'scarcity: False' + "\n"
        annYML = annYML + 'testsplit: ' + testsplit + "\n"
        # ANN Layers
        annYML = annYML + 'inputlayerunits: ' + inputlayerunits + "\n"
        annYML = annYML + 'hiddenlayers: ' + hiddenlayers + "\n"
        annYML = annYML + 'hiddenlayerunits: ' + hiddenlayerunits + "\n"
        # Fitting
        annYML = annYML + 'optimizer: ' + optimizer + "\n"
        annYML = annYML + 'loss: ' + loss + "\n"
        annYML = annYML + 'metrics: ' + metrics + "\n"
        annYML = annYML + 'batchsize: ' + batchsize + "\n"
        annYML = annYML + 'epoch: ' + epoch + "\n"
        # Training
        annYML = annYML + 'lasttrain: 0' + "\n"
        annYML = annYML + 'trainaccuracy: 0' + "\n"
        annYML = annYML + 'testaccuracy: 0' + "\n"
        # Add Nugget Info
        nfile = self.nuggetDataPath + nugget + '.pkl'
        # df = pd.read_feather(nfile)
        info = self.nugInfo(nfile)
        # Add info from nuggetinfo and enrichments
        annYML = annYML + 'symb: ' + info['symb'] + "\n"
        annYML = annYML + 'timeframe: ' + info['timeframe'] + "\n"
        annYML = annYML + 'from: ' + str(info['from']) + "\n"
        annYML = annYML + 'to: ' + str(info['to']) + "\n"
        annYML = annYML + 'depen: ' + info['depen'] + "\n"
        # indis = list(df.columns[0].values.tolist())
        with open(self.enConfPath + info['indi'] + '.yml', 'r') as afile:
            indi = yaml.full_load(afile)
        # print(indi['riches'],file=sys.stderr)
        annYML = annYML + 'indi: ' + indi['riches'] + "\n"
        # Delete empty lines
        annYML = os.linesep.join([s for s in annYML.splitlines() if s])
        # Save to YAML file
        self.writeRawCfgFile('aiann', id, annYML)

    def turnANNon(self, id):
        adata = self.readCfgFile('aiann', id + '.yml')
        adata['training'] = True
        # YAML and write to file
        self.writeCfgFile('aiann', id, adata)

    def removekey(self, d, key):
        r = dict(d)
        del r[key]
        return r

    def createRSSFeed(self, rdata):
        # Create ID
        id = rdata['name'].replace(' ', '_').lower()
        rdata['id'] = id
        rdata = self.removekey(rdata, 'action')
        # YAML and write to file
        self.writeCfgFile('sentrss', id, rdata)
        # self.ll(rdata)

    def createGoogleTrend(self, gdata):
        # Create ID
        id = gdata['keyword'].replace(' ', '_').lower() + '_' + gdata['period'] + '_' + gdata['cat']
        gdata['id'] = id
        gdata = self.removekey(gdata, 'action')
        # YAML and write to file
        self.writeCfgFile('senttrend', id, gdata)
        # self.ll(gdata)

    def createTwitterFeed(self, tdata):
        # Create ID
        id = tdata['name'].replace(' ', '_').lower()
        tdata = self.removekey(tdata, 'action')
        tdata['id'] = id
        # YAML and write to file
        self.writeCfgFile('senttwit', id, tdata)
        self.ll(tdata)

    def createBacktest(self, bdata):
        # Create ID
        id = bdata['name'].replace(' ', '_').lower()
        bdata['id'] = id
        # Time
        bdata['from'] = self.getFrom(bdata['period'])
        bdata['to'] = time.time() * 1000
        # Create sample
        sname = self.createSample(bdata['symb'], bdata['from'], bdata['to'], bdata['timeframe'], bdata['period'])
        # Create Native Nugget from Native Enrichment name
        natnug = self.createNugget(sname, bdata['native'], 'Dummy', 'drop')
        # Copy native nugget to backtest dir
        os.replace(self.nuggetDataPath + natnug + '.pkl', self.btDataPath + id + '_native.pkl')
        # Create Backtest Python
        if 'basic1ai' in bdata['type']:
            # Read in the template
            with open(self.btplDataPath + bdata['type'] + '.py', 'r') as file:
                fdata = file.read()
            # Make template only changes
            fdata = fdata.replace('XXXTAKEPROFITXXX', bdata['tp'])
            # Turn off exit
            bdata['exitai'] = 'NotUsed'
        if bdata['type'] == 'basic2ai':
            # Read in the template
            with open(self.btplDataPath + 'basic2ai.py', 'r') as file:
                fdata = file.read()
            # Make template only changes
            fdata = fdata.replace('XXXEXDFXXX', re.escape(self.btDataPath + id + '_exit') + '.pkl')
            # Models
            fdata = fdata.replace('XXXEXMODELXXX', re.escape(self.annDataPath + bdata['exitai']) + '.tf')
            fdata = fdata.replace('XXXEXSCLRXXX', re.escape(self.annDataPath + bdata['exitai']) + '.pkl')
        if 'trailing' in bdata['type']:
            # Read in the template
            with open(self.btplDataPath + bdata['type'] + '.py', 'r') as file:
                fdata = file.read()
            # Make template only changes
            fdata = fdata.replace('XXXTATRXXX', bdata['tatr'])
            fdata = fdata.replace('XXXTSLXXX', bdata['tsl'])
            # Turn off exit
            bdata['exitai'] = 'NotUsed'
        # Replace the target string
        fdata = fdata.replace('XXXNAMEXXX', bdata['id'])
        fdata = fdata.replace('XXXCASHXXX', bdata['cash'])
        fdata = fdata.replace('XXXCOMMXXX', bdata['commission'])
        fdata = fdata.replace('XXXMARGINXXX', bdata['margin'])
        # TP & SL
        fdata = fdata.replace('XXXSTOPLOSSXXX', bdata['sl'])
        # DFs
        fdata = fdata.replace('XXXNATDFXXX', re.escape(self.btDataPath + id + '_native') + '.pkl')
        fdata = fdata.replace('XXXENDFXXX', re.escape(self.btDataPath + id + '_entry') + '.pkl')
        # Models
        fdata = fdata.replace('XXXENTMODELXXX', re.escape(self.annDataPath + bdata['entryai']) + '.tf')
        fdata = fdata.replace('XXXENTSCLRXXX', re.escape(self.annDataPath + bdata['entryai']) + '.pkl')
        # Results
        fdata = fdata.replace('XXXRESULTXXXX', re.escape(self.btDataPath + id + '_results') + '.csv')
        # Write the file out again
        with open(self.btDataPath + id + '.py', 'w') as file:
            file.write(fdata)
        # Entry AI
        if bdata['entryai'] != 'NotUsed':
            # Get enrichment list from conf file for specific AI
            tmpai = self.readCfgFile('aiann', bdata['entryai'] + '.yml')
            # Create list from config comma seperated
            riches = tmpai['indi'].split(', ')
            # Create nugget with list
            entrynug = self.createNugget(sname, riches, 'Dummy', 'drop')
            # Copy entry nugget to backtest dir
            os.replace(self.nuggetDataPath + entrynug + '.pkl', self.btDataPath + id + '_entry.pkl')
        # Exit AI
        if bdata['exitai'] != 'NotUsed':
            # Get enrichment list from conf file for specific AI
            tmpai = self.readCfgFile('aiann', bdata['exitai'] + '.yml')
            # Create list from config comma seperated
            riches = tmpai['indi'].split(', ')
            # Create nugget with list
            exitnug = self.createNugget(sname, riches, 'Dummy', 'drop')
            # Copy entry nugget to backtest dir
            os.replace(self.nuggetDataPath + exitnug + '.pkl', self.btDataPath + id + '_exit.pkl')
        # Final settings
        bdata.pop('action', None)
        bdata['run'] = True
        # YAML and write to file
        self.writeCfgFile('bt', id, bdata)
        # Remove sample file
        os.remove(self.sampleDataPath + sname + '.pkl')

    def turnBTon(self, id):
        adata = self.readCfgFile('bt', id + '.yml')
        adata['run'] = True
        # YAML and write to file
        self.writeCfgFile('bt', id, adata)
