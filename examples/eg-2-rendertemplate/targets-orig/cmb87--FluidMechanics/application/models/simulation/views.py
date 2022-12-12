from flask import Blueprint, request, session, redirect, url_for, render_template, jsonify
import numpy as np
import json

from bokeh.io import output_file, show
from bokeh.models import HoverTool
from bokeh.plotting import figure
from bokeh.embed import components
from bokeh.plotting import figure, show
from bokeh.models import AjaxDataSource, CustomJS
from bokeh.embed import components

from ..simulation.digitaltwin import DigitalTwin
from ..simulation.digitaltwin import DesignLogMessage
from ...common.flask_redirect import redirect_url

dt_blueprint = Blueprint('simulation', __name__)


### Run the digital twin ###
@dt_blueprint.route('/')
def start():
    return render_template('simulation/overview.html', cases=DigitalTwin.retrieveAll())


### Create simulation case ###
@dt_blueprint.route('/create')
def create():
    dt = DigitalTwin()
    caseid = dt.store()
    msg = DesignLogMessage(user=request.remote_addr, caseid=caseid, message="Case created!")
    msg.store()

    return "Case created"


### Remove Data item ###
@dt_blueprint.route('/remove')
def remove():
    DigitalTwin.remove_from_DB(request.args.get('dataid'))
    return "DataItem deleted successfully!"

### Update Data item ###
@dt_blueprint.route('/updateBoundaryConditions/<string:caseid>')
def updateBoundaryConditions(caseid):
    try:
        dt = DigitalTwin.find_by_id(caseid)
        dt.U1 = float(request.args.get('U1value'))
        dt.U2 = float(request.args.get('U2value'))
        dt.alpha1 = float(request.args.get('alpha1value'))
        dt.alpha2 = float(request.args.get('alpha2value'))
        dt.update()

        msg = DesignLogMessage(user=request.remote_addr, caseid=caseid, message="Updated boundary conditions to U1={}[m/s], alpha1={}[deg], U2={}[m/s], alpha2={}[deg]".format(dt.U1,dt.alpha1,dt.U2,dt.alpha2))
        msg.store()

        return "Successfull" #redirect(redirect_url())
    except:
        return "Update not successfull!"

### Update Data item ###
@dt_blueprint.route('/updateGeometry/<string:caseid>')
def updateGeometry(caseid):
    if True:
        dt = DigitalTwin.find_by_id(caseid)
        dt.a0 = float(request.args.get('a0'))
        dt.R0 = float(request.args.get('R0'))
        dt.beta0 = float(request.args.get('beta0'))

        dt.update()
        msg = DesignLogMessage(user=request.remote_addr, caseid=caseid, message="Updated geometry to R={:.2f}, beta={:.2f}, a={:.2f}".format(dt.R0,dt.beta0,dt.a0))
        msg.store()

        return "Successfull" #redirect(redirect_url())
    else:
        return "Update not successfull!"

### Run Simulation ###
@dt_blueprint.route('/simulate/<string:caseid>', methods=['GET', 'POST'])
def simulate(caseid):

    dt = DigitalTwin.find_by_id(caseid)
    res = dt.simulate()

    msg = DesignLogMessage(user=request.remote_addr, caseid=caseid, message="Ran simulation")
    msg.store()

    return json.dumps(res)

### Start Optimization ###
@dt_blueprint.route('/optimize/<string:caseid>', methods=['GET', 'POST'])
def optimize(caseid):

    itermax = int(request.args.get('iterMax'))
    swarmsize =  int(request.args.get('swarmsize'))

    bounds = [(float(request.args.get('Rmin')), float(request.args.get('Rmax'))),
              (float(request.args.get('betamin')), float(request.args.get('betamax'))),
              (float(request.args.get('amin')), float(request.args.get('amax'))),
              ]

    roi = [[float(request.args.get('LiftMinOp1')), float(request.args.get('LiftMaxOp1'))],
           [float(request.args.get('LiftMinOp2')), float(request.args.get('LiftMaxOp2'))],
           [float(request.args.get('DragMinOp1')), float(request.args.get('DragMaxOp1'))], 
           [float(request.args.get('DragMinOp2')), float(request.args.get('DragMaxOp2'))],
           ]

    roitype = [int(request.args.get('isTargetLiftOp1')), int(request.args.get('isTargetLiftOp2')),
               int(request.args.get('isTargetDragOp1')), int(request.args.get('isTargetDragOp2'))]       

    constraints, targets = {}, {}
    for bnds,t,name in zip(roi, roitype, ['LiftOp1', 'LiftOp2', 'DragOp1', 'DragOp2']):
        if t==1 or t==-1:
            targets[name] = {"bounds": sorted([bnd*t for bnd in bnds]), "optidir": t}
        elif t==2:
            constraints[name] = {"bounds": bnds}

    ### Optimize ###
    dt = DigitalTwin.optimize(caseid, bounds, itermax, swarmsize, targets, constraints)

    ### Store in archive ###
    msg = DesignLogMessage(user=request.remote_addr, caseid=caseid, message="Ran optimization")
    msg.store()

    return "Optimization complete!"


### Run the digital twin ###
@dt_blueprint.route('/run/<string:caseid>')
def run(caseid):

    plots = []
    dt = DigitalTwin.find_by_id(caseid)

    ### For optimization ###
    plots.append(make_serverplot_ajax(caseid, plotnames=[['liftOP1', 'liftOP2', 'blue']], xlabel="LiftOp1", ylabel="LiftOp2", title="Lift"))
    plots.append(make_serverplot_ajax(caseid, plotnames=[['dragOP1', 'dragOP2', 'red']], xlabel="DragOp1", ylabel="DragOp2", title="Drag"))

    ### For tables ###
    return render_template('simulation/analysis/main.html', caseid=caseid, digitaltwin=dt, logmsgs=DesignLogMessage.retrieveAll(caseid), plots=plots)




### AJAX plot ####
def make_serverplot_ajax(caseid, plotnames=[['liftOP1', 'liftOP2', 'blue']], xlabel="LiftOp1", ylabel="LiftOp2", title="Lift"):

    source = AjaxDataSource(data_url=request.url_root[:-1]+url_for('simulation.server_load', caseid=caseid), polling_interval=1000)

    TOOLTIPS = [
        ("DesignID", "$index"),
        ("LiftOp1", "@liftOP1"),
        ("LiftOp2", "@liftOP2"),
        ("DragOp1", "@dragOP1"),
        ("DragOp2", "@dragOP2"),
        ("R", "@R"),
        ("beta", "@beta"),
        ("a", "@a"),
    ]

    p = figure(plot_height=300, plot_width=800, title=title, sizing_mode='scale_width',
               x_axis_label=xlabel, y_axis_label=ylabel, toolbar_location="above", 
               tooltips=TOOLTIPS)
    
    for var in plotnames:
        p.circle(var[0], var[1], source=source, color=var[2])

    #p.x_range.follow = "end"

    return components(p)


### Server to poll opti design data ###
@dt_blueprint.route('/opti_data/<string:caseid>', methods=['POST'])
def server_load(caseid):

    data = DigitalTwin.get_opti_data(caseid)

    return jsonify(liftOP1=[d["lop1"] for d in data], liftOP2=[d["lop2"] for d in data],
                   dragOP1=[d["dop1"] for d in data], dragOP2=[d["dop2"] for d in data],
                   id=[d["id"] for d in data], R=[d["R"] for d in data], a=[d["a"] for d in data],
                   beta=[d["beta"] for d in data]) 