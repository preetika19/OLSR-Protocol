from copy import deepcopy
from threading import RLock
from clock import Clock
class Route:
    lock = RLock()
    timeout_neighbour = 15
    timeout_tc = 30

    def __init__(self, nid):
        self.nid = nid
        self.unidir = set()
        self.bidir = set()
        self.neighbour_map = dict()
        self.neighbour_timestamp = dict()
        self.mpr = set()
        self.mpr_seqno = 0
        self.ms = set()
        self.ms_seqno = 0
        self.topo = dict()
        self.route_list = dict()

    @property
    def get_neighbour_timeout(self):
        return Clock().time - self.timeout_neighbour

    @property
    def get_tc_timeout(self):
        return Clock().time - self.timeout_tc

    @property
    def get_neighbour_map(self):
        return deepcopy(self.neighbour_map)

    @property
    def get_topo(self):
        return deepcopy(self.topo)

    @property
    def topo_tuple(self):
        self.lock.acquire()
        try:
            return set(self.get_topo.keys())
        finally:
            self.lock.release()

    @property
    def route(self):
        return self.route_list

    @property
    def two_hop(self):
        self.lock.acquire()
        try:
            if self.neighbour_map == {}:
                return set()
            return set.union(*list(self.neighbour_map.values()))
        finally:
            self.lock.release()

    def mpr_of(self, neighbour):
        return neighbour in self.ms

    def hello_update(self, neighbour, unidir, bidir, mpr):
        self.neighbours_hello_update(neighbour, unidir, bidir)
        self.update_mpr_set()
        self.update_ms_set(neighbour, mpr)
        self.calc_route_table()

    def neighbours_hello_update(self, neighbour, unidir, bidir):
        current = Clock().time
        if neighbour in self.bidir:
            self.neighbour_timestamp[neighbour] = current
            bidir.discard(self.nid)
            self.neighbour_map[neighbour] = bidir
            return self

        if self.nid in bidir | unidir:
            self.unidir.discard(neighbour)
            self.bidir.add(neighbour)
            bidir.discard(self.nid)
            self.neighbour_map[neighbour] = bidir
            self.neighbour_timestamp[neighbour] = current
            return self

        self.unidir.add(neighbour)
        self.neighbour_timestamp[neighbour] = current
        return self

    def update_mpr_set(self):
        def update_mpr_set_rec(get_neighbour_map, two_hop_set):
            if two_hop_set == set():
                return set()
            interset_count = lambda x: len(x & two_hop_set)
            convert = lambda x: (interset_count(x[1]), x[0])
            interset = set(map(convert, get_neighbour_map.items()))
            _, mpr = max(interset)
            two_hop_set = two_hop_set - get_neighbour_map[mpr]
            get_neighbour_map.pop(mpr)
            return {mpr} | update_mpr_set_rec(get_neighbour_map, two_hop_set)

        two_hop_set = self.two_hop
        get_neighbour_map = self.get_neighbour_map
        new_mpr = update_mpr_set_rec(get_neighbour_map, two_hop_set)
        if new_mpr == self.mpr:
            return
        self.mpr = new_mpr
        self.mpr_seqno += 1

    def update_ms_set(self, neighbour, mpr):
        if self.nid in mpr:
            if neighbour in self.ms:
                return
            self.ms.add(neighbour)
            self.ms_seqno += 1
            return
        if neighbour in self.ms:
            self.ms.discard(neighbour)
            self.ms_seqno += 1
            return

    def tc_update(self, last_hop, ms, ms_seqno):
        current = Clock().time

        for (dst, final_hop), (prev_seq, prev_ts) in self.get_topo.items():
            if final_hop == last_hop and prev_seq > ms_seqno:
                return

            if final_hop == last_hop and prev_seq <= ms_seqno:
                self.topo.pop((dst, final_hop))

        for dst in ms:
            self.topo[(dst, last_hop)] = (ms_seqno, current)

        self.calc_route_table()

    def remove_neighbour(self, neighbours):
        if neighbours == set():
            return False
        for node_id in neighbours:
            self.neighbour_map.pop(node_id)
            self.neighbour_timestamp.pop(node_id)
            self.bidir.discard(node_id)
            self.unidir.discard(node_id)
            self.ms.discard(node_id)
        return True

    def remove_topo(self, last_hops):
        deleted = False
        for last_hop in last_hops:
            for (dst, final_hop), (_, _) in self.get_topo.items():
                if final_hop == last_hop:
                    self.topo.pop((dst, final_hop))
                    deleted = deleted or True
        return deleted

    def check_timeout(self):
        neighbour_timeout_timestamp = self.get_neighbour_timeout
        neighbour_filter = lambda x: x[1] < neighbour_timeout_timestamp
        neighbour_status = self.remove_neighbour(set(map(lambda x: x[0],filter(neighbour_filter,self.neighbour_timestamp.items()))))
        if neighbour_status:
            self.update_mpr_set()

        tc_timeout_timestamp = self.get_tc_timeout
        topo_filter = lambda x: x[1][1] < tc_timeout_timestamp
        topo_status = self.remove_topo(set(map(lambda x: x[0][1],filter(topo_filter,self.get_topo.items()))))

        if neighbour_status or topo_status:
            self.calc_route_table()

    def get_calc_route_table(self, get_topo, bidir):
        route = dict()
        for node in bidir:
            route[node] = (node, 1)
        h = 1
        changed = True
        while changed:
            changed = False
            for dst, last_hop in get_topo:
                if (dst not in route and last_hop in route
                        and route[last_hop][1] == h and dst != self.nid):
                    route[dst] = (route[last_hop][0], h + 1)
                    changed = changed or True
            h += 1

        return route

    def calc_route_table(self):
        get_topo = self.topo_tuple
        bidir = self.bidir

        self.lock.acquire()
        try:
            self.route_list = self.get_calc_route_table(get_topo, bidir)
        finally:
            self.lock.release()

    def get_route(self, dst):
        try:
            return self.route[dst][0]
        except KeyError:
            return None

