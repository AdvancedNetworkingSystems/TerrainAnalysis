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
import folium

class CN_Generator():

    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"

    def __init__(self, dataset, DSN=None):
        self.infected = []
        self.susceptible = set()
        self.graph = nx.Graph()
        self.parser = argparse.ArgumentParser()
        self.parser.add_argument("-p", help="plot the graph using the browser",
                            dest='plot', action='store_true')
        self.parser.set_defaults(plot=False)
        if not DSN:
            self.t = terrain(self.DSN, dataset, ple=2.4)
        else:
            self.t = terrain(DSN, dataset, ple=2.4)

    def _post_init(self):
        gateway = self.get_gateway()
        self.infected.append(gateway)
        self.graph.add_node(gateway.gid, pos=gateway.xy())
        self.get_susceptibles()
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

    def graph_to_leaflet(self):
        location = [(self.t.working_area[1] + self.t.working_area[3])/2,
                    (self.t.working_area[0] + self.t.working_area[2])/2]
        box = [
                [self.t.working_area[1], self.t.working_area[0]],
                [self.t.working_area[1], self.t.working_area[2]],
                [self.t.working_area[3], self.t.working_area[2]],
                [self.t.working_area[3], self.t.working_area[0]],
                [self.t.working_area[1], self.t.working_area[0]]
                ]
        self.m = folium.Map(location=location, zoom_start=14, tiles='Stamen Terrain')
        folium.PolyLine(locations=box, weight=1, color='green').add_to(self.m)
        for lat, lon in nx.get_node_attributes(self.graph, 'pos').values():
            folium.Marker([lon, lat], popup='').add_to(self.m)
        for frm, to, p in self.graph.edges(data=True):
            lat_f, lon_f = nx.get_node_attributes(self.graph, 'pos')[frm]
            lat_t, lon_t = nx.get_node_attributes(self.graph, 'pos')[to]
            label = str(int(p['weight'])) + " db"
            folium.PolyLine(locations=[[lon_f, lat_f], [lon_t, lat_t]],
                            weight=3, popup=label).add_to(self.m)

    def plot(self):
        nx.draw(self.graph, pos=nx.get_node_attributes(self.graph, 'pos'))
        plt.draw()
        self.graph_to_leaflet()
        if self.display_plot:
            self.graph_to_leaflet()
            map_file = '/tmp/index.html'
            self.m.save(map_file)
            print("A browsable map was saved in " + map_file)

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
        if self.args.plot:
            self.plot()
        # save result
        self.save_graph()
