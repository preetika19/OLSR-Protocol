from _thread import interrupt_main
from threading import Thread
from time import sleep
from sys import argv
from threading import RLock

class Topology:
    topology = dict()
    lock = RLock()
    def __init__(self, topology_file):
        self.topo = dict()
        self.sender = set()
        self.receiver = set()
        with open(topology_file, "r") as topo_file:
            for line in topo_file:
                time, status, node1, node2 = line.split()
                time = int(time)
                self.sender.add(node1)
                self.receiver.add(node2)
                if time in self.topo:
                    self.topo[time] = (self.topo[time] + [(status, node1, node2)])
                else:
                    self.topo[time] = [(status, node1, node2)]

    def add_link(self, node1, node2):
        if node1 in self.topology:
            self.topology[node1].add(node2)
        else:
            self.topology[node1] = {node2}

    def delete_link(self, node1, node2):
        try:
            self.topology[node1].remove(node2)
            if self.topology[node1] == set():
                del self.topology[node1]
        except KeyError:
            pass

    def update(self, timestamp):
        self.lock.acquire()
        try:
            for status, node1, node2 in self.topo[timestamp]:
                if status == 'UP':
                    self.add_link(node1, node2)
                    pass
                if status == "DOWN":
                    self.delete_link(node1, node2)
                    pass
        except KeyError:
            pass
        finally:
            self.lock.release()

    def get_connected_node(self, sender):
        return self.topology[sender]


class Controller:
    def __init__(self, topology_file):
        self.topology = Topology(topology_file)
        self.update_topo_thd = Thread(target=self.update_topo,args=())

    def update_topo(self):
        for i in range(125):
            self.topology.update(i)
            sleep(1)
        interrupt_main()

    def broadcast_msgs(self, destinations, message):
        for dst in destinations:
            self.unicast_msg(dst, message)

    def unicast_msg(self, destination, message):
        with open("to" + destination + ".txt", "a") as toX:
            toX.write(message)

    def forward_msg(self, destinations, message):
        if message[0] == '*':
            self.broadcast_msgs(destinations, message)
        else:
            self.unicast_msg(message[0], message)

    def senders_file(self, senders):
        file_handler = dict()
        for node in senders:
            filename = 'from' + node + '.txt'
            try:
                file = open(filename, "r")
                file.seek(0, 2)
            except IOError:
                open(filename, 'w').close()
                file = open(filename, "r")
            file_handler[node] = file
        while True:
            for node in senders:
                line = file_handler[node].readline()
                if not line:
                    continue
                yield node, line
            try:
                sleep(0.1)
            except TypeError:
                break

    def start(self):
        self.update_topo_thd.start()
        messages = self.senders_file(self.topology.sender)
        try:
            for sender, message in messages:
                self.forward_msg(self.topology.get_connected_node(sender),message)
        except KeyboardInterrupt:
            print("END.")

def main():
    if len(argv) == 1:
        c = Controller()
    else:
        c = Controller(argv[1])
    c.start()

main()
