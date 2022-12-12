import os.path
import oyaml as yaml
from datetime import datetime
import sys


class Basic():
    def __init__(self, appRoot, db):
        self.db = db
        self.appRoot = appRoot
        # Runner Paths
        self.tmpPath = appRoot + os.path.sep + 'tmp' + os.path.sep
        self.runPath = self.tmpPath + 'run' + os.path.sep
        self.upPath = self.tmpPath + 'uploads' + os.path.sep
        self.logPath = appRoot + os.path.sep + 'logs' + os.path.sep
        # Configuration Paths
        self.confPath = appRoot + os.path.sep + 'conf' + os.path.sep
        self.dataConfPath = self.confPath + 'data' + os.path.sep
        self.conConfPath = self.confPath + 'conn' + os.path.sep
        self.enConfPath = self.confPath + 'enrich' + os.path.sep
        # Data paths
        self.dataPath = appRoot + os.path.sep + 'data' + os.path.sep
        self.sampleDataPath = self.dataPath + 'samples' + os.path.sep
        self.nuggetDataPath = self.dataPath + 'nuggets' + os.path.sep
        self.annDataPath = self.dataPath + 'aiann' + os.path.sep
        self.btDataPath = self.dataPath + 'bt' + os.path.sep
        self.btplDataPath = self.dataPath + 'bt-tpl' + os.path.sep
        # Chart Path
        self.chartPath = appRoot + os.path.sep + 'static' + os.path.sep + 'charts' + os.path.sep
        self.stBtPath = appRoot + os.path.sep + 'static' + os.path.sep + 'bt' + os.path.sep
        # Time format
        self.timeform = '%d/%m/%Y'
        # Bokeh theme
        self.bokehTheme = 'caliber'

    def Hello(self):
        print('Hello this is basic')

    def ll(self, info):
        # HEADER = '\033[95m'
        # OKBLUE = '\033[94m'
        # OKGREEN = '\033[92m'
        # WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        # BOLD = '\033[1m'
        # UNDERLINE = '\033[4m'
        print(f"{FAIL}" + str(info) + f"{ENDC}", file=sys.stderr)

    # List of Config files
    def listCfgFiles(self, oftype):
        return [f for f in os.listdir(self.confPath + oftype) if os.path.isfile(os.path.join(self.confPath + oftype, f)) and f != '.keep']

    # List of Data Files
    def listDataFiles(self, oftype):
        return [f for f in os.listdir(self.dataPath + oftype) if os.path.isfile(os.path.join(self.dataPath + oftype, f)) and f != '.keep']

    # List of Upload Files
    def listUpFiles(self):
        return [f for f in os.listdir(self.upPath) if os.path.isfile(os.path.join(self.upPath, f)) and f != '.keep']

    # Write Config File using Dict
    def writeCfgFile(self, oftype, nom, input):
        fname = self.confPath + oftype + os.path.sep + nom + '.yml'
        iYML = yaml.dump(input, default_flow_style=False, sort_keys=False)
        with open(fname, 'w') as file:
            file.write(iYML)

    # Write Config File using Raw data
    def writeRawCfgFile(self, oftype, nom, input):
        fname = self.confPath + oftype + os.path.sep + nom + '.yml'
        with open(fname, 'w') as file:
            file.write(input)

    # Read Config File
    def readCfgFile(self, oftype, nom):
        fname = self.confPath + oftype + os.path.sep + nom
        with open(fname, 'r') as file:
            output = yaml.full_load(file)
        return output

    def allCfgs(self, conffolder):
        # List configs in folder ignoring .keep files
        cfgfiles = self.listCfgFiles(conffolder)
        # Create data array
        cfgfull = []
        # Iterate through each file and pull data
        for cfgfile in cfgfiles:
            cfgdata = self.readCfgFile(conffolder, cfgfile)
            cfgfull.append(cfgdata)
        return cfgfull

    # Get info on all nuggets
    def nuggetsInfo(self, filelist,):
        tmpnuggets = []
        tmpinfo = {}
        # Iterate through each file
        for dfile in filelist:
            # Remove extension from filename
            # print(dfile,file=sys.stderr)
            dstr = os.path.splitext(dfile)[0]
            # Split filename into strings
            parts = dstr.split('_')
            # Create temp info from filename
            tmpinfo = {'id': dstr, 'con': parts[0], 'symb': parts[1] + '/' + parts[2], 'timeframe': parts[3],
                       'from': int(parts[4]), 'to': int(parts[5]), 'indi': parts[6], 'depen': parts[7]}
            # Add temp info to array of nuggets
            tmpnuggets.append(tmpinfo)
        return tmpnuggets

    # Get info on single nugget used in AI Creation
    def nugInfo(self, nfile):
        ntmpinfo = {}
        # Remove extension from filename
        nfile = os.path.splitext(nfile)[0]
        # Split filename into strings
        parts = nfile.split('_')
        # Create temp info from filename
        ntmpinfo = {'id': nfile, 'con': parts[0], 'symb': parts[1] + '/' + parts[2], 'timeframe': parts[3],
                    'from': int(parts[4]), 'to': int(parts[5]), 'indi': parts[6], 'depen': parts[7]}
        # Add temp info to array of nuggets
        return ntmpinfo

    # Get info on samples
    def samplesInfo(self, filelist):
        # Init temp variables
        tmpsamples = []
        tmpinfo = {}
        # Iterate through each file
        for sfile in filelist:
            # Remove extension from filename
            sstr = os.path.splitext(sfile)[0]
            # Split filename into strings
            parts = sstr.split('_')
            # Create temp info from filename
            tmpinfo = {'id': sstr, 'con': parts[0], 'symb': parts[1] + '/' + parts[2], 'timeframe': parts[3], 'from': int(parts[4]), 'to': int(parts[5])}
            # Convert ms date to human readable format
            tmpinfo['from'] = datetime.utcfromtimestamp(tmpinfo['from'] / 1000).strftime(self.timeform)
            tmpinfo['to'] = datetime.utcfromtimestamp(tmpinfo['to'] / 1000).strftime(self.timeform)
            # Add temp info to array of samples
            tmpsamples.append(tmpinfo)
        return tmpsamples

    # Timeframe to Milliseconds
    def tfToMS(self, tf):
        if 'T' in tf:
            temptf = int(tf.replace('T', ''))
            output = temptf * 60 * 1000
        if 'H' in tf:
            temptf = int(tf.replace('H', ''))
            output = temptf * 60 * 60 * 1000
        return output

    # ClearRunLocks
    def clearRunLocks(self):
        runFiles = [f for f in os.listdir(self.runPath) if os.path.isfile(os.path.join(self.runPath, f)) and f != '.keep']
        for file in runFiles:
            os.remove(self.runPath + file)
