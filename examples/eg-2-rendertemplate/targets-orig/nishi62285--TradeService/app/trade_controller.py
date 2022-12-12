from flask import Blueprint,render_template,request,url_for,redirect
from app.trade_form import REGIONBForm
trade_bp = Blueprint('trade_bp',__name__, template_folder='templates', url_prefix='/trade')
from run import application
from app import trade_util
from app.trade_util import TradeUtil
logger=application.config['logger']
trade_util=TradeUtil.getinstance()
# from blinker import Namespace
# sig=Namespace()
# custom_signal=sig.signal('custom_signal')

# def log_template_renders(sender,template,context,**app):
#     sender.logger.debug(template.name)

# @custom_signal.connect
# def process_received(app,**args):
#     a=args.get('id')
#     pass

#template_rendered.connect(log_template_renders,app)

# @mliosa_bp.before_request
# def check_access():
#     if not trade_util.check_entitlement():
#         render_template('error.html')

@application.route('/')
def healthcheck():
    return 'runing'

@trade_bp.route('/sendtrade',methods=['POST','GET'])
def put_trade():
    form_data=REGIONBForm()
    return render_template('put_trade.html',form=form_data)

@trade_bp.route('/processtrade',methods=['POST'])
def processtrade():
    form_data = REGIONBForm()
    if form_data.validate_on_submit():
       id=trade_util.process_trade(request.form)
       if id != '0':
           return redirect(url_for('trade_bp.getmli'))
       return redirect(url_for('trade_bp.getmli'))
    return render_template('put_trade.html', form=form_data)

@trade_bp.route('/error')
def error():
    return render_template('error.html')

@trade_bp.app_template_filter()
def formattext(str1):
    return str(str1) + "formatted!!"

@trade_bp.route('/gettrades',methods=['GET'])
def getmli():
    #custom_signal.send(current_app._get_current_object(),id=123)
    logger.info('fetching trades..')
    trades= trade_util.get_all_trades()
    return render_template('trade.html',data=trades)

@trade_bp.route('/get/<id>')
def getId(id):
    print(request.view_args)
    return str(id)
