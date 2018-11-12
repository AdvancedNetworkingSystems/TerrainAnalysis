from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import argparse
import time
import ubiquiti as ubnt
from antenna import Antenna


class Growing_network(CN_Generator):

    def __init__(self, dataset, args=None, DSN=None):
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, dataset, DSN=None)
        self.parser.add_argument('-n', help="number of nodes", type=int,
                                 required=True)
        self.parser.add_argument('-e', help="expansion range (in meters),"
                                 "defaults to buildings at 30km", type=float,
                                 default=30000)
        self.args = self.parser.parse_args(args)
        self.n = self.args.n
        self.e = self.args.e
        self.b = self.args.b
        self.filename = "graph-%s-%s-%d-%s-%d.graphml"\
                        % (dataset, self.n, int(self.e), self.b, time.time())
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
        return len(self.infected) >= self.n

    def check_link(self, source, destination):
        link = self.t.get_link(destination, source, h1=2, h2=2)
        if link and link.loss > 0:
            return (source, destination, link.loss, link.Aorient, link.Borient)

    def check_connectivity(self, new_node):
        visible_links = []
        for i in self.infected:
            link = self.check_link(source=new_node, destination=i)
            if link:
                visible_links.append(link)
        # with Pool(5) as p:
        #     self.new_node = new_node
        #     visible_links = list(set(p.map(self.check_link, self.infected)) - None)
        return visible_links

    def add_links(self, new_node):
        visible_links = self.check_connectivity(new_node)
        # if there's at least one vaild link add the node to the network
        if visible_links:
            visible_links.sort(key=lambda x: x[2], reverse=True)
            link = visible_links.pop()
            self.infected.append(link[0])
            #check if current node has already antennas and try to connect to them
            self.net.add_node(link[0])
            self.net.add_link(link)
            if len(visible_links) > 1:
                link = visible_links.pop()
                self.net.add_link(link)
            return True
        return False
