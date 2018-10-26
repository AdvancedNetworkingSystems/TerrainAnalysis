from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import argparse
import time


class Growing_network_exposed(CN_Generator):

    def __init__(self, dataset, args=None, DSN=None):
        self.exposed = set()
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, dataset, DSN=None)
        self.parser.add_argument('-n', help="number of nodes", type=int,
                                 required=True)
        self.parser.add_argument('-e', help="expansion range (in meters), defaults"
                                 "to buildings at 30mk", type=float,
                                 default=30000)
        self.parser.add_argument('-b', help="start building id", type=int,
                                 required=True)
        self.args = self.parser.parse_args(args)
        self.n = self.args.n
        self.e = self.args.e
        self.b = self.args.b
        self.filename = "graph-%s-%s-%d-%d-%d.graphml" % (dataset, self.n, int(self.e), self.b, time.time())
        self._post_init()

    def get_gateway(self):
        return self.t.get_building_gid(gid=self.b)

    def get_newnode(self):
        new_node = random.sample(self.susceptible, 1)[0]
        self.susceptible.remove(new_node)
        return new_node

    def get_susceptibles(self):
        geoms = [g.shape() for g in (self.infected + list(self.exposed))]
        self.sb.set_shape(geoms)

        self.susceptible = set(self.t.get_building(
                               self.sb.get_buffer(self.e))
                               ) - set(self.infected)

    def stop_condition(self):
        return len(self.infected) >= self.n

    def check_link(self, source, destination):
        loss = self.t.get_loss(destination, source, h1=2, h2=2)
        if loss > 0:
            # print("Loss between %d and %d is %f" % (i.gid, new_node.gid, loss))
            return (source, destination, loss)

    def check_connectivity(self, set_nodes, new_node):
        visible_links = []
        for i in set_nodes:
            link = self.check_link(source=new_node, destination=i)
            if link:
                visible_links.append(link)
        # with Pool(5) as p:
        #     self.new_node = new_node
        #     visible_links = list(set(p.map(self.check_link, self.infected)) - None)
        return visible_links

    def add_links(self, new_node):
        visible_links_infected = self.check_connectivity(self.infected, new_node)
        visible_links_exposed = self.check_connectivity(self.exposed, new_node)
        self.graph.add_node(new_node.gid, pos=new_node.xy())
        node_added = False
        if visible_links_infected:
            visible_links_infected.sort(key=lambda x: x[2], reverse=True)
            link = visible_links_infected.pop()
            self.graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
            self.infected.append(link[0])   # If i can connect to an infected node I'm infected too, separate island connected to main net
            node_added = True
        if visible_links_exposed:
            visible_links_exposed.sort(key=lambda x: x[2], reverse=True)
            link = visible_links_exposed.pop()
            self.graph.add_node(link[1].gid, pos=link[1].xy())
            self.graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
            if link[0] not in self.infected:
                self.infected.append(link[0])  # If i wasn't conncted to anybody but i connected to an Exposed
            self.infected.append(link[1])      # we are both infected (separate island though)
            node_added = True
        if not node_added:  # Node not connectable to anybody
            self.exposed.add(new_node)
        return True
