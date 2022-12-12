from flask import Flask, render_template, request, json
import logging
import socket


if "RPI" in socket.gethostname().upper():
    from libs.servocontrol import servocontroller as sc

def configure_logging():
    """ Configures the logging for this application"""
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s %(name)s %(levelname)s %(message)s',
                        filename='app.log',
                        filemode='w')
    
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/hello' )
def hello():
    return render_template('hello.html')


@app.route('/gimbal')
def gimbalcontrol():
    return render_template('gimbalcontrol.html')


@app.route('/postValues')
def post_values():
    
    left_right = request.args.get('left_right') # if request.args.get('left_right') else None
    up_down = request.args.get('up_down') #if request.args.get('up_down') else None
    click = request.args.get('click')

    #logging.debug(f"left_right: {left_right}")
    #logging.debug(f"up_down: {up_down}")
    #logging.debug(f"click: {click}")

    servo_positions = {'left_right':left_right,
                    'up_down':up_down, 
                    'click':click
                    }
    
    print(servo_positions)
    #logging.debug(servo_positions)
    sc.set_servo(servo_positions)

    return json.dumps({'status':'OK'})


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    configure_logging()
    app.run(debug=True,port=1080,host="0.0.0.0")
