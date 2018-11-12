import networkx as nx
from antenna import Antenna
import ubiquiti as ubnt

node_fixed_cost = 200

class Network():
    def __init__(self):
        self.graph = nx.DiGraph()
        self.cost = 0

    def add_node(self, building):
        self.graph.add_node(building.gid, pos=building.xy(), antennas=list(),
                            cost=node_fixed_cost)
        self.cost += node_fixed_cost

    def add_link(self, link):
        ant1 = None
        device0 = None
        # loop trough the antenna of the node
        for antenna in self.graph.nodes[link[1].gid]['antennas']:
            if antenna.check_node_vis(link_angles=link[4]):
                print("Link connected to existing antenna")
                ant1 = antenna
                rate0, device0 = ubnt.get_fastest_link_hardware(link[2],
                                          target=antenna.ubnt_device[0])
                rate0, rate1 = ubnt.get_maximum_rate(link[2], device0[0],
                                          antenna.ubnt_device[0])
                break
        if not ant1:
            # TODO: find proper device and create new antenna
            # link is new negotitate both device
            rate1, device1 = ubnt.get_fastest_link_hardware(link[2])
            rate0, rate1 = ubnt.get_maximum_rate(link[2], device1[0],
                                                 device1[0])
            device0 = device1
            ant1 = self.add_antenna(link[1].gid, device1, link[4])

        # find proper device add antenna to local node
        ant0 = self.add_antenna(link[0].gid, device0, link[3])
        self.graph.add_edge(link[0].gid, link[1].gid, loss=link[2],
                            src_ant=ant0, dst_ant=ant1, rate=rate0)
        self.graph.add_edge(link[1].gid, link[0].gid, loss=link[2],
                            src_ant=ant1, dst_ant=ant0, rate=rate1)

    def add_antenna(self, node, device, orientation):
        ant = Antenna(device, orientation)
        self.graph.nodes[node]['antennas'].append(ant)
        self.graph.nodes[node]['cost'] += ant.device['average_price']
        self.cost += ant.device['average_price']
        return ant

    def save_graph(self, filename):
        for node in self.graph:
            self.graph.node[node]['x'] = self.graph.node[node]['pos'][0]
            self.graph.node[node]['y'] = self.graph.node[node]['pos'][1]
            del self.graph.node[node]['pos']
        nx.write_graphml(self.graph, filename)
