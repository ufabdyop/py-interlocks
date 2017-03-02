from flask import Flask, request, Response, render_template
from authenticator import authenticator
from functools import wraps
from urlparse import urlparse
import json, threading, logging, pprint, Queue
import interlockcommands
from basecommands import ClientReply
from logtools import print_bytes
import requests
from requests.auth import HTTPBasicAuth
import random, string
from rocket import Rocket

class FlaskProxyWebThread(threading.Thread):
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

        super(FlaskProxyWebThread, self).__init__()

    def random_string(self):
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(50))

    def proxy(self, data):
        #verify
        shutdowns = data.get('shutdowns', 0)
        shutdowns = int(shutdowns)
        problems = data.get('problems', 0)
        problems = int(problems)
        scheme = data.get('scheme', 'http')
        host = data['host']
        port = data['port']
        username = data.get('username', self.credentials[0]['username'])
        password = data.get('password', self.credentials[0]['password']) #since this method requires authentication, this should be okay
        command = data['command']

        if command not in ["status", "sense", "enable", "disable", "unlock", "lock"]:
            return Response(
                '{"status": "error", "message": "no such command"}', 404)

        if scheme not in ["http", "https"]:
            return Response(
                '{"status": "error", "message": "no such scheme"}', 404)

        headers = {'Content-type': 'application/json'}
        json_data = {"shutdowns": shutdowns, "problems": problems}
        url = '%s://%s:%s/%s' % (scheme, host, port, command)
        auth = HTTPBasicAuth(username, password)
        self.logger.debug("Proxying request: %s, %s, %s, %s" % (url, command, shutdowns, problems))
        response = requests.post(url, data=json_data, headers=headers, auth=auth)
        self.logger.debug("Got response code %s " % response.status_code)
        return Response(response.text, response.status_code)

    def is_json(self):
        self.logger.debug("IS JSON?")
        self.logger.debug("Accept header: " + request.headers.get("Accept", ""));
        self.logger.debug("Content-Type header: " + request.headers.get("Content-Type", ""));
        json = False

        if request.headers.get('Content-Type', False) == 'application/json' or \
            request.headers.get('Accept', False) == 'application/json':
            json = True
        return json

    def run(self):
        self.setupRoutes()
        self.logger.debug('Flask Proxy Server Starting')
        self.server = Rocket((self.host, self.port), 'wsgi', {"wsgi_app": self.app})
        self.server.start(background=False)
        #self.app.run(host=self.host, port=self.port)
        self.logger.debug('Flask Server Stopping')

    def setupRoutes(self):
        @self.app.route('/static', methods=['GET'])
        @self.app.route('/static/', methods=['GET'])
        @self.app.route('/', methods=['GET'])
        def serve_static_index():
            self.logger.debug('static asset')
            return self.app.send_static_file('index.html')

        @self.app.route('/swagger.yaml', methods=['GET'])
        def swagger():
            self.logger.debug('swagger yaml')
            buffer = render_template('swaggerProxy.yaml',
                                     host=request.host)
            return buffer

        @self.app.route('/proxy', methods=['POST'])
        @self.authHelper.requires_auth
        def proxy():
            return self.proxy(request.get_json())

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

    def shutdown_flask(self):
        requests.post('http://localhost:' + str(self.port) + '/shutdown/' + self.shutdown_pass)

    def join(self):
        self.logger.debug("shutting down")
        self.server.stop()
        self.logger.debug("shutdown request sent")
        threading.Thread.join(self)
