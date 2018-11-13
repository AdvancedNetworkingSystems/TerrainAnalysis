from libterrain.libterrain import terrain
from geoalchemy2.shape import to_shape
from shapely.geometry.polygon import Polygon
from shapely.geometry import Point
from multiprocessing import Pool
from misc import NoGWError
import shapely
import random
import time
import networkx as nx
import matplotlib.pyplot as plt
import argparse
import mplleaflet
import network


def compute_link_bandwidth(left, right, attrs):
    return attrs['rate']/attrs['link_per_antenna']


class CN_Generator():

    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"

    def __init__(self, dataset, DSN=None):
        self.infected = []
        self.susceptible = set()
        self.net = network.Network()
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-p", help="plot the graph using the browser",
                                 dest='plot', action='store_true')
        self.parser.add_argument('-b', help="start building latlong (lat.dd,long.dd)", type=str,
                                 required=True)
        self.parser.set_defaults(plot=False)
        
        if not DSN:
            self.t = terrain(self.DSN, dataset, ple=2.4)
        else:
            self.t = terrain(DSN, dataset, ple=2.4)

    def _post_init(self):
        latlong = self.b.split(",")
        self.gw_pos = Point(float(latlong[1]), float(latlong[0]))
        gateway = self.get_gateway()
        self.infected.append(gateway)
        self.net.add_gateway(gateway)
        self.get_susceptibles()
        print("The gateway is " + repr(gateway))

    def get_gateway(self):
        buildings = self.t.get_buildings(shape=self.gw_pos)
        if len(buildings) < 1:
            raise NoGWError
        return buildings[0]

    def get_newnode(self):
        raise NotImplementedError

    def get_susceptibles(self):
        raise NotImplementedError

    def stop_condition(self):
        raise NotImplementedError

    def add_links(self, new_node):
        raise NotImplementedError

    def save_graph(self):
        self.net.save_graph(self.filename)

    def plot(self):
        nx.draw(self.net.graph, pos=nx.get_node_attributes(self.net.graph, 'pos'))
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
                print("Number of nodes:%d" % (len(self.net.graph.nodes)))
                if self.args.plot:
                    self.plot()
                #print(self.net.cost)
        # save result
        min_b = self.compute_minimum_bandwidth()
        for i in sorted([x for x in min_b.items()], key = lambda x: x[1]):
            print(i[0], i[1])
        #import code
        #code.interact(local=locals())
        #self.save_graph()

    def compute_minimum_bandwidth(self):
        min_bandwidth = {}
        for d in self.net.graph.nodes():
            if d == self.net.gateway:
                continue
            rev_path = nx.dijkstra_path(self.net.graph, d,
                self.net.gateway, weight=compute_link_bandwidth)
            min_b = float('inf')
            for i in range(len(rev_path)-1):
                attrs = self.net.graph.get_edge_data( rev_path[i], rev_path[i+1])
                b = attrs['rate']/attrs['link_per_antenna']
                if b < min_b:
                    min_b = b
            min_bandwidth[d] = min_b
        return min_bandwidth
