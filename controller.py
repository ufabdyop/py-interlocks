#!/usr/bin/python
# -*- coding: utf-8 -*-
import Queue

from client import SocketClientThread
from basecommands import ClientCommand, ClientReply
import time
import pprint
import logging
import interlockcommands


class InterlockController(object):

    (DISCONNECTED, CONNECTED) = range(2)

    def __init__(self, appAliveFlag):
        self.logger = logging.getLogger('interlocks')
        self.status = InterlockController.DISCONNECTED
        self.appAliveFlag = appAliveFlag
        self.client = SocketClientThread()
        self.client.start()

    def connect(self, host, port):
        com = ClientCommand(ClientCommand.CONNECT, [host, port])
        self.logger.debug('Sending connect command: %s, %s, %s'
                          % (host, port, com.id))
        self.client.cmd_q.put(com)
        response = self.client.reply_q.get()
        self.log_response(response)
        if response.type == ClientReply.SUCCESS:
            self.status = InterlockController.CONNECTED
        return response

    def disconnect(self):
        com = ClientCommand(ClientCommand.CLOSE)
        self.logger.debug('Sending disconnect command: %s' % com.id)
        self.client.cmd_q.put(com)
        try:
            response = self.client.reply_q.get(True, 5)
            self.log_response(response)
            if response.type == ClientReply.SUCCESS:
                self.status = InterlockController.DISCONNECTED
        except Queue.Empty:
            self.logger.error("Error calling disconnect")
            pass

    def send(self, cmd):
        if self.status != InterlockController.CONNECTED:
            raise Exception('No connection for command')
        self.logger.debug('Sending command: %s' % cmd.id)
        self.client.cmd_q.put(cmd)
        response = self.client.reply_q.get(True, 5)
        self.shutdown_if_error(response)
        self.log_response(response)
        return response

    def log_response(self, response):
        if response.type == ClientReply.SUCCESS:
            self.logger.debug('got SUCCESS response (%s): '
                              % str(response.id))
        else:
            self.logger.error('got ERROR response (%s): '
                              % str(response.id))

    def shutdown_if_error(self, response):
        if response.type == ClientReply.ERROR:
            self.logger.debug('Shutting down from error communicating')
            self.appAliveFlag.clear()

    def join(self):
        self.logger.debug('Joining')
        self.client.join()

    def readSensors(self):
        cmd = interlockcommands.ReadSensors()
        return self.send(cmd)

    def enterState(self, state):
        cmd = interlockcommands.EnterState(state)
        return self.send(cmd)

    def readState(self):
        cmd = interlockcommands.ReadState()
        return self.send(cmd)

    def isConnected(self):
        cmd = interlockcommands.IsConnected()
        return self.send(cmd)

    def readMemConfig(self):
        cmd = interlockcommands.ReadMemConfig()
        return self.send(cmd)

    def loadMemConfig(self, config):
        cmd = interlockcommands.LoadMemConfig(config)
        return self.send(cmd)

    def activateMemConfig(self):
        cmd = interlockcommands.ActivateMemConfig()
        return self.send(cmd)
