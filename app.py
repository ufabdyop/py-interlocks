#!/usr/bin/python
# -*- coding: utf-8 -*-
from client import SocketClientThread
from basecommands import ClientCommand, ClientReply
from interlockcommands import ReadSensors
from controller import InterlockController
from timerthread import TimerThread
from flaskwebthread import FlaskWebThread
import time
import pprint
import logging
import Queue
import threading
import sys


class InterlockApp(object):

    STEPTIME = 1  # number of seconds between each run through event loop
    SECONDS_BETWEEN_SENSE = 30  # number of seconds between each request to get sensor readings
    PORT = 2101

    def __init__(self):
        FORMAT = \
            '%(asctime)-15s - %(message)s - %(levelname)s %(filename)s:%(funcName)s'
        logging.basicConfig(format=FORMAT, level=logging.DEBUG)
        self.logger = logging.getLogger('interlocks')
        self.cmd_queues = {'WEB_THREAD': {'in': Queue.Queue(),
                           'out': Queue.Queue()},
                           'TIMER_THREAD': {'in': Queue.Queue(),
                           'out': Queue.Queue()}}
        self.alive = threading.Event()
        self.alive.set()
        self.check_args()

    def check_args(self):
        if len(sys.argv) != 4:
            print("Usage:")
            print("app.py interlockbox-ip port password")
            print("eg. app.py 10.0.0.5 55009 mySecret")
            sys.exit(1)
        self.interlock_host = sys.argv[1]
        self.web_port = int(sys.argv[2])
        self.password = sys.argv[3]

    def run(self):
        self.controller = InterlockController(self.alive)
        response = self.controller.connect(self.interlock_host,
                                InterlockApp.PORT)
        if response.type == ClientReply.ERROR:
            self.logger.error("Could not connect")
            sys.exit(1)

        self.start_threads()

        while self.alive.isSet():
            for key in ['WEB_THREAD', 'TIMER_THREAD']:
                try:
                    cmd = self.cmd_queues[key]['in'].get(True, 0.1)
                    self.handle(cmd, key)
                except Queue.Empty, e:
                    continue
                except KeyboardInterrupt, ki:
                    self.logger.debug("Got Keyboard Interrupt")
                    self.alive.clear()
        self.logger.debug("Disconnecting")
        self.controller.disconnect()
        self.logger.debug("Stopping Threads")
        self.stop_threads()
        self.logger.debug("Stopped")

    def handle(self, cmd, queue):
        resp = self.controller.send(cmd)
        self.cmd_queues[queue]['out'].put(resp)

    def start_threads(self):
        self.timer = TimerThread(self.cmd_queues['TIMER_THREAD'], self.alive)
        self.web = FlaskWebThread(self.cmd_queues['WEB_THREAD'], self.web_port,
                                  'admin', self.password)
        self.timer.start()
        self.web.start()

    def stop_threads(self):
        self.controller.join()
        self.timer.join()
        self.web.join()


app = InterlockApp()
app.run()
