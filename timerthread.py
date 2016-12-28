#!/usr/bin/python
# -*- coding: utf-8 -*-
import threading, sys
import time
import interlockcommands
import logging
import traceback

class TimerThread(threading.Thread):

    TIME_BETWEEN_SENSES = 30

    """ Implements the threading.Thread interface (start, join, etc.) and
    """

    def __init__(self, queues, appAliveFlag):
        super(TimerThread, self).__init__()
        self.cmd_q = queues['in']
        self.reply_q = queues['out']
        self.alive = threading.Event()
        self.alive.set()
        self.appAliveFlag = appAliveFlag
        self.logger = logging.getLogger('app')

    def run(self):
        counter = 0
        while self.alive.isSet():
            counter += 2
            time.sleep(2)

            if counter % TimerThread.TIME_BETWEEN_SENSES == 0:
                counter = 0
                command = interlockcommands.ReadSensors()
                try:
                  self.logger.debug("Sending sense command")
                  self.cmd_q.put(command)
                  response = self.reply_q.get(True, 5)
                except Exception as e:
                  self.logger.error("exception while communicating with sensors")
                  self.logger.error( traceback.format_exception_only(type(e), e) )
                  self.appAliveFlag.clear()
                  self.alive.clear()
        self.logger.debug("Shutting down timerthread")

    def handler(self):
        pass

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)
