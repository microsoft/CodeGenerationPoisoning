# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, render_template
from flask import send_from_directory
import os
import logging
from logging.handlers import RotatingFileHandler
import datetime
import time

app = Flask(__name__)


class Target:

    def __init__(self, name, id, point):
        self.id = id
        self.name = name
        self.player = "n"
        self.point = point

    def makeJson(self):
        json = {
            "name": self.name,
            "player": self.player,
            "point": self.point,
            # "id": self.id,
        }
        return json


class WarState:
    def __init__(self, matchtime, extendtime=60.):
        self.state = "end"
        self.players = {"r": "NoPlayer", "b": "NoPlayer"}
        self.ready = {"r": False, "b": False}
        self.scores = {"r": 0, "b": 0}
        self.targets = []

        self.passed_time = 0.
        self.init_time = None
        self.stoped_time = 0.

        self.match_time = matchtime # [sec]
        self.extend_time = extendtime # 1 minutes [sec]

    def makeJson(self):
        json = {
            "players": self.players,
            "ready": self.ready,
            "scores": self.scores,
            "state": self.state,
            "targets": [t.makeJson() for t in self.targets],
            "time": self.passed_time,
        }
        return json

    def makeCsv(self):
        '''
        convert war_state to one line string
        datetime, player_name_r, player_name_b, score_r, score_b, state, time, targets
        '''
        csv_list = ["{0:%y%m%d-%H%M%S}".format(datetime.datetime.now()),
                    str(self.players["r"]),
                    str(self.players["b"]),
                    str(self.scores["r"]),
                    str(self.scores["b"]),
                    str(self.state),
                    str(self.stoped_time),
                    ' '.join([str(t.makeJson()) for t in self.targets]),
                    ]
        csv = ','.join(csv_list)
        return csv

    def updateTime(self):
        app.logger.info("updateTime")
        if self.init_time is None:
            return False

        passed_time = self.stoped_time + (time.time() - self.init_time)
        app.logger.info("passed_Time {}".format(passed_time))

        if self.isOverMatchTime(passed_time):
            self.setStateStop()
            return True
        else:
            self.passed_time = passed_time
        return False

    def isOverMatchTime(self, passed_time):
        if passed_time > self.match_time + self.extend_time:
            return True
        elif passed_time > self.match_time:
            if self.scores['r'] == self.scores['b']:
                return False
            else:
                return True
        else:
            return False

    def setStateStop(self):
        self.state = "stop"
        self.init_time = None
        self.stoped_time = self.passed_time
        self.passed_time = 0.


class Response:
    def __init__(self):
        self.mutch = False
        self.new = False
        self.error = "yet init"
        self.target = None

    def makeJson(self):
        if self.target is None:
            target = None
        else:
            target = self.target.makeJson()
        json = {
            "mutch": self.mutch,
            "new": self.new,
            "error": self.error,
            "target": target
        }
        return json


class Referee:
    def __init__(self, matchtime, extendtime):
        self.war_state = WarState(matchtime, extendtime)

    def getWarStateJson(self):
        is_finished = self.war_state.updateTime()
        if is_finished:
            self.writeResult()
        return self.war_state.makeJson()

    def judgeTargetId(self, player_name, player_side, target_id):
        '''
        target_id must be string and length is "4"
        return "False" or "target json"
        '''
        # make Response object
        response = Response()

        # Update time and check match time
        is_finished = self.war_state.updateTime()
        if is_finished:
            self.writeResult()

        # check id length
        if not len(target_id) == 4:
            app.logger.error("ERROR target length is not 4")
            app.logger.info("player_name: " + player_name)
            app.logger.info("player_side: " + player_side)
            app.logger.info("target_id: " + target_id)
            response.error = "ERR id length is not 4"
            return response.makeJson()

        # set ready if id = 0000
        if target_id == "0000":
            self.war_state.ready[player_side] = True
            response.mutch = True
            response.error = "success set ready"
            return response.makeJson()

        # check state is running
        if self.war_state.state != "running":
            response.error = "ERR state is not running"
            return response.makeJson()

        for target in self.war_state.targets:
            if target_id == target.id:
                is_new = self.updateWarState(target, player_name, player_side)
                response.mutch = True
                response.new = is_new
                response.error = "no error"
                response.target = target

                if self.isIPPONTarget() or self.isCalledGame():
                    self.war_state.setStateStop()
                    self.writeResult()
                return response.makeJson()
        response.error = "ERR not mutch id"
        return response.makeJson()


    def isIPPONTarget(self):
        return self.war_state.scores['r'] >= 100 or self.war_state.scores['b'] >= 100

    def isCalledGame(self):
        length = abs(self.war_state.scores['r'] - self.war_state.scores['b'])
        return length >= 10

    def checkBothPlayerReady(self):
        if self.war_state.ready["r"] and self.war_state.ready["b"]:
            return True
        else:
            return False

    def updateWarState(self, target, player_name, player_side):
        # new target or not
        if not target.player == "n":
            is_new =  False
        else:
            is_new = True

        # change target player
        target.player = player_side

        # recount score
        red = 0
        blue = 0
        for target_ in self.war_state.targets:
            if target_.player == 'n':
                pass
            elif target_.player == 'b':
                blue += int(target_.point)
            elif target_.player == 'r':
                red += int(target_.point)
            else:
                app.logger.error("ERROR recount score")
        self.war_state.scores['b'] = blue
        self.war_state.scores['r'] = red

        return is_new 

    def registPlayer(self, name):
        if self.war_state.players['r'] == "NoPlayer":
            self.war_state.players['r'] = name
            ret = {"side": "r", "name": name}
        elif self.war_state.players['b'] == "NoPlayer":
            self.war_state.players['b'] = name
            ret = {"side": "b", "name": name}
        else:
            ret = "##Errer 2 player already registed"
        return ret

    def registTarget(self, name, target_id, point):
        target = Target(name, target_id, point)
        self.war_state.targets.append(target)
        return target.name

    def setState(self, state):
        app.logger.info("setState")
        if state == "end":
            self.war_state.state = state
        elif state == "running":
            if self.checkBothPlayerReady():
                self.war_state.state = state
                self.war_state.init_time = time.time()
        elif state == "stop":
            self.war_state.setStateStop
        else:
            pass
        return state

    def writeResult(self):
        result_string = self.war_state.makeCsv()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_file_path = script_dir + "/log/" + "game_result.log"
        with open(log_file_path, "a") as f:
            f.write(result_string + "\n")
        app.logger.info("Write Result {}".format(result_string))


import argparse
parser = argparse.ArgumentParser(description='burger_war judger server')
parser.add_argument('--matchtime', '--mt', default=float('inf'), type=float, help='match time [sec]')
parser.add_argument('--extendtime','--et', default=60, type=float, help='extend time [sec]')
args = parser.parse_args()

# global object referee
referee = Referee(args.matchtime, args.extendtime)

@app.route('/')
def index():
    ip = request.remote_addr
    app.logger.info("GET /(root) "+ str(ip))
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='static/')


@app.route('/submits', methods=['POST'])
def judgeTargetId():
    body = request.json
    ip = request.remote_addr
    app.logger.info("POST /submits " + str(ip) + str(body))
    player_name = body["name"]
    player_side = body["side"]
    target_id = body["id"]
    response = referee.judgeTargetId(player_name, player_side, target_id)
    res = response
    app.logger.info("RESPONSE /submits " + str(ip) + str(res))
    return jsonify(res)


@app.route('/warState', methods=['GET'])
def getState():
    ip = request.remote_addr
    #app.logger.info("GET /warState " + str(ip))
    state_json = referee.getWarStateJson()
    res = state_json
    #app.logger.info("RESPONSE /warState "+ str(ip) + str(res))
    return jsonify(res)


@app.route('/warState/players', methods=['POST'])
def registPlayer():
    body = request.json
    ip = request.remote_addr
    app.logger.info("POST /warState/players " + str(ip) + str(body))
    name = body["name"]
    ret = referee.registPlayer(name)
    res = ret
    app.logger.info("RESPONSE /warState/players " + str(ip)+ str(res))
    return jsonify(res)


@app.route('/warState/targets', methods=['POST'])
def registTarget():
    body = request.json
    ip = request.remote_addr
    app.logger.info("POST /warState/targets " + str(ip)+ str(body))
    name = body["name"]
    target_id = body["id"]
    point = body["point"]
    ret = referee.registTarget(name, target_id, point)
    res = {"name": ret}
    app.logger.info("RESPONSE /warState/targets " + str(ip)+ str(res))
    return jsonify(res)


@app.route('/warState/state', methods=['POST'])
def setState():
    body = request.json
    ip = request.remote_addr
    app.logger.info("POST /warState/state " + str(ip)+ str(body))
    state = body["state"]
    ret = referee.setState(state)
    res =  {"state": ret}
    app.logger.info("RESPONSE /warState/state " + str(ip)+ str(res))
    return jsonify(res)


@app.route('/reset', methods=['GET'])
def reset():
    ip = request.remote_addr
    app.logger.info("GET /reset " + str(ip))
    global referee
    referee = Referee(args.matchtime, args.extendtime)
    res = "reset"
    app.logger.info("RESPONSE /reset " + str(ip) + str(res) + str(args.matchtime) + str(args.extendtime))
    return jsonify(res)


@app.route('/test', methods=['GET'])
def getTest():
    ip = request.remote_addr
    app.logger.info("GET /test "+ str(ip))
    res = { "foo": "bar", "hoge": "hogehoge" }
    app.logger.info("RESPONSE /test "+ str(ip) + str(res))
    return jsonify(res)


if __name__ == '__main__':
    now = datetime.datetime.now()
    now_str = now.strftime("%y%m%d_%H%M%S")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_path = script_dir + "/log/" + now_str + ".log"
    handler = RotatingFileHandler(log_file_path, maxBytes = 1000000, backupCount=100)
    handler.setLevel(logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.run(debug=True, host='0.0.0.0', port=5000)

