""" Human readable views for the SMR site
"""
import io
from os import environ
from datetime import datetime, timedelta

from flask import send_file, render_template, request, abort
from flask.views import MethodView

from odinapi.views.level1b_scandata_exporter_v2 import (
    get_scan_data_v2, plot_scan)
from odinapi.views.level1b_scanlogdata_exporter import (
    get_scan_logdata, plot_loginfo)
from odinapi.views.database import DatabaseConnector
from odinapi.views.level2 import parse_parameters
from odinapi.utils.defs import FREQMODE_TO_BACKEND


class ViewIndex(MethodView):
    """View for Index page"""

    def get(self):
        return render_template('index.html', data=str('ODIN_API_PRODUCTION' in
                                                      environ))


class ViewLevel1(MethodView):
    """View of all scans"""

    def get(self):
        return render_template('level1.html', data=str('ODIN_API_PRODUCTION' in
                                                       environ))


class ViewLevel1Stats(MethodView):
    """View statistics of level1 scans"""

    def get(self):
        return render_template('level1stats.html')


class ViewLevel2(MethodView):
    """View of all scans"""

    def get(self):
        return render_template('level2.html')


class ViewLevel2Scan(MethodView):
    """View level2 single scan"""

    def get(self, project, freqmode, scanno):
        data = {'title': 'production',
                'project': project,
                'freqmode': freqmode,
                'scanno': scanno}
        return render_template('level2scan.html', data=data)


class ViewLevel2DevScan(MethodView):
    """View level2 development single scan"""

    def get(self, title, project, freqmode, scanno):
        data = {'title': title,
                'project': project,
                'freqmode': freqmode,
                'scanno': scanno}
        return render_template('level2scan.html', data=data)


class ViewLevel2PeriodOverview(MethodView):
    """View of all scans for period shown on a map"""

    def get(self, project):
        try:
            params = parse_parameters(
                min_lon=0, max_lon=360, min_lat=-90, max_lat=90,
                min_altitude=0, max_altitude=150000)
            params['start_time'] = params['start_time'].date().isoformat()
            params['end_time'] = params['end_time'].date().isoformat()
        except ValueError:
            params = {
                "start_time": (datetime.today() -
                               timedelta(days=1)).date().isoformat(),
                "end_time": datetime.today().date().isoformat(),
                "products": ["O3 / 501 GHz / 20 to 50 km"],
                "min_altitude": 0,
                "max_altitude": 150000,
            }
        params["product"] = params["products"][0]
        params.pop("products")
        params["min_lon"] = request.args.get('min_lon', '0')
        params["max_lon"] = request.args.get('max_lon', '360')
        params["min_lat"] = request.args.get('min_lat', '-90')
        params["max_lat"] = request.args.get('max_lat', '90')
        params.pop("areas")
        data = {
            "project": project,
            "parameter": "VMR",
            "parameters": params,
        }
        return render_template('level2periodoverview.html', data=data)


class ViewScanSpec(MethodView):
    """plots information: data from a given scan"""

    def get(self, freqmode, scanno):
        try:
            backend = FREQMODE_TO_BACKEND[freqmode]
        except KeyError:
            abort(404)

        con = DatabaseConnector()
        calstw = int(scanno)
        spectra = get_scan_data_v2(con, backend, freqmode, scanno)
        fig = plot_scan(backend, calstw, spectra)
        con.close()
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)

        return send_file(
            buf, attachment_filename='plot.png', mimetype='image/png')


class ViewFreqmodeInfoPlot(MethodView):
    """plots information: loginfo for all scans from a given date and freqmode
    """

    def get(self, date, freqmode):
        try:
            backend = FREQMODE_TO_BACKEND[freqmode]
        except KeyError:
            abort(404)

        con = DatabaseConnector()
        loginfo, date1, date2 = get_scan_logdata(
            con, backend, date+'T00:00:00', int(freqmode), 1)
        con.close()

        lista = []
        for ind in range(len(loginfo['ScanID'])):
            row = []
            row.append(loginfo['DateTime'][ind].date())
            for item in ['DateTime', 'FreqMode', 'StartLat', 'EndLat', 'SunZD',
                         'AltStart', 'AltEnd', 'ScanID']:
                row.append(loginfo[item][ind])
            lista.append(row)

        fig = plot_loginfo(backend, date1, date2, loginfo)
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        return send_file(buf, attachment_filename='plot.png',
                         mimetype='image/png')


class ViewDataAccess(MethodView):
    """View for Data access page"""

    def get(self):
        return render_template('dataaccess.html',
                               data=str('ODIN_API_PRODUCTION' in environ))
