from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import argparse


class Growing_network(CN_Generator):

    def __init__(self, dataset, args=None, DSN=None):
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, dataset, DSN=None)
        self.parser.add_argument('-n', help="number of nodes", type=int)
        self.args = self.parser.parse_args(args)
        self.n = self.args.n

    def get_gateway(self):
        return self.t.get_building_gid(gid=54922)

    def get_newnode(self):
        new_node = random.sample(self.susceptible, 1)[0]
        self.susceptible.remove(new_node)
        return new_node

    def get_susceptibles(self):
        geoms = [g.shape() for g in self.infected]
        self.sb.set_shape(geoms)
        self.susceptible = set(self.t.get_building(self.sb.get_buffer(1000))) - set(self.infected)

    def stop_condition(self):
        if len(self.infected) >= self.n:
            return True
        return False

    def check_link(self, source, destination):
        loss = self.t.get_loss(destination, source, h1=2, h2=2)
        if loss > 0:
            # print("Loss between %d and %d is %f" % (i.gid, new_node.gid, loss))
            return (destination, source, loss)

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
            self.graph.add_node(link[0].gid, pos=link[0].xy())
            self.graph.add_node(link[1].gid, pos=link[1].xy())
            self.graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
            if len(visible_links) > 1:
                link = visible_links.pop()
                self.graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
            return True
        return False
