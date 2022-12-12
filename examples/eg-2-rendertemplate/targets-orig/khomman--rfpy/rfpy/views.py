import os
from shutil import copyfile
from threading import Thread

from flask import render_template, request, url_for, flash, redirect, jsonify
from rfpy import app, db
from .hkstack import HKStack
from rfpy.data import _async_get_data
from rfpy.models import Stations, Filters, HKResults, ReceiverFunctions,\
                        Earthquakes, Arrivals, RawData, ProgressStatus
from rfpy.plotting import rftn_plot, station_map, hk_map, sta_total_rf_plot,\
                          eq_map
from rfpy.rftn import _async_rf_calc
from rfpy.util import rftn_stream


@app.route('/', methods=['GET', 'POST'])
def index():
    stations = Stations.query.order_by(Stations.station).all()
    total_sta = len(stations)
    status = ProgressStatus.query
    dl_query = status.filter_by(name='download').first()
    rf_query = status.filter_by(name='rf').first()

    if dl_query is not None:
        dl_stat = dl_query.progress
    else:
        dl_stat = 0

    if rf_query is not None:
        rf_stat = rf_query.progress
    else:
        rf_stat = 0

    if total_sta == 0:
        return render_template('index.html')

    todo, hk, qc = 0, 0, 0

    dl_status_file = os.path.join(app.config['BASE_DIR'], 'Data/.stat.txt')
    if os.path.exists(dl_status_file):
        with open(dl_status_file) as f:
            dl_stat = f.read()

    for sta in stations:
        if sta.status == 'H':
            hk += 1
            qc += 1
        elif sta.status == 'Q':
            qc += 1
        else:
            todo += 1
    status = {'total': total_sta, 'todo': todo, 'hk': hk, 'qc': qc,
              'qcpercent': int(100*(qc/total_sta)),
              'todopercent': int(100*(todo/total_sta)),
              'hkpercent': int(100*(hk/total_sta)),
              'dlpercent': dl_stat, 'rfpercent': rf_stat}
    return render_template('index.html', status=status, stations=stations)


@app.route('/stations')
def stations():
    stas = Stations.query.order_by(Stations.station).all()
    return render_template('stations.html', stations=stas)


@app.route('/qc', methods=['GET', 'POST'])
def qc():
    stations = Stations.query.order_by(Stations.station).all()
    filters = Filters.query.order_by(Filters.filter).all()

    if request.method == 'POST':
        sta = request.form['staselect']
        filt = request.form['filtselect']
        start_time = request.form['starttime']
        end_time = request.form['endtime']

        if request.form['selectAll'] == 'yes':
            rf_query = db.session.query(ReceiverFunctions).join(
                                        Stations).join(Filters).filter(
                                        Stations.station == sta).filter(
                                        Filters.filter == filt)
            rfs = [[rftn.path, rftn.accepted, rftn.id] for rftn in rf_query]

        elif request.form['selectAll'] == 'new':
            rf_query = db.session.query(ReceiverFunctions).join(Stations).join(
                                Filters).filter(
                                Stations.station == sta).filter(
                                Filters.filter == filt).filter(
                                ReceiverFunctions.new_receiver_function
                                == True) # noqa
            rfs = [[rftn.path, rftn.accepted, rftn.id] for rftn in rf_query]
        else:
            rf_query = db.session.query(ReceiverFunctions).join(Stations).join(
                                Filters).filter(
                                Stations.station == sta).filter(
                                Filters.filter == filt).filter(
                                ReceiverFunctions.accepted == True) # noqa
            rfs = [[rftn.path, rftn.accepted, rftn.id] for rftn in rf_query]

        # TODO Remove dependency on "eq?" in name..use tr.stats.channel instead
        eqt_rf = [rf[0] for rf in rfs if rf[0][-3:] == 'eqt']
        eqr_rf = [rf[0] for rf in rfs if rf[0][-3:] == 'eqr']
        accepted = {}
        for i in rfs:
            tmp = i[0].split('/')[-1]
            accepted[tmp] = [i[1], i[2]]
        eqt_stream = rftn_stream(eqt_rf)
        eqr_stream = rftn_stream(eqr_rf)
        rftn_plots = rftn_plot(eqr_stream, eqt_stream, start_time, end_time,
                               base_path=app.root_path)
        rftn_results = []
        for i in rftn_plots:
            name = i.split('/')[-1]
            name_rad = name[:-4]
            name_trans = f"{name_rad[:-1]}t"
            val = accepted[name_rad][0]
            dbid_rad = accepted[name_rad][1]
            dbid_trans = accepted[name_trans][1]
            rftn_results.append([i, val, dbid_rad, dbid_trans, sta])
            rftn_results.sort(key=lambda x: x[1], reverse=True)
        return render_template('rftnqc.html', stas=stations, filters=filters,
                               eqrresult=rftn_results)
    return render_template('rftnqc.html', stas=stations, filters=filters)


@app.route('/doneqc', methods=['GET', 'POST'])
def doneqc():
    ''' Parses JSON sent from cliet.  JSON contains 2 ids that correspond
    to the radial and transverse rftn entries in the database.  Selects both
    entries and sets the values (accepted and new_receiver_function)
    '''
    for rf in request.json:
        query_rad = ReceiverFunctions.query.filter_by(id=rf[0]).first()
        query_trans = ReceiverFunctions.query.filter_by(id=rf[1]).first()
        query_rad.new_receiver_function = False
        query_trans.new_receiver_function = False
        if rf[2]:
            query_rad.accepted = True
            query_trans.accepted = True
        else:
            query_rad.accepted = False
            query_trans.accepted = False

    station = request.json[-1][4]
    query_sta = Stations.query.filter_by(station=station).first()
    query_sta.status = "Q"
    db.session.commit()

    return redirect(url_for('qc'))


@app.route('/hkstack', methods=['GET', 'POST'])
def hkstack():
    stations = Stations.query.order_by(Stations.station).all()
    filters = Filters.query.order_by(Filters.filter).all()

    if request.method == 'POST':
        sta = request.form['staselect']
        filt = request.form['filtselect']
        w1 = float(request.form['w1'])
        w2 = float(request.form['w2'])
        w3 = float(request.form['w3'])
        vp = float(request.form['vp'])
        h_ini = float(request.form['startDepth'])
        h_fin = float(request.form['endDepth'])
        k_ini = float(request.form['startKappa'])
        k_fin = float(request.form['endKappa'])
        plot_ts = float(request.form['startTime'])
        plot_tf = float(request.form['endTime'])
        if 'pws' in request.form:
            pws = True
        else:
            pws = False

        if 'doboot' in request.form:
            do_boot = True
        else:
            do_boot = False
        rf_query = db.session.query(ReceiverFunctions).join(
                                    Stations).join(Filters).filter(
                                    Stations.station == sta).filter(
                                    Filters.filter == filt)
        rfs = [rftn.path for rftn in rf_query
               if rftn.accepted is True and rftn.path[-1] == 'r']

        if len(rfs) == 0:
            flash('No accepted receiver functions!  Add receiver functions and'
                  'perform quality control')
            return redirect(url_for('hkstack'))

        st = rftn_stream(rfs)
        hk = HKStack(st, station=sta, vp=vp, depth_range=(h_ini, h_fin),
                     kappa_range=(k_ini, k_fin), w1=w1, w2=w2, w3=w3, pws=pws,
                     bs=do_boot, starttime=plot_ts, endtime=plot_tf,
                     plotfile=os.path.join(app.root_path,
                     f'static/{sta}_{filt}_hkstack.svg'))
        plot = hk.plotfile
        plot = f'static/{plot.split("/")[-1]}'
        hk_vals = [hk.maxh, hk.sigmah, hk.maxk, hk.sigmak, vp]
        return render_template('hkstack.html', stas=stations, plot=plot,
                               hk=hk_vals, filters=filters,
                               w1=w1, w2=w2, w3=w3, vp=vp, startd=h_ini,
                               endd=h_fin, startk=k_ini, endk=k_fin, pws=pws,
                               bs=do_boot, starttime=plot_ts, endtime=plot_tf,
                               staval=sta, filtval=filt, newform=0)
    return render_template('hkstack.html', stas=stations, filters=filters,
                           newform=1)


@app.route('/savehk', methods=["GET", "POST"])
def savehk():
    '''
    Receives JSON object from HKstack page.  Parses object and updates
    database to reflect the calculated values.  If no entry in the database
    create one.  Otherwise, update the entry.
    '''
    payload = request.json
    sta = payload['sta']
    filt = payload['filt']
    if payload['sigmah'] == 'None':
        sigmah = 0.0
        sigmak = 0.0
    else:
        sigmah = float(payload['sigmah'])
        sigmak = float(payload['sigmak'])
    path_to_save = app.config['BASE_PLOT_PATH']
    saved_hk = f'{path_to_save}{payload["fname"]}'
    copyfile(f'{app.root_path}/{payload["hkpath"]}', saved_hk)
    query = db.session.query(HKResults).join(Stations).join(Filters).filter(
                            Stations.station == sta).filter(
                            Filters.filter == filt).first()
    if query:
        query.h = payload['maxh']
        query.k = payload['maxk']
        query.sigmah = payload['sigmah']
        query.sigmak = payload['sigmak']
        query.vp = payload['vp']
        query.hkpath = payload['hkpath']
        # Grab station from query.id in order to update status column
        sta_query = Stations.query.filter_by(id=query.station).first()
        sta_query.status = "H"
    else:
        sta_id = Stations.query.filter_by(station=sta).first().id
        filt_id = Filters.query.filter_by(filter=filt).first().id
        hk = HKResults(station=sta_id, filter=filt_id,
                       hkpath=payload['hkpath'], savedhkpath=saved_hk,
                       h=float(payload['maxh']),
                       sigmah=sigmah,
                       k=float(payload['maxk']),
                       sigmak=sigmak,
                       vp=float(payload['vp']))
        db.session.add(hk)
        # Grab station from query.id in order to update status column
        sta_query = Stations.query.filter_by(id=sta_id).first()
        sta_query.status = "H"

    db.session.commit()
    return redirect(url_for('index'))


@app.route('/plots', methods=['GET', 'POST'])
def plots():
    return render_template('plots.html', plot=None, format='')


@app.route('/stationmap')
def stationmap():
    """ View for stationmap plot """
    stations = Stations.query.all()
    if len(stations) == 0:
        flash('No station data in database...Please download or add data')
        return redirect(url_for('index'))
    sta_lats = []
    sta_lons = []
    sta_names = []
    for sta in stations:
        sta_lats.append(sta.latitude)
        sta_lons.append(sta.longitude)
        sta_names.append(sta.station)

    station_map(sta_lats, sta_lons, sta_names=sta_names,
                filename=os.path.join(app.root_path,
                                      'static', 'station_map.svg'))

    plot = "static/station_map.svg"

    return render_template('plots.html', plot=plot, format='station')


@app.route('/hkmap')
def hkmap():
    ''' View to plot depth and kappa maps'''
    plots = []
    filt_query = Filters.query.all()
    for filt in filt_query:
        f = filt.id
        sta_query = HKResults.query.filter_by(filter=f).all()
        if len(sta_query) == 0:
            continue
        sta_lats = []
        sta_lons = []
        sta_names = []
        depth_vals = []
        kappa_vals = []
        for sta in sta_query:
            sta_lats.append(sta.hk_station.latitude)
            sta_lons.append(sta.hk_station.longitude)
            sta_names.append(sta.hk_station.station)
            depth_vals.append(sta.h)
            kappa_vals.append(sta.k)

        depth_plot = f'static/depth_map_{f}.svg'
        kappa_plot = f'static/kappa_map_{f}.svg'
        plots.append([depth_plot, kappa_plot])
        hk_map(sta_lats, sta_lons, depth_vals, sta_names=sta_names,
               filter=filt.filter,
               filename=os.path.join(app.root_path, depth_plot))
        hk_map(sta_lats, sta_lons, kappa_vals, sta_names=sta_names,
               filter=filt.filter,
               filename=os.path.join(app.root_path, kappa_plot))

    return render_template('plots.html', plot=plots,
                           format='hk')


@app.route('/eqmap')
def eqmap():
    """ View to plot earthquakes used in study """
    eqs = Earthquakes.query.filter_by(utilized=True)
    sta_coords = [[s.latitude, s.longitude] for s in Stations.query.all()]
    if len(sta_coords) == 0 or len(eqs.all()) == 0:
        flash(f"No stations or earthquakes in database...Please download "
              f"or add data")
        return redirect(url_for('index'))
    min_lat = min([i[0] for i in sta_coords])
    max_lat = max([i[0] for i in sta_coords])
    min_lon = min([i[1] for i in sta_coords])
    max_lon = max([i[1] for i in sta_coords])
    center_lat = (max_lat - min_lat)/2 + min_lat
    center_lon = (max_lon - min_lon)/2 + min_lon
    eq_lat = [eq.latitude for eq in eqs]
    eq_lon = [eq.longitude for eq in eqs]
    eq_plot = 'static/eq_map.svg'
    eq_map(eq_lat, eq_lon, center_lat, center_lon,
           filename=os.path.join(app.root_path, eq_plot))
    return render_template('plots.html', plot=eq_plot, format='eq')


@app.route('/rfplots', methods=['GET', 'POST'])
def rfplots():
    stations = Stations.query.order_by(Stations.station).all()

    if request.method == 'POST':
        sta = request.form['staselect']
        plot_start = request.form['startTime']
        plot_end = request.form['endTime']

        sta_id = Stations.query.filter_by(station=sta).first().id
        filt_query = Filters.query.all()
        plots = []
        for filt in filt_query:
            f = filt.id
            rf_query = ReceiverFunctions.query.filter_by(station=sta_id) \
                                              .filter_by(filter=f) \
                                              .filter_by(accepted=True).all()
            if not rf_query:
                continue
            rfs = [rf.path for rf in rf_query]
            st = rftn_stream(rfs)
            plot = f'static/{sta}_{filt.filter}_totalPlot.svg'
            sta_total_rf_plot(st, plot_start=float(plot_start),
                              plot_end=float(plot_end),
                              title=f'Station: {sta}    Filter: {filt.filter}',
                              filename=os.path.join(app.root_path, plot))
            plots.append(plot)
        return render_template('rfplots.html', plots=plots, stas=stations)
    return render_template('rfplots.html', stas=stations)


@app.route('/dbAdmin', methods=['GET', 'POST'])
def dbAdmin():
    tables = [['HKResults', 'hk'], ['Filters', 'filter'],
              ['Receiver Functions', 'rftn'], ['Stations', 'station'],
              ['Earthquakes', 'earthquakes'], ['Arrivals', 'arrivals'],
              ['Raw Data', 'rawdata']]
    return render_template('dbAdmin.html', tables=tables)


@app.route('/getTables', methods=['GET', 'POST'])
def getTables():
    table = request.args.get('table')
    if table == 'hk':
        data = HKResults.query.all()
    elif table == 'station':
        data = Stations.query.all()
    elif table == 'filter':
        data = Filters.query.all()
    elif table == 'rftn':
        data = ReceiverFunctions.query.all()
    elif table == 'earthquakes':
        data = Earthquakes.query.all()
    elif table == 'arrivals':
        data = Arrivals.query.all()
    elif table == 'rawdata':
        data = RawData.query.all()
    else:
        flash('That table is not available')
        return redirect(url_for('dbAdmin'))

    data_list = [d.as_dict() for d in data]
    return jsonify(data_list)


@app.route('/exportData', methods=['GET', 'POST'])
def exportData():
    stas = Stations.query.all()
    hk = HKResults.query.all()
    eq = Earthquakes.query.all()
    arr = Arrivals.query.all()

    with open(f'{app.config["BASE_EXPORT_PATH"]}RFTN_Stations.txt', 'w') as f:
        f.write('Station Latitude Longitude Elevation\n')
        for s in stas:
            f.write(f'{s.station} {s.latitude} {s.longitude} {s.elevation}\n')

    with open(f'{app.config["BASE_EXPORT_PATH"]}HK_Results.txt', 'w') as f:
        f.write('Station Latitude Longitude Elevation Filter Depth SigmaDepth')
        f.write('Kappa SigmaKappa Vp\n')
        for i in hk:
            f.write(f'{i.hk_station.station} {i.hk_station.latitude} ')
            f.write(f'{i.hk_station.longitude} {i.hk_station.elevation} ')
            f.write(f'{i.hk_filter.filter} {i.h} {round(i.sigmah, 1)} {i.k} ')
            f.write(f'{round(i.sigmak, 2)} {i.vp}\n')

    with open(f'{app.config["BASE_EXPORT_PATH"]}RFTN_Eqs.txt', 'w') as f:
        f.write('Time Latitude Longitude Depth Used\n')
        for e in eq:
            f.write(f'{e.origin_time} {e.latitude} {e.longitude} {e.depth} ')
            f.write(f'{e.utilized}\n')

    with open(f'{app.config["BASE_EXPORT_PATH"]}RFTN_Arrivals.txt', 'w') as f:
        f.write('Type Time Station Earthquake\n')
        for a in arr:
            f.write(f'{a.arr_type} {a.time} {a.station.station} {a.eq_id}\n')

    flash(f'Data saved to {app.config["BASE_EXPORT_PATH"]}')
    return redirect(url_for('index'))


@app.route('/getData', methods=['GET', 'POST'])
def getData():
    if request.method == 'POST':
        stations = request.form['stations'].splitlines()
        channels = request.form['channels']
        location = request.form['location']
        start_time = request.form['start-time']
        end_time = request.form['end-time']
        minmag = request.form['min-magnitude']
        username = request.form['username']
        password = request.form['password']
        # pass info to get_data, get_stations etc
        # run in background thread? (celery seems like overkill to have users
        # setup)
        nets = ','.join(set([s.split('_')[0] for s in stations]))
        stas = ','.join(set([s.split('_')[1] for s in stations]))
        kw = {'starttime': start_time,
              'endtime': end_time,
              'network': nets,
              'station': stas,
              'channels': channels,
              'location': location,
              'minmagnitude': minmag}

        if username and password != '':
            kw['username'] = username
            kw['password'] = password

        Thread(target=_async_get_data, args=(app,), kwargs=kw).start()

        flash(f'Your data will be downloaded')
        return (f'<p>Loading...</p><script> let timer=setTimeout(()=>'
                f'{{window.location="{url_for("index")}"}}, 4000)</script>')
        # return redirect(url_for('index'))
    return render_template('getData.html')


@app.route('/calc_rf', methods=['POST'])
def calc_rf():
    # stations = request.form['station'].splitlines()
    # sta_ids = Stations.query.filter(Stations.station.in_(stations))
    # data_query = RawData.query.filter(RawData.sta_id.in_(sta_ids))
    data = [(d.path, d.earthquake_id) for d in
            RawData.query.filter_by(new_data=True).all()]
    gaussians = [float(g) for g in request.form['gaussians'].splitlines()]
    rms_cut = request.form['rms-cut']
    trim_start = request.form['trim-start']
    trim_end = request.form['trim-end']
    prefilt_low = request.form['prefilt-low']
    prefilt_high = request.form['prefilt-high']
    dt = request.form['dt']
    kw = {'data': data,
          'gauss': gaussians,
          'trim': (int(trim_start), int(trim_end)),
          'prefilt': (float(prefilt_low), float(prefilt_high)),
          'dt': float(dt),
          'rms_cut': float(rms_cut)}
    Thread(target=_async_rf_calc, args=(app,), kwargs=kw).start()
    # spin up more processes for more compute power during deconvolution?
    flash('Calculating Receiver Functions')
    return redirect(url_for('index'))


@app.route('/poll_status')
def poll_status():
    data = ProgressStatus.query.all()
    data_list = [{d.name: d.progress} for d in data]
    print(data_list)
    return jsonify(data_list)


@app.after_request
def add_header(r):
    """ Add headers to disable caching """
    r.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    r.headers['Pragma'] = 'no-cache'
    r.headers['Expires'] = '0'
    return r
