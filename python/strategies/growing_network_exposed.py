from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import argparse
import time
import ubiquiti as ubnt
from edgeffect import edgeffect
import networkx as nx


class Growing_network_exposed(CN_Generator):

    def __init__(self, dataset, args=None, DSN=None):
        self.exposed = set()
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, dataset, DSN=None)
        self.parser.add_argument('-n', help="number of nodes", type=int,
                                 required=True)
        self.parser.add_argument('-e', help="expansion range (in meters), "
                                 "defaults to buildings at 30km", type=float,
                                 default=30000)
        self.args = self.parser.parse_args(args)
        self.n = self.args.n
        self.e = self.args.e
        self.b = self.args.b
        self.feasible_links = []
        self.filename = "graph-%s-%s-%d-%s-%d.graphml"\
                        % (dataset, self.n, int(self.e), self.b, time.time())
        self._post_init()
        ubnt.load_devices()

    def get_newnode(self):
        new_node = random.sample(self.susceptible, 1)[0]
        self.susceptible.remove(new_node)
        return new_node

    def get_susceptibles(self):
        geoms = [g.shape() for g in (self.infected + list(self.exposed))]
        self.sb.set_shape(geoms)

        self.susceptible = set(self.t.get_buildings(
                               self.sb.get_buffer(self.e))
                               ) - set(self.infected)

    def stop_condition(self):
        return self.net.size() >= self.n

    def check_link(self, source, destination):
        link = self.t.get_link(destination, source, h1=2, h2=2)
        if link and link.loss > 0:
            return (source, destination, link.loss, link.Aorient, link.Borient)

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
        visible_links_infected = self.check_connectivity(self.infected,
                                                         new_node)
        visible_links_exposed = self.check_connectivity(self.exposed, new_node)
        self.net.add_node(new_node)
        node_added = False
        if visible_links_infected:
            visible_links_infected.sort(key=lambda x: x[2], reverse=True)
            link = visible_links_infected.pop()
            if self.net.add_link(link):
                # If i can connect to an infected node I'm infected too,
                # separate island connected to main net
                self.infected.append(link[0])
                node_added = True
        if visible_links_exposed:
            visible_links_exposed.sort(key=lambda x: x[2], reverse=True)
            link = visible_links_exposed.pop()
            if self.net.add_link(link):
                if link[0] not in self.infected:
                    self.infected.append(link[0])  # If i wasn't conncted to anybody but i connected to an Exposed
                    self.infected.append(link[1])      # we are both infected (separate island though)
                    self.exposed.remove(link[1])
                node_added = True
        if not node_added:  # Node not connectable to anybody
            self.exposed.add(new_node)
        self.feasible_links += visible_links_exposed + visible_links_infected
        return True

    def add_edges(self):
        if self.net.size() % 10 != 0:
            # run 1 in 5 rounds
            return
        # run it only in the biggest connected component
        eel = []
        for l in self.feasible_links:
            if not (l[0].gid in self.net.biggest_sg() and l[1].gid in self.net.biggest_sg()):
                continue
            edge = {}
            edge[0] = l[0].gid
            edge[1] = l[1].gid
            edge['weight'] = 1  # For now do not use costs
            # TODO: What cost should we use? Can use bandwidth since it depends on the antenna
            e = edgeffect(self.net.biggest_sg(), edge)
            eel.append((l, e))
        eel.sort(key=lambda x: x[1])
        # Try to connect the best link (try again till something gets connected)
        while(eel):
            if self.net.add_link(eel.pop()[0]):
                print("Added one edge")
                return
