#!/usr/bin/python
# -*- coding: utf-8 -*-
from basecommands import ClientCommand


class BaseInterlockCommand(ClientCommand):

    """ Use as a base for creating other interlock commands
    """

    def __init__(self, commandbytes, reply_length):
        super(BaseInterlockCommand, self).__init__(ClientCommand.SEND,
                bytearray(commandbytes))
        self.msg_len = reply_length


class ReadSensors(BaseInterlockCommand):

    """ Read A/D sensors. This command responds with 15 bytes of data
....250 10 0 
    """

    def __init__(self):
        super(ReadSensors, self).__init__([250, 10, 0], 15)


class EnterState(BaseInterlockCommand):

    """ Tell the interlock box to enter state x (1 by default)
....250 12 1 
    """

    def __init__(self, state=1):
        super(EnterState, self).__init__([250, 12, state], 1)


class ReadState(BaseInterlockCommand):

    """ Ask interlock box what state it is in (1-9)
....250 14 1 
    """

    def __init__(self, state=1):
        super(ReadState, self).__init__([250, 14, 1], 2)


class IsConnected(BaseInterlockCommand):

    """ Ask interlock box if it thinks it is connected
....Response of 1 is yes, 0 is no
....250 14 0
    """

    def __init__(self):
        super(IsConnected, self).__init__([250, 14, 0], 2)


class ReadMemConfig(BaseInterlockCommand):

    """ This asks the interlock box for its current configuration. 
....Responds with a byte that contains the configuration in the low order 4 bits. See below for a description of configurations.
....250 16 1

....Details:
....Charles modified the programming on the pic chips to make a more robust solution for our interlocking needs. The programming was necessary so that we can define custom settings for the enabled mode of each machine. For example, on our current system, if we enable a machine in coral, it signals the Hardware Server Proxy to engage the interlocking mechanism. In our system, that means turning all four relays on our relay controller card to "ON" (which we can represent as 1,1,1,1), closing the relays. However, we would like to configure it so that depending on the machine, the relays can be set to the inverse of that for an enable signal, so coral would send the enable command, Hardware Server Proxy flips the relays to (0,0,0,0). We can do this fine as our system is now, however, the keyswitch mechanism we developed will always override the machine as if it were enabled with relays of (1,1,1,1). With the new system each machine will have a configuration of four bits. Each bit represents whether its corresponding relay should be closed on enable or open on enable. If we want all 4 relays to be closed on enable, this configuration would be (0,0,0,0) or (1,1,1,1) for the inverse. Or if we want the first two relays to be closed on enable and the last two open, we use the configuration of (0,0,1,1). Of course, these are all represented as the low order 4 bits of a byte so (1,1,1,1) = 0x0F = decimal 15, (0,0,1,1) = 0x03, etc.
    """

    def __init__(self):
        super(ReadMemConfig, self).__init__([250, 16, 1], 2)


class LoadMemConfig(BaseInterlockCommand):

    """ This sends a new configuration to the interlock box. Loads config data into memory. x represents a new configuration. Just the low order 4 bits are heeded. This command responds with 85 on success, 170 on failure.
....250 18 x
    """

    def __init__(self, config=15):
        super(LoadMemConfig, self).__init__([250, 18, config], 2)


class ActivateMemConfig(BaseInterlockCommand):

    """  This makes the configuration active. This command responds with 85 on success, 170 on failure.
....250 16 2
    """

    def __init__(self):
        super(ActivateMemConfig, self).__init__([250, 16, 2], 1)
