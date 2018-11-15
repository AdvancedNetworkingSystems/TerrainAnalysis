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
import network
import folium
from folium import plugins

class CN_Generator():

    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"

    def __init__(self, dataset, DSN=None):
        self.round = 0
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
        self.event_counter = 0

    def _post_init(self):
        latlong = self.b.split(",")
        self.gw_pos = Point(float(latlong[1]), float(latlong[0]))
        gateway = self.get_gateway()
        self.infected.append(gateway)
        self.net.add_gateway(gateway, attrs={'event': 0})
        self.event_counter += 1
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

    def add_node(self, node):
        self.event_counter += 1
        return self.net.add_node(node, attrs={'event': self.event_counter})

    def add_link(self, link):
        self.event_counter += 1
        return self.net.add_link(link, attrs={'event': self.event_counter})

    def save_graph(self):
        self.net.save_graph(self.filename)

    def graph_to_animation(self):
        quasi_centroid = self.t.polygon_area.representative_point()
        self.m = folium.Map(location=(quasi_centroid.y, quasi_centroid.x),
                zoom_start=14, tiles='OpenStreetMap')
        p = shapely.ops.cascaded_union([pl for pl in self.t.polygon_area])
        point_list = list(zip(*p.exterior.coords.xy))
        folium.PolyLine(locations=[(y, x) for (x, y) in point_list], 
                fill_color="green",
                weight=1, color='green').add_to(self.m)
        edges_s = sorted(self.net.graph.edges(data=True), key=lambda x: x[2]['event'])
        nodes_s = sorted(self.net.graph.nodes(data=True), key=lambda x: x[1]['event'])
        last_event = max(edges_s[-1][2]['event'], nodes_s[-1][1]['event'])
        e_coords = []
        e_times = []
        for e in edges_s:
            e_coords.append([list(self.net.graph.nodes()[e[0]]['pos']),
                          list(self.net.graph.nodes()[e[1]]['pos'])])
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
        quasi_centroid = self.t.polygon_area.representative_point()
        self.m = folium.Map(location=(quasi_centroid.y, quasi_centroid.x),
                zoom_start=14, tiles='Stamen Terrain')
        p = shapely.ops.cascaded_union([pl for pl in self.t.polygon_area])
        point_list = list(zip(*p.exterior.coords.xy))
        folium.PolyLine(locations=[(y, x) for (x, y) in point_list], 
                fill_color="green",
                weight=1, color='green').add_to(self.m)
        for lat, lon in nx.get_node_attributes(self.net.graph, 'pos').values():
            folium.Marker([lon, lat], popup='').add_to(self.m)
        for frm, to, p in self.net.graph.edges(data=True):
            lat_f, lon_f = nx.get_node_attributes(self.net.graph, 'pos')[frm]
            lat_t, lon_t = nx.get_node_attributes(self.net.graph, 'pos')[to]
            label = "Loss: %d\nRate: %d\nlink_per_antenna: %d" % \
                    (p['loss'], p['rate'], p['link_per_antenna'])
            folium.PolyLine(locations=[[lon_f, lat_f], [lon_t, lat_t]],
                            weight=3, popup=label).add_to(self.m)

    def plot(self):
        nx.draw(self.net.graph, pos=nx.get_node_attributes(self.net.graph, 'pos'))
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
            self.round += 1
            # pick random node
            new_node = self.get_newnode()
            # connect it to the network
            if(self.add_links(new_node)):
                # update area of susceptible nodes
                self.get_susceptibles()
                print("Number of nodes:%d, infected:%d, susceptible:%d" % (self.net.size(), len(self.infected), len(self.susceptible)))
                if self.args.plot:
                    self.plot()
                #print(self.net.cost)
            self.add_edges()
            self.net.compute_minimum_bandwidth()
        # save result
        min_b = self.net.compute_minimum_bandwidth()
        for k, v in self.net.compute_metrics().items():
            print(k, v)
        #import code
        #code.interact(local=locals())
        #self.save_graph()
