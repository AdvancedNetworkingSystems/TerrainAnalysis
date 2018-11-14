import networkx as nx
from antenna import Antenna
import ubiquiti as ubnt
import code
node_fixed_cost = 200


def compute_link_quality(left, right, attrs, min_rate=6):
    """ We want to express metrics as a cost, so high=bad, 1/bandwidth may
    introduce non linearities with non additive metrics, thus we rescale it for
    a basic minimum rate  """
    return min_rate*attrs['link_per_antenna']/attrs['rate']


class Network():
    def __init__(self):
        self.graph = nx.DiGraph()
        self.cost = 0

    def add_gateway(self, building):
        self.add_node(building)
        self.gateway = building.gid

    def add_node(self, building):
        self.graph.add_node(building.gid, pos=building.xy(), antennas=list(),
                            cost=node_fixed_cost)
        self.cost += node_fixed_cost

    def del_node(self, building):
        self.graph.remove_node(building.gid)
        self.cost -= node_fixed_cost

    def add_link(self, link):
        ant1 = None
        device0 = None
        link_per_antenna = 2
        # loop trough the antenna of the node
        for antenna in self.graph.nodes[link[1].gid]['antennas']:
            if antenna.check_node_vis(link_angles=link[4]):
                ant1 = antenna
                rate0, device0 = ubnt.get_fastest_link_hardware(link[2],
                                        target=antenna.ubnt_device[0])
                if not rate0:
                    # no radio available for this link loss, target antenna pair
                    # try with a better antenna 
                    # TODO: We can have multiple antenna in the same viewshed -> must doublecheck it
                    #       No we select the first one we find, but we should search for the optimal one (max rate)
                    ant1 = None
                    break
                rate0, rate1 = ubnt.get_maximum_rate(link[2], device0[0],
                                        antenna.ubnt_device[0])
                for l in self.graph.out_edges(link[1].gid, data=True):
                    if l[2]['src_ant'] == antenna:
                        link_per_antenna = l[2]['link_per_antenna'] + 2
                        l[2]['link_per_antenna'] += 2
                for l in self.graph.in_edges(link[1].gid, data=True):
                    if l[2]['dst_ant'] == antenna:
                        link_per_antenna = l[2]['link_per_antenna'] + 2
                        l[2]['link_per_antenna'] += 2
                break
        if not ant1:
            rate1, device1 = ubnt.get_fastest_link_hardware(link[2])
            if not rate1:
                # TODO: What should we do if the link is unfeasible?
                return False
            rate0, rate1 = ubnt.get_maximum_rate(link[2], device1[0],
                                                 device1[0])
            device0 = device1
            ant1 = self.add_antenna(link[1].gid, device1, link[4])

        # find proper device add antenna to local node
        ant0 = self.add_antenna(link[0].gid, device0, link[3])
        self.graph.add_edge(link[0].gid, link[1].gid, loss=link[2],
                            src_ant=ant0, dst_ant=ant1, rate=rate0,
                            link_per_antenna=link_per_antenna)
        self.graph.add_edge(link[1].gid, link[0].gid, loss=link[2],
                            src_ant=ant1, dst_ant=ant0, rate=rate1,
                            link_per_antenna=link_per_antenna)
        return True

    def add_antenna(self, node, device, orientation):
        ant = Antenna(device, orientation)
        self.graph.nodes[node]['antennas'].append(ant)
        self.graph.nodes[node]['cost'] += ant.device['average_price']
        self.cost += ant.device['average_price']
        return ant

    def save_graph(self, filename):
        self.compute_minimum_bandwidth()
        for node in self.graph:
            self.graph.node[node]['x'] = self.graph.node[node]['pos'][0]
            self.graph.node[node]['y'] = self.graph.node[node]['pos'][1]
            del self.graph.node[node]['pos']
            # remove antenna to allow graph_ml exportation
            del self.graph.node[node]['antennas']
        for edge in self.graph.edges():
            del self.graph.edges[edge]['src_ant']
            del self.graph.edges[edge]['dst_ant']
        nx.write_graphml(self.graph, filename)

    def compute_minimum_bandwidth(self):
        min_bandwidth = {}
        for d in self.graph.nodes():
            if d == self.gateway:
                continue
            rev_path = nx.dijkstra_path(self.graph, d,
                                        self.gateway,
                                        weight=compute_link_quality)
            min_b = float('inf')
            for i in range(len(rev_path) - 1):
                attrs = self.graph.get_edge_data(rev_path[i], rev_path[i + 1])
                b = attrs['rate'] / attrs['link_per_antenna']
                if b < min_b:
                    min_b = b
            self.graph.node[d]['min_bw'] = min_b
            min_bandwidth[d] = min_b
        return min_bandwidth
