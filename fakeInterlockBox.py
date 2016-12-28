import socket, pprint, time
from logtools import print_bytes

class FakeInterlockBox(object):
    KEYSTATES = ("normal", "service", "lockout")
    NORMAL=0
    SERVICE=1
    LOCKOUT=2
    CMDSIZE = 3

    def __init__(self, host='', port=2101):
        self.host = host
        self.port = port
        self.state = 1
        self.keystate = self.NORMAL

        self.addr = (self.host,self.port)
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.bind(self.addr)
        self.serverSocket.listen(30)

    def recvMin(self, socket, length):
        data = socket.recv(length)
        buffer = ''
        buffer += data
        while len(buffer) < length:
            data = socket.recv(length - len(buffer))
            buffer += data

        return buffer

    def printState(self):
        print("STATE: %s, KEY: %s" % (self.state,
                                      self.KEYSTATES[self.keystate]))

    def handleChangeState(self, byteCode):
        response = chr(85)
        print ('COMMAND: CHANGE STATE')
        if self.keystate == self.NORMAL:
            response = self.handleChangeStateNormal(byteCode)
        elif self.keystate == self.SERVICE:
            response = self.handleChangeStateService(byteCode)
        elif self.keystate == self.LOCKOUT:
            response = self.handleChangeStateLockout(byteCode)
        else:
            response = chr(85) + chr(62)

        return response

    def handleChangeStateNormal(self, byteCode):
        if byteCode in [1,2,3,4,6,8]:
            self.state = byteCode
            return chr(85)
        else:
            return chr(85) + chr(62)

    def handleChangeStateService(self, byteCode):
        if byteCode in [5,6,8,9]:
            self.state = byteCode
            return chr(85)
        else:
            return chr(85) + chr(62)

    def handleChangeStateLockout(self, byteCode):
        if byteCode in [7,8]:
            self.state = byteCode
            return chr(85)
        else:
            return chr(85) + chr(62)

    def handleChangeKey(self, byteCode):
        print ('COMMAND: CHANGE KEY POSITION')
        oldkeystate = self.keystate
        if byteCode in [self.NORMAL, self.SERVICE, self.LOCKOUT]:
            self.keystate = byteCode
        if oldkeystate != self.keystate:
            if keystate == self.NORMAL:
                self.handleChangeState(1)
            elif keystate == self.SERVICE:
                self.handleChangeState(5)
            elif keystate == self.LOCKOUT:
                self.handleChangeState(8)
        response = chr(85)
        return response

    def handleReadSensors(self):
        print ('COMMAND: READ SENSORS')
        if self.keystate == self.NORMAL:
            response = '550100000000000000000000000000'.decode('hex')
        elif self.keystate == self.SERVICE:
            response = '550000000000000000000000000000'.decode('hex')
        elif self.keystate == self.LOCKOUT:
            response = '550001000000000000000000000000'.decode('hex')
        else:
            response = '550000000000000000000000000000'.decode('hex')
        return response

    def handleCheckConnectionStatus(self):
        print 'COMMAND: CHECK CONNECTION STATUS'
        response = chr(85) + chr(1)
        return response

    def handleCheckState(self):
        print 'COMMAND: CHECK STATE'
        response = chr(85) + chr(self.state)
        return response

    def handleRequest(self, data):
        if data == chr(250) + chr(10) + chr(0):  # read sensors:
            response = self.handleReadSensors()
        elif data[0] == chr(250) and data[1] == chr(12):  # enter state
            response = self.handleChangeState(ord(data[2]))
        elif data == chr(250) + chr(14) + chr(0):  # read current state:
            response = self.handleCheckConnectionStatus()
        elif data == chr(250) + chr(14) + chr(1):  # read current state:
            response = self.handleCheckState()
        elif data[0] == chr(250) and data[1] == chr(25):  # move key (not actual command)
            response = self.handleChangeKey(ord(data[2]))
        else:
            print "Unable to parse command"
            response = chr(85)
        return response

    def main(self):
        print ("LISTENING FOR CONNECTIONS ON %s:%s" % (self.host, self.port))
        while True:
            self.conn, self.addr = self.serverSocket.accept()
            print 'client connected ... ', self.addr

            while True:
                data = self.recvMin(self.conn, FakeInterlockBox.CMDSIZE)
                if not data: continue
                print "\n--> Received Bytes: %s" % print_bytes(bytearray(data))
                response = self.handleRequest(data)
                print '<-- Sending Bytes: %s' % print_bytes(bytearray(response))
                self.conn.sendall(response)
                self.printState()

            self.conn.close()
        self.conn.close()

box = FakeInterlockBox()
box.main()
