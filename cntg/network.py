import networkx as nx
from antenna import Antenna
from node import Node
import ubiquiti as ubnt
import numpy
import wifi
import random
import datetime
from collections import Counter, defaultdict
from node import AntennasExahustion, ChannelExahustion, LinkUnfeasibilty, LinkTooBad


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
        self.graph.add_node(building.gid,
                            pos=building.pos,
                            node=Node(self.max_dev * 2),
                            **attrs)
        self.gateway = building.gid

    def add_node(self, building, attrs={}):
        self.graph.add_node(building.gid,
                            pos=building.pos,
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
        # Now there are 2 devices, calculate the rates
        src_rate, dst_rate = ubnt.get_maximum_rate(link['loss'],
                                                   src_ant.ubnt_device[0],
                                                   dst_ant.ubnt_device[0])
        if(src_rate == 0 or dst_rate ==0):
            raise LinkTooBad
            return False
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
        # Check if there's a free channel on both (intersection)
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
        if(src_rate == 0 or dst_rate ==0):
            raise LinkTooBad
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
            self.graph.nodes[node]['x'] = self.graph.nodes[node]['pos'][0]
            self.graph.nodes[node]['y'] = self.graph.nodes[node]['pos'][1]
            del self.graph.nodes[node]['pos']
            # remove antenna to allow graph_ml exportation
            del self.graph.nodes[node]['node']
        for edge in self.graph.edges():
            del self.graph.edges[edge]['src_ant']
            del self.graph.edges[edge]['dst_ant']
            del self.graph.edges[edge]['src_orient']
            del self.graph.edges[edge]['dst_orient']
            try:
                del self.graph.edges[edge]['interfering_links']
            except KeyError:
                pass
        nx.write_graphml(self.graph, filename)

    def calc_metric(self, link):
        self.add_node(link['src'])
        try:
            src_ant = self.add_link_generic(link)
        except (LinkUnfeasibilty, AntennasExahustion, ChannelExahustion) as e:
            worse = (link['src'].gid, None)
        else:
            # i must remove the new node from this list to avoid problems when i make difference and order them
            min_bw = [m for m in list(self.compute_minimum_bandwidth().items())
                            if m[0] != link['src'].gid]
            if min_bw:
                worse = min(min_bw, key=lambda x: x[1])
            else:
                #This happens only at the begining when the new node is the 2nd node
                worse = (link['src'].gid, 0)
        return({'link': link, 'node': worse[0], 'min_bw': worse[1]})

# --- METRICS ---
    def compute_minimum_bandwidth(self):
        min_bandwidth = {}
        paths = defaultdict(list)
        paths_per_edge = Counter()  # how many SPs pass through an edge
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
                # interfereing links = all the links that share an antenna with
                # this link
                try:
                    intf_links = g_e['interfering_links']
                except KeyError:
                    intf_links = []

                intf_number = 1
                # the achievable rate on a link e is given by the maximum
                # bit rate divided by the number of interfering links that
                # have at least one shortest path passing through them.
                # If an interfering link is not used by any shortest path, we
                # don't count it.
                for l in intf_links:
                    if (l[0], l[1]) in paths_per_edge:
                        intf_number += 1
                bw = g_e['rate'] / (intf_number * paths_per_edge[e])
                # the bottleneck is given by the achievable bandwidth/number
                # of shortest path passing through the link
                # Example:
                #       1----2----3---GW
                #                 |
                #                 |
                #                 4
                #  2->3 and 4->3 share the same radio and have max rate 100
                #  then the achievable rate on 2->3 and 4->3 is 100/2 and the
                #  bottleneck link for node 1 is 2->3 whose bandwidth is
                #  (100/2)/2: the maximum bandwidth in the link, divided by the
                #  number of SPs passing through it (1->GW and 2->GW)

                if bw < min_bw:
                    min_bw = bw
            self.graph.nodes[d]['min_bw'] = min_bw
            min_bandwidth[d] = min_bw
        return min_bandwidth

    def compute_equivalent_connectivity(self):
        """ if C_0 is the component including the gateway, then if graph
        connectivity > 1, return connectivity, else return 1/the number of
        cut-points. High = robust (many node need to fail to partition) """
        if len(self.graph) < 2:
            return 1
        main_comp = None
        for c in nx.connected_components(self.graph.to_undirected()):
            sg = self.graph.subgraph(c)
            if self.gateway in sg.nodes():
                main_comp = sg

        connectivity = nx.node_connectivity(main_comp)
        if connectivity > 1:
            return connectivity
        else:
            return 1/len(list(nx.articulation_points(
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
        # Calculate cost of network
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
        metrics["price_per_mbit"] = metrics['price_per_user'] / \
                                     (sum([x for x in min_bandwidth.values()])/len(min_bandwidth))
        metrics["cut_points"] = self.compute_equivalent_connectivity()
        # more useful metrics
        metrics["avg_link_per_antenna"] = numpy.mean([d['link_per_antenna']
                                                     for _, _, d in
                                                     self.graph.edges(
                                                     data=True)])
        metrics["time_passed"] = datetime.datetime.now()
        metrics["antennas_per_node"] = sum([len(x[1]['node'].antennas)
                                            for x in self.graph.nodes(data=True)])\
                                                    /len(min_bandwidth)
        return metrics
