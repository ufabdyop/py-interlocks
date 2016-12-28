#!/usr/bin/python
# -*- coding: utf-8 -*-
import socket
import logging
import struct
import threading
import Queue
import pprint
from basecommands import ClientCommand, ClientReply
from logtools import print_bytes


class SocketClientThread(threading.Thread):

    """ Implements the threading.Thread interface (start, join, etc.) and
        can be controlled via the cmd_q Queue attribute. Replies are
        placed in the reply_q Queue attribute.
    """

    def __init__(self, cmd_q=None, reply_q=None):
        super(SocketClientThread, self).__init__()
        self.cmd_q = cmd_q or Queue.Queue()
        self.reply_q = reply_q or Queue.Queue()
        self.alive = threading.Event()
        self.alive.set()
        self.socket = None
        self.logger = logging.getLogger('app')

        self.handlers = {ClientCommand.CONNECT: self._handle_CONNECT,
                         ClientCommand.CLOSE: self._handle_CLOSE,
                         ClientCommand.SEND: self._handle_SEND}

    def run(self):
        while self.alive.isSet():
            try:
                # Queue.get with timeout to allow checking self.alive
                cmd = self.cmd_q.get(True, 0.1)
                self.handlers[cmd.type](cmd)
            except Queue.Empty, e:
                continue

    def join(self, timeout=None):
        self.alive.clear()
        threading.Thread.join(self, timeout)

    def _handle_CONNECT(self, cmd):
        try:
            self.socket = socket.socket(socket.AF_INET,
                    socket.SOCK_STREAM)

            self.socket.settimeout(5.0)
            self.socket.connect((cmd.data[0], cmd.data[1]))
            self.reply_q.put(self._success_reply(cmd=cmd))
        except IOError, e:
            self.reply_q.put(self._error_reply(str(e), cmd=cmd))

    def _handle_CLOSE(self, cmd):
        self.socket.close()
        reply = self._success_reply(cmd=cmd)
        self.reply_q.put(reply)

    def _handle_SEND(self, cmd):
        try:
            self.logger.debug('sending bytes %s'
                              % print_bytes(cmd.data))
            self.socket.sendall(cmd.data)
            self._handle_RECEIVE(cmd)
        except IOError, e:
            self.reply_q.put(self._error_reply(str(e), cmd=cmd))

    def _handle_RECEIVE(self, cmd):
        try:
            data = self._recv_min(cmd.msg_len)
            self.logger.debug('got response bytes %s'
                              % print_bytes(bytearray(data)))
            if len(data) == cmd.msg_len:
                self.reply_q.put(self._success_reply(bytearray(data),
                                 cmd=cmd))
                return
            self.logger.error('Expected %s bytes, but got %s bytes'
                              % (cmd.msg_len, len(data)))
            reply_msg = 'Socket closed prematurely: %s' \
                % bytearray(data)
            reply = self._error_reply(reply_msg, cmd=cmd)
            self.reply_q.put(reply)
        except IOError, e:
            self.reply_q.put(self._error_reply(str(e), cmd=cmd))

    def _error_reply(self, errstr, cmd=None):
        return ClientReply(ClientReply.ERROR, errstr, cmd.id)

    def _success_reply(self, data=None, cmd=None):
        return ClientReply(ClientReply.SUCCESS, data, cmd.id)

    def _recv_min(self, length):
        data = self.socket.recv(length)
        buffer = ''
        buffer += data
        while (len(buffer) < length) and self.alive.isSet():
            data = self.socket.recv(length - len(buffer))
            buffer += data

        return buffer
