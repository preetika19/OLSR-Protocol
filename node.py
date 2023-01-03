from clock import Clock
from route import Route
from concurrent.futures import ThreadPoolExecutor
from sys import argv
from time import sleep

class Node:
    threads = ThreadPoolExecutor(max_workers=10)
    clock_time = Clock()
    hello_format = '* {} HELLO UNIDIR {} BIDIR {} MPR {}\n'
    tc_format = '* {} TC {} {} MS {}\n'
    data_format = '{} {} DATA {} {} {}\n'
    msg_queue = None
    kill = False

    def __init__(self, node_id, dst=None, msg=None, timestamp=None):
        self.nid = node_id
        self.dst = dst
        self.msg = msg
        self.timestamp = timestamp
        self.fromfilename = 'from' + self.nid + '.txt'
        self.tofilename = 'to' + self.nid + '.txt'
        self.receivefilename = self.nid + 'received.txt'
        self.process_msgs = {'HELLO': self.receive_hello,'TC': self.receive_tc,'DATA': self.receive_data}
        self.stored_msgs = dict()
        self.route_list = Route(node_id)

    def stored_msgs_reset(self):
        self.stored_msgs = dict()

    @property
    def get_time(self):
        return self.clock_time.time

    def get_tick(self):
        self.clock_time.tick()

    def send_hello(self):
        sender = self.nid
        unidir = ' '.join(map(str, self.route_list.unidir))
        bidir = ' '.join(map(str, self.route_list.bidir))
        mpr = ' '.join(map(str, self.route_list.mpr))
        hello = self.hello_format.format(sender, unidir, bidir, mpr)
        with open(self.fromfilename, 'a') as from_me:
            from_me.write(hello)

    def send_tc(self):
        sender = self.nid
        source = self.nid
        seqno = self.route_list.ms_seqno
        ms = ' '.join(map(str, self.route_list.ms))
        tc = self.tc_format.format(sender, source, seqno, ms)
        with open(self.fromfilename, 'a') as from_me:
            from_me.write(tc)

    def send_data(self):
        next_hop = self.route_list.get_route(self.dst)
        if next_hop:
            sender = self.nid
            originator = self.nid
            dst = self.dst
            msg = self.msg
            data = self.data_format.format(next_hop, sender, originator, dst, msg)
            with open(self.fromfilename, 'a') as from_me:
                from_me.write(data)
        else:
            self.timestamp += 30

    def timeout_check(self):
        self.route_list.check_timeout()

    def processor_msgs(self):
        for msg in self.msg_queue:
            self.process_msgs[msg.split(' ')[2]](msg)
            if self.kill:
                break

    def get_files(self):
        try:
            open(self.tofilename, 'r').close()
        except IOError:
            open(self.tofilename, 'w').close()
        with open(self.tofilename, 'r') as to_me:
            to_me.seek(0, 2)
            while not self.kill:
                line = to_me.readline()
                if not line:
                    sleep(0.1)
                    continue
                yield line

    def receive_hello(self, msg):
        with open(self.receivefilename, 'a') as received:
            received.write(msg)
        msg = msg[:-1]
        neighbour = msg[2]
        unidir, rest = msg.split('UNIDIR ')[1].split(' BIDIR ')
        bidir, mpr = rest.split(' MPR ')
        to_set = lambda x: set() if x == '' else set(x.split(' '))
        self.route_list.hello_update(neighbour,to_set(unidir),to_set(bidir),to_set(mpr))

    def receive_tc(self, msg):
        with open(self.receivefilename, 'a') as received:
            received.write(msg)
        msg = msg[:-1]
        neighbour = msg[2]
        s, ms = msg.split(' TC ')[1].split(' MS ')
        source, seqno = s.split(' ')
        if source == self.nid:
            return
        try:
            if self.stored_msgs[source] >= seqno:
                return
        except KeyError:
            pass
        finally:
            self.stored_msgs[source] = seqno
        to_set = lambda x: set() if x == '' else set(x.split(' '))
        self.route_list.tc_update(source, to_set(ms), int(seqno))
        if self.route_list.mpr_of(neighbour):
            tc = self.tc_format.format(self.nid, source, seqno, ms)
            with open(self.fromfilename, 'a') as from_me:
                from_me.write(tc)

    def receive_data(self, msg):
        with open(self.receivefilename, 'a') as received:
            received.write(msg)
        msg_list = msg[:-1].split(' ')
        if self.nid == msg_list[4]:
            return
        next_hop = self.route_list.get_route(msg_list[4])
        if next_hop:
            new_msg = ' '.join([next_hop, self.nid] + msg_list[2:]) + '\n'
            with open(self.fromfilename, 'a') as from_me:
                from_me.write(new_msg)
        else:
            pass

    def start(self):
        self.msg_queue = (self.threads.submit(self.get_files)).result()
        self.threads.submit(self.processor_msgs)
        while self.get_time <= 120:
            self.threads.submit(self.timeout_check)
            if self.get_time == self.timestamp:
                self.threads.submit(self.send_data)
            if self.get_time % 5 == 0:
                self.threads.submit(self.send_hello)
            if self.get_time % 10 == 8:
                self.threads.submit(self.stored_msgs_reset)
            if self.get_time % 10 == 0 and self.route_list.ms:
                self.threads.submit(self.send_tc)
            sleep(1)
            self.get_tick()
        self.kill = True
        sleep(1)

def main():
    if len(argv) == 5:
        c = Node(argv[1], argv[2], argv[3], int(argv[4]))
    else:
        c = Node(argv[1])
    c.start()
    print("Node", argv[1], "finished.")

main()
