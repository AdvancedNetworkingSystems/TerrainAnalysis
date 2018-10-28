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
from folium import plugins

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
        self.event_counter = 0

    def _post_init(self):
        gateway = self.get_gateway()
        self.infected.append(gateway)
        self.graph.add_node(gateway.gid, pos=gateway.xy(), 
                            event=self.event_counter)
        self.event_counter += 1
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

    def add_node(self, node, pos):
        self.graph.add_node(node, pos=pos, event=self.event_counter)
        self.event_counter += 1

    def add_edge(self, src, dst, weight):
        self.graph.add_edge(src, dst, weight=weight, event=self.event_counter)
        self.event_counter += 1

    def save_graph(self):
        for node in self.graph:
            self.graph.node[node]['x'] = self.graph.node[node]['pos'][0]
            self.graph.node[node]['y'] = self.graph.node[node]['pos'][1]
            del self.graph.node[node]['pos']
        nx.write_graphml(self.graph, self.filename)

    def graph_to_animation(self):
        location = [(self.t.working_area[1] + self.t.working_area[3])/2,
                    (self.t.working_area[0] + self.t.working_area[2])/2]
        box = [
                [self.t.working_area[1], self.t.working_area[0]],
                [self.t.working_area[1], self.t.working_area[2]],
                [self.t.working_area[3], self.t.working_area[2]],
                [self.t.working_area[3], self.t.working_area[0]],
                [self.t.working_area[1], self.t.working_area[0]]
                ]
        self.m = folium.Map(location=location, zoom_start=13, tiles='Stamen Terrain')
        edges_s = sorted(self.graph.edges(data=True), key=lambda x: x[2]['event'])
        nodes_s = sorted(self.graph.nodes(data=True), key=lambda x: x[1]['event'])
        last_event = max(edges_s[-1][2]['event'], nodes_s[-1][1]['event'])
        e_coords = []
        e_times = []
        for e in edges_s:
            e_coords.append([list(self.graph.nodes()[e[0]]['pos']),
                          list(self.graph.nodes()[e[1]]['pos'])])
            e_times.append(1530744263666+e[2]['event']*36000000)
            #FIXME starting time is just a random moment
            
        features_edges = {
          'type': 'Feature',
          'geometry': {
              'type': 'MultiLineString',
              'coordinates': e_coords,
              },
           'properties': {
              'times':  e_times,
              }
           }
 
        n_coords = []
        n_times = []

        for n in nodes_s:
            n_coords.append([n[1]['pos'], n[1]['pos']])
            n_times.append(1530744263666+n[1]['event']*36000000)
            
        # the only way I found to plot the nodes is pretend they are one-point lines
        features_nodes = {
          'type': 'Feature',
          'geometry': {
              'type': 'MultiLineString',
              'coordinates': n_coords,
              },
           'properties': {
              'times':  n_times,
              'style':{
                  'color': 'red',
                  'width': 20,
                  }
              }
           }


        plugins.TimestampedGeoJson({
            'type': 'FeatureCollection',
            'features': [features_edges, features_nodes]},
            transition_time=500, auto_play=False).add_to(self.m)


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
            self.graph_to_animation()
            map_file = '/tmp/index-animation.html'
            self.m.save(map_file)
            print("A browsable animated map was saved in " + map_file)

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
