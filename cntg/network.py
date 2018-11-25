import networkx as nx
from antenna import Antenna
from node import Node
import ubiquiti as ubnt
import numpy
import wifi
import random
from collections import Counter, defaultdict


def compute_link_quality(left, right, attrs, min_rate=6):
    """ We want to express metrics as a cost, so high=bad, 1/bandwidth may
    introduce non linearities with non additive metrics, thus we rescale it for
    a basic minimum rate  """
    return min_rate * attrs['link_per_antenna'] / attrs['rate']


class Network():
    def __init__(self):
        self.graph = nx.DiGraph()
        self.cost = 0

    def set_maxdev(self, max_dev):
        self.max_dev = max_dev

    def size(self):
        return len(self.graph)

    def main_sg(self):
        # Return the connected subgraph belonging to the gateway
        # Always return something, otherwise something very bad is happening
        sgs = nx.connected_component_subgraphs(self.graph.to_undirected())
        for sg in sgs:
            if self.gateway in sg:
                return sg

    def add_gateway(self, building, attrs={}):
        self.add_node(building, attrs)
        self.gateway = building.gid

    def add_node(self, building, attrs={}):
        self.graph.add_node(building.gid,
                            pos=building.xy(),
                            node=Node(self.max_dev),
                            **attrs)

    def del_node(self, building):
        self.graph.remove_node(building.gid)

    def update_interfering_links(self, link, dst_antenna=None, src_antenna=None):
        interfering_links = []
        degree = 0
        # calculate the number of link wrt the 2 antennas
        if dst_antenna:
            for l in self.graph.out_edges(link['dst'].gid, data=True):
                if l[2]['src_ant'] == dst_antenna:
                    interfering_links.append(l)
                    degree += 1
            for l in self.graph.in_edges(link['dst'].gid, data=True):
                if l[2]['dst_ant'] == dst_antenna:
                    interfering_links.append(l)
                    degree += 1
        if src_antenna:
            for l in self.graph.out_edges(link['src'].gid, data=True):
                if l[2]['dst_ant'] == src_antenna:
                    interfering_links.append(l)
                    degree += 1
            for l in self.graph.in_edges(link['src'].gid, data=True):
                if l[2]['src_ant'] == src_antenna:
                    interfering_links.append(l)
                    degree += 1
        # set it to the attribute
        if src_antenna:
            for l in self.graph.out_edges(link['src'].gid, data=True):
                if l[2]['dst_ant'] == src_antenna:
                    l[2]['interfering_links'] = interfering_links
                    l[2]['link_per_antenna'] = degree
            for l in self.graph.in_edges(link['src'].gid, data=True):
                if l[2]['src_ant'] == src_antenna:
                    l[2]['interfering_links'] = interfering_links
                    l[2]['link_per_antenna'] = degree
        if dst_antenna:
            for l in self.graph.out_edges(link['dst'].gid, data=True):
                if l[2]['src_ant'] == dst_antenna:
                    l[2]['interfering_links'] = interfering_links
                    l[2]['link_per_antenna'] = degree
            for l in self.graph.in_edges(link['dst'].gid, data=True):
                if l[2]['dst_ant'] == dst_antenna:
                    l[2]['interfering_links'] = interfering_links
                    l[2]['link_per_antenna'] = degree


    def add_link_generic(self, link, attrs={}, reverse=False, existing=False):
        result = None
        if reverse:
            reverse_link = {}
            reverse_link['src'] = link['dst']
            reverse_link['dst'] = link['src']
            reverse_link['loss'] = 50  # Fixed
            reverse_link['src_orient'] = link['dst_orient']
            reverse_link['dst_orient'] = link['src_orient']
            link = reverse_link

        if existing:
            result = self._add_link_existing(link, attrs)
        else:
            result = self._add_link(link, attrs)
        return result
    '''
    This function is used to connect a new node (src) to an existing node of the network
    NB: source must be a new node without antennas
    '''
    def _add_link(self, link, attrs={}):
        # Search if there's an antenna usable at the destination
        dst_antennas = self.graph.nodes[link['dst'].gid]['node']
        dst_ant = dst_antennas.get_best_dst_antenna(link)
        src_antennas = self.graph.nodes[link['src'].gid]['node']
        src_ant = src_antennas.add_antenna(loss=link['loss'],
                                           orientation=link['src_orient'],
                                           device=dst_ant.ubnt_device,
                                           channel=dst_ant.channel)
        # print("Added link from %s to %s oriented %s, %s" % (link['src'].gid, link['dst'].gid, link['src_orient'], link['dst_orient']))
        # print("src_ant %s, dst_ant %s"%(src_ant, dst_ant))
        # Now there are 2 devices, calculate the rates
        src_rate, dst_rate = ubnt.get_maximum_rate(link['loss'],
                                                   src_ant.ubnt_device[0],
                                                   dst_ant.ubnt_device[0])
        # Add everything to nx graph
        self.graph.add_edge(link['src'].gid,
                            link['dst'].gid,
                            loss=link['loss'],
                            src_ant=src_ant,
                            dst_ant=dst_ant,
                            src_orient=link['src_orient'],
                            dst_orient=link['dst_orient'],
                            rate=src_rate,
                            **attrs)

        self.graph.add_edge(link['dst'].gid,
                            link['src'].gid,
                            loss=link['loss'],
                            src_ant=dst_ant,
                            dst_ant=src_ant,
                            src_orient=link['dst_orient'],
                            dst_orient=link['src_orient'],
                            rate=dst_rate,
                            **attrs)
        self.update_interfering_links(link, src_antenna=src_ant, dst_antenna=dst_ant) 
        return src_ant

    def _add_link_existing(self, link, attrs={}):
        # Pick the best antenna at dst
        dst_antennas = self.graph.nodes[link['dst'].gid]['node']
        src_antennas = self.graph.nodes[link['src'].gid]['node']
        #Check if there's a free channel on both (intersection)
        free_channels = set(dst_antennas.free_channels) & set(src_antennas.free_channels)
        try:
            channel = random.sample(free_channels, 1)[0]
        except ValueError:
            raise ChannelExahustion
        # Since we want to add capacity to the network we always add new antennas
        dst_ant = dst_antennas.add_antenna(loss=link['loss'], orientation=link['dst_orient'], channel=channel)
        src_ant = src_antennas.add_antenna(loss=link['loss'], orientation=link['dst_orient'], channel=channel, device=dst_ant.ubnt_device)

        src_rate, dst_rate = ubnt.get_maximum_rate(link['loss'],
                                                   src_ant.ubnt_device[0],
                                                   dst_ant.ubnt_device[0])
        # Add everything to nx graph
        self.graph.add_edge(link['src'].gid,
                            link['dst'].gid,
                            loss=link['loss'],
                            src_ant=src_ant,
                            dst_ant=dst_ant,
                            rate=src_rate,
                            dst_orient=link['dst_orient'],
                            src_orient=link['src_orient'],
                            **attrs)

        self.graph.add_edge(link['dst'].gid,
                            link['src'].gid,
                            loss=link['loss'],
                            src_ant=dst_ant,
                            dst_ant=src_ant,
                            src_orient=link['dst_orient'],
                            dst_orient=link['src_orient'],
                            rate=dst_rate,
                            **attrs)
        self.update_interfering_links(link, src_antenna=src_ant, dst_antenna=dst_ant)
        return src_ant

    def save_graph(self, filename):
        self.compute_minimum_bandwidth()
        for node in self.graph:
            self.graph.node[node]['x'] = self.graph.node[node]['pos'][0]
            self.graph.node[node]['y'] = self.graph.node[node]['pos'][1]
            del self.graph.node[node]['pos']
            # remove antenna to allow graph_ml exportation
            del self.graph.node[node]['node']
        for edge in self.graph.edges():
            del self.graph.edges[edge]['src_ant']
            del self.graph.edges[edge]['dst_ant']
            del self.graph.edges[edge]['src_orient']
            del self.graph.edges[edge]['dst_orient']
        nx.write_graphml(self.graph, filename)


# --- METRICS ---
    def compute_minimum_bandwidth(self):
        min_bandwidth = {}
        paths = defaultdict(list)
        paths_per_edge = Counter()
        for d in self.graph.nodes():
            if d == self.gateway:
                continue
            try:
                path = nx.dijkstra_path(self.graph, d,
                                        self.gateway,
                                        weight=compute_link_quality)
            except nx.exception.NetworkXNoPath:
                continue
            for i in range(len(path)-1):
                paths_per_edge[(path[i], path[i+1])] += 1
                paths[d].append((path[i], path[i+1]))
        for d in paths:
            min_bw = float('inf')
            for e in paths[d]:
                g_e = self.graph[e[0]][e[1]]
                bw = g_e['rate'] / (g_e['link_per_antenna'] * paths_per_edge[e])
                if bw < min_bw:
                    min_bw = bw
            self.graph.node[d]['min_bw'] = min_bw
            min_bandwidth[d] = min_bw
        return min_bandwidth

    def compute_equivalent_connectivity(self):
        """ if C_0 is the component including the gateway, then if graph
        connectivity > 1, return 1/connectivity, else return the number of
        cut-points """
        if len(self.graph) < 2:
            return 1
        main_comp = None
        for c in nx.connected_component_subgraphs(self.graph.to_undirected()):
            if self.gateway in c.nodes():
                main_comp = c

        connectivity = nx.node_connectivity(main_comp)
        if connectivity >= 1:
            return 1/connectivity
        else:
            return len(list(nx.articulation_points(
                               main_comp.to_undirected())))

    def compute_metrics(self):
        """ returns a dictionary with a set of metrics that evaluate the
        network graph under several points of view """

        metrics = {}
        min_bandwidth = self.compute_minimum_bandwidth()
        disconnected_nodes = 0
        percentiles = [10, 50, 90]
        for perc in percentiles:
            metrics["perc_"+str(perc)] = ""
        # Calculate costo of network
        self.cost = 0
        for n in self.graph.nodes(data=True):
            self.cost += n[1]['node'].cost()
        counter = 1
        per_i = 0
        for d, b in sorted(min_bandwidth.items(), key=lambda x: x[1]):
            if not b:
                disconnected_nodes += 1
            else:
                perc = int(100*counter/len(min_bandwidth))
                counter += 1
                if per_i < len(percentiles) and perc > percentiles[per_i]:
                    metrics["perc_"+str(percentiles[per_i])] = b
                    per_i += 1

        metrics["connected_nodes"] = 1 + len(min_bandwidth) -\
                                       disconnected_nodes
        metrics["unconnected_ratio"] = disconnected_nodes / \
                                       (1 + len(min_bandwidth))
        metrics["price_per_user"] = self.cost/metrics['connected_nodes']
        metrics["price_per_mbyte"] = 8*metrics['price_per_user'] * \
                                     sum([1/x for x in min_bandwidth.values()
                                         if x])/metrics['connected_nodes']
        metrics["cut_points"] = 1/self.compute_equivalent_connectivity()
        # more useful metrics
        metrics["avg_link_per_antenna"] = numpy.mean([d['link_per_antenna']
                                                     for _, _, d in
                                                     self.graph.edges(
                                                     data=True)])
        return metrics
