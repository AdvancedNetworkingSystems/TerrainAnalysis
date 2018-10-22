from libterrain.libterrain import terrain
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry.polygon import Polygon
from multiprocessing import Pool
import shapely
import random
import time
import networkx as nx
import matplotlib.pyplot as plt


class CN_Generator():
    def __init__(self, DSN, dataset):
        self.infected = []
        self.susceptible = set()
        self.graph = nx.Graph()
        self.t = terrain(DSN, dataset, ['0201'])
        gateway = self.get_gateway()
        self.infected.append(gateway)
        self.graph.add_node(gateway.gid, pos=gateway.xy())
        print("The gateway is " + repr(gateway))
        self.get_susceptibles()

    def get_gateway(self):
        raise NotImplementedError

    def get_newnode(self):
        raise NotImplementedError

    def get_susceptibles(self):
        raise NotImplementedError

    def stop_condition(self):
        raise NotImplementedError

    def add_links(self, new_node):
        raise NotImplementedError

    def save_graph(self):
        for node in self.graph:
            self.graph.node[node]['x'] = infected_graph.node[node]['pos'][0]
            self.graph.node[node]['y'] = infected_graph.node[node]['pos'][1]
            del self.graph.node[node]['pos']
        nx.write_graphml(self.graph, "graph-%d.graphml" % (time.time()))

    def main(self):
        while not self.stop_condition():
            # pick random node
            new_node = self.get_newnode()
            # connect it to the network
            if(self.add_links(new_node)):
                # update area of susceptible nodes
                self.get_susceptibles()
            print("Number of nodes:%d" % (len(self.infected)))
        # save result
        self.save_graph()
