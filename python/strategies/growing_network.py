from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import argparse
import time
import ubiquiti as ubnt
from antenna import Antenna
from edgeffect import edgeffect


class Growing_network(CN_Generator):

    def __init__(self, args, unk_args=None, DSN=None):
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, args.d, DSN=None)
        self.parser.add_argument('-n', help="number of nodes", type=int,
                                 required=True)
        self.parser.add_argument('-e', help="expansion range (in meters),"
                                 "defaults to buildings at 30km", type=float,
                                 default=30000)
        self.args = self.parser.parse_args(unk_args)
        self.n = self.args.n
        self.e = self.args.e
        self.b = self.args.b
        self.net.set_maxdev(args.max_dev)
        self.feasible_links = []
        self.filename = "graph-%s-%s-%d-%s-%d.graphml"\
                        % (args.d, self.n, int(self.e), self.b, time.time())
        self._post_init()
        ubnt.load_devices()

    def get_newnode(self):
        new_node = random.sample(self.susceptible, 1)[0]
        self.susceptible.remove(new_node)
        return new_node

    def get_susceptibles(self):
        geoms = [g.shape() for g in self.infected]
        self.sb.set_shape(geoms)

        self.susceptible = set(self.t.get_buildings(
                               self.sb.get_buffer(self.e))
                               ) - set(self.infected)

    def stop_condition(self):
        # recompute minimum bw at each node
        self.net.compute_minimum_bandwidth()
        # if the minimum bw of a node is less than the treshold stop
        for n in self.net.graph.nodes():
            if n == self.net.gateway:
                continue
            if self.net.graph.node[n]['min_bw'] < 40:
                return False
        return len(self.infected) >= self.n

    def check_link(self, source, destination):
        phy_link = self.t.get_link(destination, source, h1=2, h2=2)
        if phy_link and phy_link.loss > 0:
            link = {}
            link['src'] = source
            link['dst'] = destination
            link['loss'] = phy_link.loss
            link['src_orient'] = phy_link.Aorient
            link['dst_orient'] = phy_link.Borient
            return link

    def check_connectivity(self, set_nodes, new_node):
        visible_links = []
        for i in set_nodes:
            link = self.check_link(source=new_node, destination=i)
            if link:
                visible_links.append(link)
        # with Pool(5) as p:
        #   TODO: fix client mutlithreading
        #   self.new_node = new_node
        #   visible_links = list(set(p.map(self.check_link, self.infected)) - None)
        return visible_links

    def add_links(self, new_node):
        visible_links = self.check_connectivity(self.infected, new_node)
        # if there's at least one vaild link add the node to the network
        if visible_links:
            visible_links.sort(key=lambda x: x['loss'], reverse=True)
            link = visible_links.pop()
            self.infected.append(link['src'])
            # check if current node has already antennas and try to connect to them
            self.net.add_node(link['src'])
            if not self.net.add_link(link):
                # if this link is not feasible the following ones (worser) aren't either
                self.net.del_node(link['src'])
                return False
            if len(visible_links) > 1:
                link = visible_links.pop()
                self.net.add_link(link)
            # add the remaining links to a list of feasible links
            self.feasible_links += visible_links
            return True
        return False

    def restructure(self):
        # run only every 10 nodes added
        if self.net.size() % 10 != 0:
            return
        # for each link that we found is feasible, but we havent added compute the edge effect
        for l in self.feasible_links:
            # we do it only for the link between nodes of the main connected component
            if not (l['src'].gid in self.net.main_sg() and l['dst'].gid in self.net.main_sg()):
                l['effect'] = 0
                continue
            edge = {}
            edge[0] = l['src'].gid
            edge[1] = l['dst'].gid
            edge['weight'] = 1  # For now do not use costs
            # TODO: What cost should we use? Can use bandwidth since it depends on the antenna
            l['effect'] = edgeffect(self.net.main_sg(), edge)
        # We could just pick up the maximum, but if the link is not negotiable then we should do it again and again
        # so we order them and we pop them untill the first one connect
        self.feasible_links.sort(key=lambda x: x['effect'])
        # Try to connect the best link (try again till something gets connected)
        while(self.feasible_links):
            if self.net.add_link(self.feasible_links.pop()):
                print("Added one edge")
                return
