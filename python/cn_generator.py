from libterrain.libterrain import terrain
from geoalchemy2.shape import to_shape
from shapely.geometry.polygon import Polygon
from multiprocessing import Pool
import shapely
import random
import time
import networkx as nx
import matplotlib.pyplot as plt
import argparse
import mplleaflet

class CN_Generator():

    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"

    def __init__(self, dataset, DSN=None):
        self.infected = []
        self.susceptible = set()
        self.graph = nx.Graph()
        self.parser = argparse.ArgumentParser()
        if not DSN:
            self.t = terrain(self.DSN, dataset, ple=2.4)
        else:
            self.t = terrain(DSN, dataset, ple=2.4)

    def _post_init(self):
        gateway = self.get_gateway()
        self.infected.append(gateway)
        self.graph.add_node(gateway.gid, pos=gateway.xy())
        print("The gateway is " + repr(gateway))

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
            self.graph.node[node]['x'] = self.graph.node[node]['pos'][0]
            self.graph.node[node]['y'] = self.graph.node[node]['pos'][1]
            del self.graph.node[node]['pos']
        nx.write_graphml(self.graph, self.filename)

    def plot(self):
        nx.draw(self.graph, pos=nx.get_node_attributes(self.graph, 'pos'))
        plt.draw()
        if self.display_plot:
            mplleaflet.show()
            self.display_plot = False
        else:
            mplleaflet.save_html()

    def main(self):
        self.display_plot = True
        while not self.stop_condition():
            # pick random node
            new_node = self.get_newnode()
            # connect it to the network
            if(self.add_links(new_node)):
                # update area of susceptible nodes
                self.get_susceptibles()
                print("Number of nodes:%d" % (len(self.graph.nodes)))
                self.plot()
        # save result
        self.save_graph()
