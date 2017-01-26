from flask import Flask, request, Response, render_template
from authenticator import authenticator
from functools import wraps
from urlparse import urlparse
import json, threading, logging, pprint, Queue
import interlockcommands
from basecommands import ClientReply
from logtools import print_bytes
import requests
import random, string
from rocket import Rocket

class FlaskWebThread(threading.Thread):
    def __init__(self, queues, port, username, password):
        self.credentials = [{"username":username, "password":password}]
        self.app = Flask(__name__, static_folder='static', static_path='/static', static_url_path='/static')
        self.app.debug = False
        self.authHelper = authenticator(self.credentials)
        self.cmd_q = queues['in']
        self.reply_q = queues['out']
        self.logger = logging.getLogger('app')
        self.host = '0.0.0.0'
        self.port = port
        self.shutdown_pass = self.random_string()
        self.server = None

        rocketlog = logging.getLogger('Rocket')
        rocketlog.setLevel(logging.INFO)

        super(FlaskWebThread, self).__init__()

    def random_string(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(50))

    def admin(self):
        return render_template('admin.html')

    def sense(self):
        self.logger.debug("Got sense command")
        return self.status()

    def status(self):
        self.logger.debug("Got status command")
        command = interlockcommands.ReadState()
        response = self.sendCommand(command)
        if request.headers['Content-Type'] == 'application/json' or \
            request.headers['Accept'] == 'application/json':
            status = self.interpret_response(response.data)
            buffer = json.dumps({"status": status})
        else:
            buffer = render_template('status.html',
                                 data=print_bytes(response.data),
                                 cmd='status')
        return buffer

    def enable(self, data):
        shutdowns = data.get('shutdowns', 0)
        shutdowns = int(shutdowns)
        problems = data.get('problems', 0)
        problems = int(problems)

        self.logger.debug("Got enable command, %s shutdowns, %s problems" %
                          (shutdowns, problems))
        if shutdowns > 0:
            #command = interlockcommands.EnterState(9) #only available if keyswitch is turned
            command = interlockcommands.EnterState(4)
        elif problems > 0:
            command = interlockcommands.EnterState(4)
        else:
            command = interlockcommands.EnterState(2)

        response = self.sendCommand(command)
        if request.headers['Content-Type'] == 'application/json' or \
            request.headers['Accept'] == 'application/json':
            buffer = json.dumps({"status": "unlocked"})
        else:
            buffer = render_template('enable.html',
                                 data=print_bytes(response.data),
                                 cmd='enable')
        return buffer

    def disable(self, data):
        shutdowns = data.get('shutdowns', 0)
        shutdowns = int(shutdowns)
        problems = data.get('problems', 0)
        problems = int(problems)
        self.logger.debug("Got disable command, %s shutdowns, %s problems" %
                          (shutdowns, problems))
        if shutdowns > 0:
            command = interlockcommands.EnterState(8)
        elif problems > 0:
            command = interlockcommands.EnterState(3)
        else:
            command = interlockcommands.EnterState(1)

        response = self.sendCommand(command)
        if request.headers['Content-Type'] == 'application/json' or \
            request.headers['Accept'] == 'application/json':
            buffer = json.dumps({"status": "locked"})
        else:
            buffer = render_template('enable.html',
                                 data=print_bytes(response.data),
                                 cmd='disable')
        return buffer

    def run(self):
        self.setupRoutes()
        self.logger.debug('Flask Server Starting')
        self.server = Rocket((self.host, self.port), 'wsgi', {"wsgi_app": self.app})
        self.server.start(background=False)
        #self.app.run(host=self.host, port=self.port)
        self.logger.debug('Flask Server Stopping')

    def setupRoutes(self):
        @self.app.route('/admin', methods=['GET', 'POST'])
        @self.authHelper.requires_auth
        def admin():
            return self.admin()

        @self.app.route('/sense', methods=['GET', 'POST'])
        @self.authHelper.requires_auth
        def sense():
            return self.sense()

        @self.app.route('/status', methods=['GET', 'POST'])
        @self.authHelper.requires_auth
        def status():
            return self.status()

        @self.app.route('/enable', methods=['POST'])
        @self.authHelper.requires_auth
        def enable():
            return self.enable(request.form)

        @self.app.route('/disable', methods=['POST'])
        @self.authHelper.requires_auth
        def disable():
            return self.disable(request.form)

        @self.app.route('/unlock', methods=['POST'])
        @self.authHelper.requires_auth
        def unlock_to_enable():
            return self.enable(request.form)

        @self.app.route('/lock', methods=['POST'])
        @self.authHelper.requires_auth
        def log_to_disable():
            return self.disable(request.form)

        @self.app.route('/static', methods=['GET'])
        @self.app.route('/static/', methods=['GET'])
        @self.app.route('/', methods=['GET'])
        def serve_static_index():
            self.logger.debug('static asset')
            return self.app.send_static_file('index.html')

        @self.app.route('/swagger.yaml', methods=['GET'])
        def swagger():
            self.logger.debug('swagger yaml')
            buffer = render_template('swagger.yaml',
                                     host=request.host)
            return buffer

        @self.app.route('/shutdown/<shutdown_pass>', methods=['POST'])
        def shutdown(shutdown_pass):
            if shutdown_pass == self.shutdown_pass:
                func = request.environ.get('werkzeug.server.shutdown')
                if func is None:
                    raise RuntimeError('Not running with the Werkzeug Server')
                func()
                return "Shutting down..."
            else:
                return ""

    def sendCommand(self, command):
        self.cmd_q.put(command)
        response = self.reply_q.get(True, 5)
        if response.type == ClientReply.ERROR:
            self.logger.error(
                "ERROR response is : %s" % pprint.pformat(response))
            raise Exception(
                'Error response from interlock box: %s' % response.data)
        self.logger.debug("response is : %s" % pprint.pformat(response))
        return response

    def shutdown_flask(self):
        requests.post('http://localhost:' + str(self.port) + '/shutdown/' + self.shutdown_pass)

    def join(self):
        self.logger.debug("shutting down")
        self.server.stop()
        #self.shutdown_flask()
        self.logger.debug("shutdown request sent")
        threading.Thread.join(self)

    def interpret_response(self, data):
        unlocked_states = [2,4,5,9]
        locked_states = [1, 3, 7, 8]
        if len(data) == 2 and data[0] == 85:
            if data[1] in unlocked_states:
                return "unlocked"
            elif data[1] in locked_states:
                return "locked"
            else:
                return "unknown"
        else:
            return "unknown"

