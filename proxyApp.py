#!/usr/bin/python
# -*- coding: utf-8 -*-
from client import SocketClientThread
from basecommands import ClientCommand, ClientReply
from interlockcommands import ReadSensors
from controller import InterlockController
from timerthread import TimerThread
from flaskproxywebthread import FlaskProxyWebThread
import time
import pprint
import logging
import Queue
import threading
import sys


class ProxyInterlockApp(object):

    def __init__(self):
        FORMAT = \
            '%(asctime)-15s - %(message)s - %(levelname)s %(filename)s:%(funcName)s'
        logging.basicConfig(format=FORMAT, level=logging.DEBUG)
        self.logger = logging.getLogger('interlocks')
        self.cmd_queues = {'WEB_THREAD': {'in': Queue.Queue(),
                           'out': Queue.Queue()}}
        self.alive = threading.Event()
        self.alive.set()
        self.check_args()

    def check_args(self):
        if len(sys.argv) not in (3,):
            print("Usage:")
            print("proxyApp.py port password")
            print("eg. proxyApp.py 55009 mySecret")
            sys.exit(1)
        self.web_port = int(sys.argv[1])
        self.password = sys.argv[2]

    def run(self):
        self.start_threads()

        while self.alive.isSet():
            key = 'WEB_THREAD'
            try:
                cmd = self.cmd_queues[key]['in'].get(True, 0.1)
                self.handle(cmd, key)
            except Queue.Empty, e:
                continue
            except KeyboardInterrupt, ki:
                self.logger.debug("Got Keyboard Interrupt")
                self.alive.clear()
        self.logger.debug("Stopping Threads")
        self.stop_threads()
        self.logger.debug("Stopped")

    def start_threads(self):
        self.web = FlaskProxyWebThread(self.cmd_queues['WEB_THREAD'], self.web_port,
                                  'admin', self.password)
        self.web.start()

    def stop_threads(self):
        self.web.join()

    def handle(self, cmd, key):
        self.logger.debug("CMD, KEY: %s, %s" % (cmd, key))


app = ProxyInterlockApp()
app.run()
