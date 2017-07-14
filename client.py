import time
import timeit as ti
import uuid
import zmq
from helper import Proto, switch

# Globals
g_zmqhwm = 100

class Client():
    # client registration string

    def __init__(self, server_port):
        context = zmq.Context().instance()
        self.socket = context.socket(zmq.DEALER)
        # generate a universally unique client ID
        self.id = uuid.uuid4()
        self.socket.setsockopt(zmq.IDENTITY, str(self.id))
        self.socket.setsockopt(zmq.SNDHWM, g_zmqhwm)
        self.socket.setsockopt(zmq.RCVHWM, g_zmqhwm)
        self.socket.connect("tcp://localhost:%s" % server_port)
        # set up a read poller
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)
        self.svr_connect = False

        # send connection message that will register server with client
        print "Connecting to server..."
        self.send(Proto.greet)
        # blocking read
        msg = self.socket.recv()
        self.parseMsg(msg)

        print "Client: " + str(self.id) + " connected to port: " + str(server_port)

    def run(self):
        print "Client: start run"

        # Client's idle loop
        timeout = 1
        total = 0
        while True:
            # Read incoming
            sockets = dict(self.poller.poll(timeout))
            if self.socket in sockets and sockets[self.socket] == zmq.POLLIN:
                msg = self.socket.recv()
                total += 1
                if not self.parseMsg(msg):
                    break

            if self.svr_connect:
                # Send outgoing
                work = b"workload" + str(total)
                self.send(Proto.str, work)

        print("Client: total messages received: %s" % total)
        print "Client: end run"
        self.socket.close()

    def send(self, proto, data = b''):
        try:
            if not self.socket.send(proto + data, zmq.NOBLOCK) == None:
                print "Client: socket send failed"
        except zmq.ZMQError:
            print "Client: socket send failed, disconnecting"
            self.svr_connect = False

    def parseMsg(self, msg):
        ret = True
        header = msg[0:Proto.headerlen]
        body = msg[Proto.headerlen:]
        for case in switch(header):
            if case(Proto.greet):
                print "Client: server greet"
                self.svr_connect = True
                break
            if case(Proto.str):
                print "Client: string: " + body
                break
            if case(Proto.serverstop):
                print "Client: serverstop"
                # Send reply to delete client
                self.svr_connect = False
                self.send(Proto.clientstop)
                ret = False
                break
            if case():  # default
                print "Client: received undefined message!"
                # TODO: debug
        return ret