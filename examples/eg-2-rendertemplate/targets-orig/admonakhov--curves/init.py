from flask import Flask, render_template, request, jsonify, send_file, redirect
import mymath
import mkxlsx
import os, json, re
import readxlsx
import numpy as np

stress = []
count = []
properties = {}
s = {}
e = {}
UPLOAD_FOLDER = '/home/ant/Programms/curves/'
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.chdir(UPLOAD_FOLDER)

@app.route('/')
def main_page():
    return render_template("main.html")


@app.route('/sncurve', methods=['POST'])
def sn_curve_ret():
    if request.form['key'] == 'regression':
        stress = list(map(int, request.form.getlist('stress')))
        count = list(map(int, request.form.getlist('count')))
        if (len(stress) == len(count)) and (len(stress) > 1):
            if request.form['equation'] == 'pow':
                d = mymath.pow_equation(count, stress)
            if request.form['equation'] == 'mandell':
                d = mymath.mandell_pow_equation(count, stress)
            return json.dumps({'stress': d['y'], 'count': d['x'], 'intercept': d['intercept'], 'slope': d['slope'],
                               'key': 'regression'})
        else:
            return json.dumps({'stress': [], 'count': [], 'intercept': 0, 'slope': 0, 'key': 'regression'})
    elif request.form['key'] == 'mkxlsx':
        d = json.loads(request.form['data'])
        mkxlsx.mk_book(d)
        return json.dumps({'key': 'file'})


@app.route('/sncurve', methods=['GET'])
def sn_page():
    return render_template("sncurve.html")


@app.route('/sscurve', methods=['GET'])
def ss_page():
    return render_template("sscurve.html")


@app.route('/sscurve', methods=['POST'])
def ss_curve_pos():
    global s, e, properties
    if 'filetosave' in request.files:
        print('File is come!')
        for file in request.files:
            f = request.files[file]
            extension = re.findall(r'(?:\w+.)(\w+)', f.filename)[0]
            if f and mkxlsx.allowed_file(extension):
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], 'upload.' + extension))
                if extension == 'xlsx':
                    try:
                        s, e = readxlsx.mk_df(UPLOAD_FOLDER+'upload.xlsx')
                    except:
                        return json.dumps({'key': 'no_data'})
                    for key in s.keys():
                        properties[key] = mymath.s_s_prop(e[key], s[key], 100, 200)
                    print(properties.keys())
        return json.dumps({'properties': properties, 'status': 'uploaded'})
    elif request.form['key'] == 'request_data':
        properties[request.form['sample']] = mymath.s_s_prop(e[request.form['sample']], s[request.form['sample']],
                                                             int(request.form['begin']), int(request.form['end']))
        stress = readxlsx.less_lenght(s[request.form['sample']], 100)
        strain = readxlsx.less_lenght(e[request.form['sample']], 100)
        stress_reg = np.linspace(0, max(stress) * 1.1, 10)
        strain_reg = ((stress_reg - properties[request.form['sample']]['intercept']) \
                      / properties[request.form['sample']]['slope'])
        strain_reg = list(strain_reg)
        stress_reg = list(stress_reg)

        return json.dumps({'properties': properties, 'strain': strain, 'stress': stress,
                           'strain_reg': strain_reg, 'stress_reg': stress_reg, 'key': 'data'})
    elif request.form['key'] == 'reload_data':
        for sample in s.keys():
            properties[sample] = mymath.s_s_prop(e[sample], s[sample], int(request.form['begin']),
                                                 int(request.form['end']))
        return json.dumps({'properties': properties, 'key': 'properties'})
    elif request.form['key'] == 'stats':
        stats = {}
        props = {}
        for sample in properties.keys():
            for p in properties[sample]:
                if p in props.keys():
                    props[p].append(properties[sample][p])
                else:
                    props[p] = []
                    props[p].append(properties[sample][p])
        for prop in ['ultimate', 'modulus', 'proportional', 'yield', 'extension']:
            stats[prop] = {}
            stats[prop]['Макс'] = mymath.round_step(max(props[prop]), 0.1)
            stats[prop]['Мин'] = mymath.round_step(min(props[prop]), 0.1)
            stats[prop]['Сред.'] = mymath.round_step(mymath.mean(props[prop]), 0.1)
            stats[prop]['СКО'] = mymath.round_step(mymath.sko(props[prop]), 0.1)
            stats[prop]['CV, %'] = mymath.round_step(mymath.cv(props[prop]), 0.1)
        return json.dumps({'stats': stats, 'key': 'stats'})


@app.route('/xlsxdownload.xlsx', methods=['GET'])
def xlsxdownload():
    return send_file('/home/ant/Programms/curves/tmp.xlsx')


@app.route('/resources', methods=['GET'])
def resources():
    return render_template("resources.html")

