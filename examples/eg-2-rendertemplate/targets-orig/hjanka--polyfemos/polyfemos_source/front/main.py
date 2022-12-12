# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This file is part of Polyfemos.
#
# Polyfemos is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or any later version.
#
# Polyfemos is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License and
# GNU General Public License along with Polyfemos. If not, see
# <https://www.gnu.org/licenses/>.'
#
# Author: Henrik Jänkävaara
# -----------------------------------------------------------------------------
"""
Frontend of polyfemos

Utilizes `Flask <http://flask.pocoo.org/>`_

Functions used for different site:

- :func:`~polyfemos.front.main.index_alias`
- :func:`~polyfemos.front.main.home`
- :func:`~polyfemos.front.main.sohtable`
- :func:`~polyfemos.front.main.sohmap`
- :func:`~polyfemos.front.main.datacoverageimage`
- :func:`~polyfemos.front.main.summary`
- :func:`~polyfemos.front.main.datacoveragebrowser`
- :func:`~polyfemos.front.main.plotbrowser`
- :func:`~polyfemos.front.main.alertheat`

See :ref:`Frontend` for documentation.

:copyright:
    2019, University of Oulu, Sodankyla Geophysical Observatory
:license:
    GNU Lesser General Public License v3.0 or later
    (https://spdx.org/licenses/LGPL-3.0-or-later.html)
"""
import os
import itertools
import functools
import math
import csv
import time
from io import BytesIO, StringIO
from datetime import timedelta, datetime
from dateutil import tz
from PIL.PngImagePlugin import PngImageFile
from PIL import Image, ImageDraw, ImageFont
import base64
from urllib.parse import quote
import importlib

from flask import (Flask, make_response, stream_with_context,
                   send_from_directory)

import numpy as np
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
plt.switch_backend('agg')
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.colors import LinearSegmentedColormap, rgb2hex

import bokeh
from obspy import UTCDateTime

from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response

from polyfemos.parser import typeoperator as to
from polyfemos.util.messenger import messenger
from polyfemos.data import outlierremover
from polyfemos.util import coordinator
from polyfemos.almanac.utils import parse_date, get_jY
from polyfemos.front import colors, userdef, request
from polyfemos.front.sohplot.sohplot import SOHPlot
from polyfemos.front.trafficmonitor import (logged, limited, IPStorage,
                                            check_permission, limit_access)
from polyfemos.front.alertreader import get_sohdict


# Initialize app
app = Flask(__name__, instance_relative_config=True)
app.config.from_object('polyfemos.front.flask_config.ProductionConfig')
app.config['SECRET_KEY'] = userdef.secret_key()

# IPStorage to be used with @limited functions as a decorator argument
ipstorage = IPStorage()
# Replaces the normally used flask's render_template function
render_template = colors.colored_template


if 0:
    # If addional logging is wanted
    import logging
    app.config['LOG_FILE'] = 'application.log'
    if not app.debug:
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(app.config['LOG_FILE'])
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        logger.addHandler(file_handler)


def render_base(func_):
    """
    :type func\_: func
    :param func\_: :func:`~flask.render_template`
    :rtype: func
    :return: decorated function
    """
    @functools.wraps(func_)
    def wrapper(*args, **kwargs):
        utcdatetime_now = UTCDateTime(precision=0)
        timestr = []
        timestr.append("polyfemos system time {} ".format(
            utcdatetime_now.strftime("%Y.%j")))
        timestr.append("{}".format(
            utcdatetime_now.strftime("%Y-%m-%d %H:%M:%S UTC")))
        timestr.append("{}".format(
            datetime.now(tz=tz.tzlocal()).strftime("%Y-%m-%d %H:%M:%S %Z")))
        if "network_code" not in kwargs:
            kwargs["network_code"] = request.cookie("network_code")
        return func_(*args, timestr=timestr, **kwargs)
    return wrapper


def get_image_data(image):
    """
    Converts the images into ascii

    :type image: :obj:`~PIL.PngImagePlugin.PngImageFile` or
        :class:`~matplotlib.figure.Figure`, or :obj:`~PIL.Image.Image`
    :param image:
    :rtype: str
    :return: ``image`` as ascii
    """
    buffer_ = BytesIO()
    if isinstance(image, (PngImageFile, Image.Image)):
        image.save(buffer_, 'PNG')
    elif isinstance(image, Figure):
        canvas = FigureCanvas(image)
        canvas.print_png(buffer_)
    else:
        return ""
    data = base64.b64encode(buffer_.getvalue()).decode('ascii')
    data = 'data:image/png;base64,{}'.format(quote(data))
    return data


def get_summary(startdate="", enddate="", headerdate="", combinations=[],
                remove_irrationals=False, advanced_outlier_removal=False,
                fext="csv"):
    """
    The function used to get the statistical summary of station/sohpar
    combinations.
    The execution is little bit slow because the combinations are
    dealt separately, which means that, as all of the sohpars are in the same
    file, the file is opened and closed multiple times during
    the creation of the summary

    :type startdate: str or :class:`~datetime.date`
    :param startdate:
    :type enddate: str or :class:`~datetime.date`
    :param enddate:
    :type headerdate: str or :class:`~datetime.date`
    :param headerdate: The header information of this date is used in
        calculations
    :type combinations: list[tuple[str, str]]
    :param combinations: list containing all unique station and sohpar
        combinations
    :type remove_irrationals: bool, optional
    :param remove_irrationals: defaults to ``False``, If ``True``, irrational
        values (limits defined in stf header) are removed from the data.
    :type advanced_outlier_removal: bool, optional
    :param advanced_outlier_removal: defaults to ``False``. If ``True``,
        advanced outlier removal is used for specific station/sohpar
        combination. The combinations and outlier removal are provided by
        :func:`~polyfemos.front.userdef.summary_outlierremfuncs`, if the
        YAML configuration is provided.
    :type fext: str, optional
    :param fext: defaults to "csv", select "stf" or "csv",
        defines the datafile format which is read
    :rtype: list, list
    :return: rows and header, list of lists and a list.
    """
    rows = []
    header = []
    max_loops = len(combinations)

    for i, (station_id, sohpar_name) in enumerate(combinations):

        sohplot = SOHPlot(
            station_id=station_id,
            sohpar_name=sohpar_name,
            startdate=startdate,
            enddate=enddate,
            headerdate=headerdate,
            remove_irrationals=remove_irrationals,
            advanced_outlier_removal=advanced_outlier_removal,
            fext=fext)

        dict_ = sohplot.get_statistics_dict()

        if not header:
            header = ["Station", "Sohpar"] + list(dict_.keys())
        row = [station_id, sohpar_name]

        # If every numerical value is nan, don't show the parameter
        func_ = lambda x: isinstance(x, str) or math.isnan(x)
        if all(map(func_, dict_.values())):
            continue
        rows.append(row + list(dict_.values()))

        pr = 100.0 * float(i + 1) / max_loops
        msg = "Summary table, percents ready: {:.2f}".format(pr)
        messenger(msg, "R")

    return rows, header


def generate_csv(rows):
    """
    :type rows: list
    :param rows: list of lists to be written into csv
    :rtype: generator
    :return: generator yielding rows of csv file
    """
    data = StringIO()
    csvwriter = csv.writer(data)
    for row in rows:
        csvwriter.writerow(row)
        yield data.getvalue()
        data.seek(0)
        data.truncate(0)


def csv_response(rows):
    """
    :type rows: list
    :param rows: list of lists to be written into csv
    :rtype: :class:`~werkzeug.wrappers.Response`
    :return: csv file as a html response
    """
    headers = Headers()
    headers.set('Content-Disposition', 'attachment', filename='summary.csv')

    return Response(
        stream_with_context(generate_csv(rows)),
        mimetype='text/csv', headers=headers,
    )


@app.route('/', defaults={'filename': ''})
@app.route('/<path:filename>')
@logged
def index_alias(filename):
    """
    Index site of the polyfemos web.
    In addition provides the documentation files.
    """
    msg = "Documentation filename: {}".format(filename)
    messenger(msg, "R")
    if not filename:
        return render_template('index.htm')
    folder = userdef.paths("doc_dir")
    return send_from_directory(folder, filename)


@app.route('/home', methods=['GET', 'POST'])
@logged
def home():
    """
    Navigation site consisting of link library for every site
    available in polyfemos web.
    """
    from polyfemos.front.forms import SelectNetworkForm
    form = SelectNetworkForm()

    if not form.validate_on_submit():
        form.network_code.data = userdef.get_network_code()

    network_code = form.network_code.data

    resp = render_base(render_template)('home.htm', form=form,
                                        network_code=network_code)
    resp = make_response(resp)
    resp.set_cookie("network_code", value=network_code)

    return resp


@app.route('/sohtable', methods=['GET', 'POST'])
@logged
@limit_access(access_level=3)
def sohtable():
    """
    A state of health table with every station and parameter combination,
    incorporating current alerts and alert history.
    """
    from polyfemos.front import forms
    importlib.reload(forms)
    form = forms.SohTableForm()

    if not form.validate_on_submit():
        form.date.data = UTCDateTime().now().date
        form.show_all.data = True
        form.realtimeness_bool.data = True
        form.realtimeness_limit.data = 120

    realtimeness_limit = form.realtimeness_limit.data
    realtimeness_bool = form.realtimeness_bool.data
    realtimeness = None
    if realtimeness_bool:
        realtimeness = UTCDateTime() - 60 * realtimeness_limit

    date = form.date.data
    if form.submit_pd.data:
        date += timedelta(days=1)
    elif form.submit_sd.data:
        date -= timedelta(days=1)
    form.date.data = date

    julday, year = get_jY(date)
    visibilities = {1, 2} if form.show_all.data else {1}

    sohpar_names = userdef.sohpars(visibilities=visibilities)
    station_ids = userdef.station_ids()

    fpf = userdef.filepathformats("alert")
    sohdict = get_sohdict(station_ids, year, julday, fpf,
                          realtimeness=realtimeness)

    header = ""
    header = "{}.{}".format(year, julday)

    return render_base(render_template)(
        'sohtable.htm', alertdict=sohdict['alerts'], header=header,
        station_ids=station_ids, sohpar_names=sohpar_names, form=form)


@app.route('/sohmap')
@logged
@limit_access(access_level=3)
def sohmap():
    """
    A map of the network area with stations. Alerts are sorted by their
    priorities. The innermost circle consists of the alerts of the highest
    priority.
    """

    alertcolors = {
        0: colors.ALERT_GREEN,
        1: colors.ALERT_YELLOW,
        2: colors.ALERT_RED,
    }

    filename = userdef.paths("map_file")
    filename, extension = os.path.splitext(filename)
    imgfile = "web_static/{}{}".format(filename, extension)
    mapfile = "web_static/{}{}".format(filename, ".map")

    msg = "Img and map files: {}, {}".format(imgfile, mapfile)
    messenger(msg, "R")

    if not os.path.isfile(imgfile):
        return render_base(render_template)('sohmap.htm')
    if not os.path.isfile(mapfile):
        return render_base(render_template)('sohmap.htm')

    # get transformation from WGS84 to pixels
    pixel_transform = coordinator.transform_from_ozi_map(mapfile)

    # open background map
    pil_image = Image.open(imgfile)
    draw = ImageDraw.Draw(pil_image)

    today = UTCDateTime().now()
    julday, year = get_jY(today)
    sohpar_names = userdef.sohpars()
    station_ids = userdef.station_ids()

    # get alerts and priorities with each station and parameter combination
    fpf = userdef.filepathformats("alert")
    sohdict = get_sohdict(station_ids, year, julday, fpf)

    for station_id in station_ids:

        sohplot = SOHPlot(
            station_id=station_id,
            headerdate=today,)

        epsg = sohplot.header["EPSG"]
        locx = sohplot.header["LOCX"]
        locy = sohplot.header["LOCY"]

        if epsg is None:
            continue

        # Convert stations coordinates into WGS84
        transform = coordinator.get_transform(epsg, "4326")
        px, py = pixel_transform(*transform(locx, locy))

        def get_bbox(radius):
            return (px - radius, py - radius, px + radius, py + radius)

        # Alerts are stored in 3x3 matrix
        # Priority in x axis
        # Alert (red, yellow or green) in y axis
        # Red alert with the highest priority is stored in [0,2]
        alertcount = np.zeros((3, 3))
        for sohpar_name in sohpar_names:
            key = station_id + sohpar_name
            if key not in sohdict['alerts']:
                continue
            alert = to.int_(sohdict['alerts'][key])
            priority = to.int_(sohdict['priorities'][key])
            if alert is None or priority is None or priority > 4:
                continue
            priority = min(3, priority) - 1
            alertcount[alert, priority] += 1

        # TODO clean plotting, own function?
        # TODO Scalable map
        radius = 21
        for i in range(3)[::-1]:

            bbox = get_bbox(radius)
            draw.ellipse(bbox, fill=colors.BLACK)
            radius -= 1

            alerts = alertcount[:, i]
            alertsum = np.sum(alerts)

            bbox = get_bbox(radius)
            if alertsum <= 0:
                draw.pieslice(bbox, start=0, end=360, fill=colors.GREY_3)
            else:
                alerts *= 360. / alertsum
                start = 0
                for j in range(3):
                    alert = alerts[j]
                    color = alertcolors[j]
                    end = start + alert
                    draw.pieslice(bbox, start=start, end=end, fill=color)
                    start += alert

            radius -= 5 - i

    fontpath = userdef.paths("ttf_file")
    font = None
    if os.path.isfile(fontpath):
        font = ImageFont.truetype(fontpath, 20)
    str_ = "{} UTC".format(today.strftime("%Y-%m-%d %H:%M:%S"))
    draw.text((10, 10), str_, font=font, fill=(0, 0, 0, 128))

    max_height = 1500
    width, height = pil_image.size
    scale = int(max_height / height)

    pil_image = pil_image.resize(
        (scale * width, scale * height),
        resample=Image.ANTIALIAS)

    data = get_image_data(pil_image)

    return render_base(render_template)('sohmap.htm', sohmapimg=data)


@app.route('/plotbrowser', methods=['GET', 'POST'])
@logged
@limit_access(access_level=3)
@limited(ipstorage)
def plotbrowser():
    """
    Soh plotter site, Plot Browser.
    """
    from polyfemos.front import forms
    importlib.reload(forms)
    form = forms.PlotbrowserForm()

    today = UTCDateTime().now().date

    full_access = check_permission(1)
    message_lines = []

    if not form.validate_on_submit():
        form.station_ids.data = []
        form.sohpar_names.data = []
        form.startdate.data = today
        form.enddate.data = today
        form.headerdate.data = today
        form.rirv.data = False
        form.ridv.data = True
        form.decimate.data = True
        form.track_len.data = True
        form.aor.data = 'null'
        form.fromfileformat.data = "stf"

    if request.arguments("b") == "1":
        selected_date = UTCDateTime(request.arguments("date")).date
        form.station_ids.data = [request.arguments("station_id")]
        form.sohpar_names.data = [request.arguments("sohpar_name")]
        form.startdate.data = selected_date
        form.enddate.data = selected_date

    station_ids = form.station_ids.data
    sohpar_names = form.sohpar_names.data
    startdate = form.startdate.data
    enddate = form.enddate.data
    headerdate = form.headerdate.data
    remove_irrationals = form.rirv.data
    remove_identicals = form.ridv.data
    decimate = form.decimate.data
    track_len = form.track_len.data
    aor_selected = form.aor.data
    fromfileformat = form.fromfileformat.data

    aorkwargs = {
        "null": [],
        "dtr": [],
        "sta": [],
        "lip": [],
    }
    funcs = {
        "dtr": [outlierremover.dtr, {}],
        "sta": [outlierremover.stalta, {}],
        "lip": [outlierremover.lipschitz, {}],
    }
    for field in form:
        split = field.id.split("_")
        if len(split) < 2:
            continue
        id_, kwarg = split
        if id_ not in {"dtr", "sta", "lip"}:
            continue
        aorkwargs[id_].append(field)
        funcs[id_][1][kwarg] = field.data

    outlierremfunc = None
    advanced_outlier_removal = True
    if aor_selected in funcs:
        aorfunc = funcs[aor_selected][0]
        kwargs = funcs[aor_selected][1]
        outlierremfunc = lambda data: aorfunc(data, **kwargs)
    else:
        advanced_outlier_removal = False

    combinations = list(itertools.product(station_ids, sohpar_names))
    if not full_access:
        if not remove_identicals:
            str_ = "You don't have permission to uncheck " \
                + "'Remove identical values'."
            message_lines.append(str_)
            remove_identicals = True
        if not decimate:
            str_ = "You don't have permission to uncheck 'Decimate'."
            message_lines.append(str_)
            decimate = True
        if len(combinations) > 2:
            str_ = "You may only select at most 2 stations or " \
                + "state of health parameters."
            message_lines.append(str_)
            combinations = combinations[:2]
        if abs((startdate - enddate).days) > 35:
            str_ = "You don't have permission to select timespan " \
                + "wider than 35 days."
            message_lines.append(str_)
            startdate = enddate
        limit_date = today - timedelta(days=730)
        if startdate < limit_date or enddate < limit_date:
            str_ = "You don't have permission to view " \
                + "data before {}.".format(str(limit_date))
            message_lines.append(str_)
            startdate = today
            enddate = today

    plots = []
    for station_id, sohpar_name in combinations:
        # Contruct plot
        sohplot = SOHPlot(
            station_id=station_id,
            sohpar_name=sohpar_name,
            startdate=startdate,
            enddate=enddate,
            headerdate=headerdate,
            remove_irrationals=remove_irrationals,
            advanced_outlier_removal=advanced_outlier_removal,
            outlierremfunc=outlierremfunc,
            track_datalen=track_len,
            remove_identicals=remove_identicals,
            fext=fromfileformat)

        plotdict = {}
        stats_table = []
        infolines = []
        plotscript, plotdiv = sohplot.get_plot_components(decimate=decimate)

        if plotscript:
            stats_table = sohplot.get_statistics_table()
            infolines = [line
                         .replace("*", "\xa0")
                         .replace(">", "\u2192")
                         for line in sohplot.get_info()]

        plotdict['stats_table'] = stats_table
        plotdict['plotscript'] = plotscript
        plotdict['plotdiv'] = plotdiv
        plotdict['infolines'] = infolines

        plots.append(plotdict)

    return render_base(render_template)(
        "plotbrowser.htm", bokeh_version=str(bokeh.__version__),
        form=form, plots=plots, aorkwargs=aorkwargs,
        message_lines=message_lines)


@app.route('/datacoveragebrowser', methods=['GET', 'POST'])
@logged
@limit_access(access_level=2)
def datacoveragebrowser():
    """
    Creates the datacoveragebrowser view and edits the link
    which directs to the actual datacoverage image which is created
    according to the given parameters
    """
    from polyfemos.front import forms
    importlib.reload(forms)
    form = forms.DatacoverageForm()

    if not form.validate_on_submit():
        enddate = UTCDateTime().now()
        startdate = enddate - 86400 * 30
        form.station_ids.data = []
        form.channel_codes.data = []
        form.startdate.data = startdate.date
        form.enddate.data = enddate.date

    startdate = parse_date(form.startdate.data)
    enddate = parse_date(form.enddate.data) + 86399
    station_ids = form.station_ids.data
    channel_codes = form.channel_codes.data

    func_ = userdef.datacoveragebrowser_func()
    fig = func_(station_ids, channel_codes, startdate,
                enddate, userdef.filepathformats("rawdata"))
    data = get_image_data(fig)

    return render_base(render_template)(
        "datacoveragebrowser.htm", form=form,
        station_ids=station_ids, channel_codes=channel_codes, dcimage=data)


@app.route('/datacoverageimage')
@logged
@limit_access(access_level=3)
def datacoverageimage():
    """
    A simple site including separately created datacoverage image.
    """
    dci_file = os.path.join("web_static", userdef.paths("dci_file"))
    if not os.path.isfile(dci_file):
        return render_base(render_template)('datacoverageimage.htm')
    data = get_image_data(Image.open(dci_file))
    return render_base(render_template)('datacoverageimage.htm', dci_file=data)


@app.route('/summary', methods=['GET', 'POST'])
@logged
@limit_access(access_level=2)
@limited(ipstorage)
def summary():
    """
    Creates a parameter summary table
    """
    from polyfemos.front import forms
    importlib.reload(forms)
    form = forms.SummaryForm()

    enddate = UTCDateTime().now()
    startdate = enddate - 86400

    t0 = time.time()

    if not form.validate_on_submit():
        form.station_ids.data = []
        form.sohpar_names.data = []
        form.startdate.data = startdate.date
        form.enddate.data = enddate.date
        form.headerdate.data = enddate.date
        form.rirv.data = True
        form.aor.data = False
        form.csv_requested.data = False
        form.fromfileformat.data = "csv"

    station_ids = form.station_ids.data
    sohpar_names = form.sohpar_names.data
    startdate = form.startdate.data
    enddate = form.enddate.data
    headerdate = form.headerdate.data
    remove_irrationals = form.rirv.data
    advanced_outlier_removal = form.aor.data
    csv_requested = form.csv_requested.data
    fromfileformat = form.fromfileformat.data

    combinations = list(itertools.product(station_ids, sohpar_names))

    rows, header = get_summary(
        startdate=startdate,
        enddate=enddate,
        headerdate=headerdate,
        combinations=combinations,
        remove_irrationals=remove_irrationals,
        advanced_outlier_removal=advanced_outlier_removal,
        fext=fromfileformat,
    )

    exectime = round((time.time() - t0) / 60., 4)

    if csv_requested:
        rows.insert(0, header)
        return csv_response(rows)

    return render_base(render_template)(
        "summary.htm", header=header, rows=rows, form=form,
        aorinfolines=userdef.summary_outlierremfunc_info(), exectime=exectime)


@app.route('/alertheat', methods=['GET', 'POST'])
@logged
@limit_access(access_level=2)
def alertheat():
    """
    Creates a state of health table with every station and parameter
    combination. Timespan selection available for time interval anaysis.
    """
    from polyfemos.front import forms
    importlib.reload(forms)
    form = forms.AlertHeatForm()

    enddate = UTCDateTime().now()
    startdate = enddate - 86400 * 20

    if not form.validate_on_submit():
        form.startdate.data = startdate.date
        form.enddate.data = enddate.date
        form.log_color.data = False
        form.points_per_thbb.data = 1
        form.points_per_tib.data = 2

    startdate = parse_date(form.startdate.data)
    enddate = parse_date(form.enddate.data)

    log_color = form.log_color.data

    points = {
        "0": 0,
        "1": form.points_per_thbb.data,
        "2": form.points_per_tib.data,
    }

    sohpar_names = userdef.sohpars(visibilities={1, 2})
    station_ids = userdef.station_ids()
    fpf = userdef.filepathformats("alert")

    results = {}

    while startdate <= enddate:

        julday, year = get_jY(startdate)
        sohdict = get_sohdict(station_ids, year, julday, fpf)

        for k, v in sohdict['alerts'].items():

            if k not in results:
                results[k] = {'count': 0, 'max': 0}

            if v in points:
                results[k]['count'] += points[v]
                results[k]['max'] += 2.

        startdate += 86400

    cmap = LinearSegmentedColormap.from_list("", [
        colors.ALERT_GREEN,
        colors.ALERT_YELLOW,
        colors.ALERT_RED,
    ])

    for k, v in results.items():
        if v['max'] <= 0.:
            v['color'] = colors.GREY_3
            v['tooltip'] = "0 / 0\n0.0%"
            continue
        else:
            percentage = v['count'] / v['max']
        percents = round(100. * percentage, 2)
        if log_color:
            color = 255. * np.log(max(1, percents)) / np.log(100)
        else:
            color = 255. * percentage
        color = int(round(color))
        v['color'] = rgb2hex(cmap(color)[:3])
        v['tooltip'] = "{} / {:.0f}\n{:.1f}%" \
            .format(v['count'], v['max'], percents)

    return render_base(render_template)(
        'alertheat.htm', alertdict=results, station_ids=station_ids,
        sohpar_names=sohpar_names, form=form)


# With debug=True, Flask server will auto-reload
# when there are code changes
if __name__ == '__main__':
    host = "127.0.0.1"
    app.run(host=host, port=5000, debug=False, threaded=True)
