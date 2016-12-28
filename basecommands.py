#!/usr/bin/python
# -*- coding: utf-8 -*-
import uuid


class ClientCommand(object):

    """ A command to the client thread.
        Each command type has its associated data:

        CONNECT:    (host, port) tuple
        SEND:       Data string
        RECEIVE:    None
        CLOSE:      None
    """

    (CONNECT, SEND, CLOSE) = range(3)

    def __init__(
        self,
        type,
        data=None,
        id=None,
        ):
        self.type = type
        self.data = data
        self.id = id
        if id == None:
            self.id = uuid.uuid4()


class ClientReply(object):

    """ A reply from the client thread.
        Each reply type has its associated data:

        ERROR:      The error string
        SUCCESS:    Depends on the command - for RECEIVE it's the received
                    data string, for others None.
    """

    (ERROR, SUCCESS) = range(2)

    def __init__(
        self,
        type,
        data=None,
        id=None,
        ):
        self.type = type
        self.data = data
        self.id = id
