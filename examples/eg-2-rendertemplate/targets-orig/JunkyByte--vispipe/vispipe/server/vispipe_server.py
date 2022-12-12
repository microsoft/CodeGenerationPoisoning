from ..vispipe import Pipeline
from flask_socketio import SocketIO
from threading import Thread, Event
from flask import Flask, render_template, session
from .server_gui import CursesQueueGUI
from itertools import chain
from collections import defaultdict
import numpy as np
import traceback
import os
import logging
import time
log = logging.getLogger('vispipe.server')
log.setLevel(logging.DEBUG)
app = Flask(__name__)
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = os.urandom(16)
socketio = SocketIO(app, async_mode=None, logger=False, engineio_logger=False)


class Server:
    gui_thread = Thread()
    vis_thread = Thread()
    vis_thread.daemon = True
    vis_thread_stop_event = Event()
    qsize_thread_stop_event = Event()
    SESSION_TYPE = 'redis'

    def __init__(self, PATH_CKPT='./scratch_test.pickle', slow=True, use_curses=True):
        self.pipeline = Pipeline()
        self.pipeline.vis_mode = True

        self.PATH_CKPT = PATH_CKPT
        self.slow = slow
        self.vis_data = None
        self.update = True
        socketio.on_event('new_node', self.new_node)
        socketio.on_event('remove_node', self.remove_node)
        socketio.on_event('new_conn', self.new_conn)
        socketio.on_event('set_custom_arg', self.set_custom_arg)
        socketio.on_event('set_name', self.set_name)
        socketio.on_event('set_output', self.set_output)
        socketio.on_event('set_macro', self.set_macro)
        socketio.on_event('run_pipeline', self.run_pipeline)
        socketio.on_event('stop_pipeline', self.stop_pipeline)
        socketio.on_event('clear_pipeline', self.clear_pipeline)
        socketio.on_event('save_nodes', self.save_nodes)
        socketio.on_event('connect', self.connect)
        socketio.on_event('disconnect', self.disconnect)

        self.gui = None
        if use_curses and os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            self.gui = CursesQueueGUI()
            if not self.gui_thread.isAlive():
                logging.info('Launching terminal queue visualization')
                self.gui_thread = Thread(target=self.set_qsize)
                self.gui_thread.daemon = True
                self.gui_thread.start()
            time.sleep(1)

        socketio.run(app)

    @app.route('/')
    def index():
        session['test_session'] = 42
        return render_template('index.html')

    @app.route('/get/')
    def show_session():
        log.info(session['test_session'])
        return '%s' % session.get('test_session')

    def share_blocks(self):
        for block in self.pipeline.get_blocks(serializable=True):
            socketio.emit('new_block', block)
        socketio.emit('end_block', None)

    def new_node(self, block):
        try:
            log.info('New node')
            node_hash = hash(self.pipeline.add_node(block['name']))
            return {'id': node_hash}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def remove_node(self, node_hash):
        try:
            log.info('Removing node')
            self.pipeline.remove_node(node_hash)
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def new_conn(self, x):
        try:
            self.pipeline.add_conn(x['from_hash'], x['out_idx'], x['to_hash'], x['inp_idx'])
            self.update = True
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def set_custom_arg(self, data):
        try:
            log.debug('Setting node %s arg %s to value %s' % (data['id'], data['key'], data['value']))
            node = self.pipeline.get_node(data['id'])
            node.set_custom_arg(data['key'], data['value'])
            self.update = True
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def set_name(self, data):
        try:
            log.debug('Setting node %s name to value %s' % (data['id'], data['name']))
            self.pipeline.get_node(data['id']).name = data['name']
            self.update = True
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def set_output(self, data):
        try:
            node_hash = data['id']
            log.debug('Setting output %s' % node_hash)
            if data['state']:
                self.pipeline.add_output(node_hash)
            else:
                self.pipeline.remove_output(node_hash)
            self.update = True
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def set_macro(self, data):
        try:
            if data['state']:
                edges = self.pipeline.add_macro(data['from_id'], data['to_id'])
            else:
                edges = self.pipeline.remove_macro(data['from_id'])
            return {'edges': edges}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def send_vis(self, vis_thread_stop_event):
        while not vis_thread_stop_event.isSet():
            try:
                vis = self.pipeline.runner.read_vis()
                shape = None
                for node_hash, value in vis.items():
                    node = self.pipeline.get_node(int(node_hash))
                    if node.block.data_type == 'plot':
                        img = np.frombuffer(value.canvas.tostring_rgb(), dtype=np.uint8)
                        value = img.reshape(value.canvas.get_width_height()[::-1] + (3,))
                    if node.block.data_type in ['image', 'plot']:
                        shape = value.shape
                        value = np.reshape(value, (-1,)).tolist()
                    elif node.block.data_type == 'raw':
                        if isinstance(value, (np.ndarray, list)):
                            try:
                                value = np.around(value, 2)
                            except Exception:
                                log.warning('The value is a numpy array or list that is not roundable')
                        elif isinstance(value, float):
                            value = round(value, 2)
                        value = str(value)

                    socketio.emit('send_vis', {**{'id': node_hash, 'value': value, 'shape': shape}, **node.block.serialize()})
            except Exception as e:
                log.error(traceback.format_exc())
                socketio.emit('message', str(e))
            socketio.sleep(0.5)

    def set_qsize(self):
        while True:
            try:
                values = self.pipeline.read_qsize()
                for h, name, q, qmax in values:
                    self.gui.set_queues(h, name, q, qmax)
                self.gui.clear_queues()
            except Exception:
                log.error(traceback.format_exc())
            time.sleep(1)

    def run_pipeline(self):
        try:
            self.pipeline.run(slow=self.slow, use_mp=False)
            self.vis_thread_stop_event.clear()
            if not self.vis_thread.isAlive():
                self.vis_thread = socketio.start_background_task(self.send_vis,
                                                                 self.vis_thread_stop_event)
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500
        return 'Invalid State Encountered', 500

    def stop_pipeline(self):
        try:
            self.vis_thread_stop_event.set()
            self.pipeline.stop()
            if self.vis_thread.isAlive():
                self.vis_thread.join()
            return {}, 200
        except Exception as e:
            return str(e), 500

    def clear_pipeline(self):
        try:
            self.stop_pipeline()
            self.pipeline.clear_pipeline()
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def save_nodes(self, vis_data):
        try:
            if vis_data == self.vis_data and not self.update:
                log.info('Checkpoint skipped, there are no changes')
                return {}, 200

            self.pipeline.save(self.PATH_CKPT, vis_data)
            self.vis_data = vis_data
            log.info('Saved checkpoint automatically')
            self.update = False
            return {}, 200
        except Exception as e:
            log.error(traceback.format_exc())
            return str(e), 500

    def load_checkpoint(self, path):
        if not os.path.isfile(path):
            return

        self.vis_data = self.pipeline.load(path, vis_mode=True)
        macros = list(chain.from_iterable(self.pipeline.macro))
        pipeline_def = defaultdict(list)
        for node in self.pipeline.nodes:
            n_hash = hash(node)
            value = (n_hash, n_hash in self.pipeline._outputs, n_hash in macros, node.name)
            pipeline_def['nodes'].append(value)
            conn = self.pipeline.connections(n_hash, out=True)
            pipeline_def['connections'].append([(hash(n), i, j) for n, i, j, _ in conn])
            pipeline_def['blocks'].append(node.block.serialize())
            pipeline_def['custom_args'].append(node.block.serialize_args(node.custom_args))
        socketio.emit('load_checkpoint', {'vis_data': self.vis_data, 'pipeline': pipeline_def})

    def connect(self):
        log.warning('Client connected')
        self.pipeline.clear_pipeline()

        log.info('Sharing blocks')
        self.share_blocks()

        log.info('Loading checkpoint from %s' % self.PATH_CKPT)
        self.load_checkpoint(self.PATH_CKPT)

        socketio.emit('set_auto_save', True)

    def disconnect(self):
        log.warning('Client disconnected')


if __name__ == '__main__':
    Server()
