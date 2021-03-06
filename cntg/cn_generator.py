import libterrain as lt
from geoalchemy2.shape import to_shape
from shapely.geometry.polygon import Polygon
from shapely.geometry import Point
from multiprocessing import Pool
from misc import NoGWError
from node import AntennasExahustion, ChannelExahustion, LinkUnfeasibilty
import shapely
import random
import time
import networkx as nx
import configargparse
import network
import folium
from folium import plugins
import ubiquiti as ubnt
from edgeffect import EdgeEffect
import multiprocessing as mp
import os
import psutil
import datetime
import wifi
import yaml
from collections import defaultdict

class NoMoreNodes(Exception):
    pass


def poor_mans_color_gamma(bitrate):
    blue_to_red = {200: '#03f', 150: '#6600cc', 100: '#660099',
                   50: '#660066', 30: '#660000'}
    for b in sorted(blue_to_red):
        if bitrate < b:
            return blue_to_red[b]
    return blue_to_red[200]


class CN_Generator():

    def __init__(self, args={}, unk_args={}):
        self.round = 0
        self.below_bw_nodes = 0
        self.infected = {}
        self.susceptible = set()
        self.pool = None
        self.net = network.Network()
        with open("gws.yml", "r") as gwf:
            self.gwd = yaml.load(gwf)
        self.args = args
        self.n = self.args.max_size
        self.e = self.args.expansion
        self.b = self.args.gateway
        self.P = self.args.processes
        if self.args.bandwidth:
            self.B = tuple(map(float, self.args.bandwidth.split(' ')))
        if self.args.restructure:
            self.R = tuple(map(int, self.args.restructure.split(' ')))
        self.V = self.args.viewshed_extra
        self.dataset = self.args.dataset
        wifi.default_channel_width = self.args.channel_width
        if not self.args.seed:
            self.random_seed = random.randint(1, 10000)
        else:
            self.random_seed = self.args.seed
        self.debug_file = None
        random.seed(self.random_seed)
        self.net.set_maxdev(self.args.max_dev)
        self.datafolder = self.args.base_folder + "data/"
        self.graphfolder = self.args.base_folder + "graph/"
        self.mapfolder = self.args.base_folder + "map/"
        for f in [self.datafolder, self.graphfolder, self.mapfolder]:
            os.makedirs(f, exist_ok=True)
        if self.args.restructure:
            restructure = "edgeffect"
        else:
            restructure = "no_restructure"
        self.filename = "%s-%s-%d-%d-%s-%d-%d-%s-%d-%d-%d"\
                        % (self.dataset, self.args.strategy, self.b, self.random_seed, self.n,
                           int(self.e), self.B[0], restructure, self.V, self.args.max_dev, time.time())
        #self.t = terrain(self.args.dsn, self.dataset, ple=2.4, processes=self.P)
        self.t = lt.ParallelTerrainInterface(self.args.dsn, lidar_table=self.args.lidar_table, processes=self.P)
        self.BI = lt.BuildingInterface.get_best_interface(self.args.dsn, self.dataset)
        self.polygon_area = self.BI.get_province_area(self.dataset)
        self.event_counter = 0
        self.noloss_cache = defaultdict(set)
        ubnt.load_devices()
        self.pool = Pool(self.P)

    def _post_init(self):
        gateway = self.get_gateway()
        self.infected[gateway.gid] = gateway
        self.net.add_gateway(gateway, attrs={'event': 0})
        self.event_counter += 1
        self.get_susceptibles()
        print("The gateway is " + repr(gateway))

    def get_gateway(self):
        try:
            position = self.gwd['gws'][self.dataset][self.b]
        except IndexError:
            print("Index %d is out of range" % (self.b))
            raise NoGWError
        except KeyError:
            print("Dataset %s is not in gw file" % (self.dataset))
            raise NoGWError
        self.gw_pos = Point(float(position[1]), float(position[0]))
        #buildings = self.t.get_buildings(shape=self.gw_pos)
        buildings = self.BI.get_buildings(shape=self.gw_pos)
        if len(buildings) < 1:
            raise NoGWError
        gw = buildings[0]
        gw.height = position[2]
        return gw

    def get_random_node(self):
        #must cast into list and order because sample on set is unpredictable
        susceptible_tmp = sorted(list(self.susceptible), key=lambda x: x.gid)
        if not susceptible_tmp:
            raise NoMoreNodes
        new_node = random.sample(susceptible_tmp, 1)[0]
        self.susceptible.remove(new_node)
        return new_node

    def get_susceptibles(self):
        geoms = [g.shape() for g in self.infected.values()]
        self.sb.set_shape(geoms)
        #db_buildings = self.t.get_buildings(self.sb.get_buffer(self.e))
        db_buildings =  self.BI.get_buildings(shape=self.sb.get_buffer(self.e), area=self.polygon_area)
        self.susceptible = set(db_buildings) - set(self.infected.values())

    def get_newnode(self):
        raise NotImplementedError

    def stop_condition(self):
        raise NotImplementedError

    def stop_condition_maxnodes(self):
        return len(self.infected) > self.n

    def stop_condition_minbw(self, rounds=1):
        #in case you don't want to test the stop condition every round
        if len(self.infected) % rounds != 0 or\
                len(self.infected) < self.B[2]:
            self.below_bw_nodes = '-'
            return False
        self.below_bw_nodes = 0

        # recompute minimum bw at each node
        bw = self.B[0]
        self.net.compute_minimum_bandwidth()
        # if the minimum bw of a node is less than the treshold stop
        for n in self.infected:
            if n == self.net.gateway:
                continue
            try:
                if self.net.graph.node[n]['min_bw'] < bw:
                    self.below_bw_nodes += 1
                    if self.below_bw_nodes/len(self.infected) > self.B[1]:
                        return True
            except KeyError:
                #if the nod has no 'min_bw' means that it is not connected
                pass
        return False

    def add_links(self, new_node):
        raise NotImplementedError

    def check_connectivity(self, nodes, new_node):
        
        nodes_to_test = set(nodes) - self.noloss_cache[new_node]
        if not nodes_to_test:
            return []
        links = self.t.get_link_parallel(src=new_node.coord_height(),
                                         dst_list=list(map(lambda x: x.coord_height(), nodes_to_test)))
        los_nodes = set()
        for l in links:
            if l:
                l['src'] = l['src']['building']
                l['dst'] = l['dst']['building']
                if new_node == l['src']:
                    los_nodes.add(l['dst'])
                elif new_node == l['dst']:
                    los_nodes.add(l['src'])
        noloss_nodes = set(nodes) - los_nodes
        self.noloss_cache[new_node] |= noloss_nodes
        return links

    def restructure(self):
        raise NotImplementedError

    def main(self):
        try:
            while not self.stop_condition():
                self.round += 1
                # pick random node
                try:
                    new_node = self.get_newnode()
                except NoMoreNodes:
                    print("No more nodes to test")
                    break
                # connect it to the network
                if(self.add_links(new_node)):
                    # update area of susceptible nodes
                    self.get_susceptibles()
                    self.restructure()
                    print("Number of nodes:%d, infected:%d, susceptible:%d, "
                          "Nodes below bw:%s"
                          % (self.net.size(), len(self.infected),
                             len(self.susceptible), self.below_bw_nodes))
                    if self.args.D and len(self.net.graph) > 2:
                        self.print_metrics()
                        self.plot_map()
                    #input("stop me")
        except KeyboardInterrupt:
            pid = os.getpid()
            killtree(pid)
            pass
        # save result
        for k, v in self.net.compute_metrics().items():
            print(k, v)
        if self.debug_file:
    
            dataname = self.datafolder + "data-" + self.filename + ".csv"
            with open(dataname, "w+") as f: 
                header_line = "# node, min_bw" 
                print(header_line, file=f)
                min_b = self.net.compute_minimum_bandwidth()
                for n, b in sorted(min_b.items(), key = lambda x: x[1]):
                    print(n, "," ,  b, file=f)
                print("A data file was saved in " + dataname)

            self.debug_file.close()
        if self.args.plot:
            animationfile = self.save_evolution()
            mapfile = self.plot_map()
            graphfile = self.save_graph()
            print("A browsable map was saved in " + mapfile)
            print("A browsable animated map was saved in " + animationfile)
            print("A graphml was saved in " + graphfile)

    def restructure_edgeeffect_mt(self, num_links=1):
        # run only every self.args.R[0] nodes added
        if not self.args.restructure or self.net.size() % int(self.R[0]) != 0:
            return
        num_links = self.R[1]
        max_links = num_links
        ee = EdgeEffect(self.net.graph, self.net.main_sg())
        effect_edges = self.pool.map(ee.restructure_edgeeffect, self.feasible_links)
        effect_edges.sort(key=lambda x: x['effect'])
        # Try to connect the best link (try again till it gets connected)
        while(effect_edges):
            selected_edge = effect_edges.pop()
            link = [link for link in self.feasible_links
                    if link['src'].gid == selected_edge[0] and
                    link['dst'].gid == selected_edge[1]
                    ]
            try:
                self.add_link(link[0], existing=True)
            except (LinkUnfeasibilty, AntennasExahustion, ChannelExahustion):
                pass
            else:
                max_links -= 1
                if max_links <= 0:
                    print("Restructured {} links".format(num_links))
                    return

    def add_node(self, node):
        self.event_counter += 1
        return self.net.add_node(node, attrs={'event': self.event_counter})

    def add_link(self, link, existing=False, reverse=False):
        self.event_counter += 1
        return self.net.add_link_generic(link=link,
                                         attrs={'event': self.event_counter},
                                         existing=existing,
                                         reverse=reverse)

    def save_graph(self):
        graphname = self.graphfolder + "graph-" + self.filename + ".graphml"
        self.net.save_graph(graphname)
        return graphname

    def graph_to_animation(self):
        quasi_centroid = self.polygon_area.representative_point()
        self.animation = folium.Map(location=(quasi_centroid.y,
                                    quasi_centroid.x),
                                    zoom_start=14, tiles='OpenStreetMap')
        p = shapely.ops.cascaded_union([pl for pl in self.polygon_area])
        point_list = list(zip(*p.exterior.coords.xy))
        folium.PolyLine(locations=[(y, x) for (x, y) in point_list],
                        fill_color="green", weight=1,
                        color='green').add_to(self.animation)
        edges_s = sorted(self.net.graph.edges(data=True),
                         key=lambda x: x[2]['event'])
        nodes_s = sorted(self.net.graph.nodes(data=True),
                         key=lambda x: x[1]['event'])
        last_event = max(edges_s[-1][2]['event'], nodes_s[-1][1]['event'])
        e_coords = []
        e_times = []
        for e in edges_s:
            e_coords.append([list(self.net.graph.nodes()[e[0]]['pos']),
                            list(self.net.graph.nodes()[e[1]]['pos'])])
            e_times.append(1530744263666 + e[2]['event'] * 36000000)
            # FIXME starting time is just a random moment
            features_edges = {
                'type': 'Feature',
                'geometry': {
                    'type': 'MultiLineString',
                    'coordinates': e_coords,
                },
                'properties': {
                    'times': e_times,
                }
            }
        n_coords = []
        n_times = []
    
        for n in nodes_s:
            n_coords.append([n[1]['pos'], n[1]['pos']])
            n_times.append(1530744263666 + n[1]['event'] * 36000000)
        # the only way I found to plot the nodes is pretend they are
        # one-point lines
        features_nodes = {
            'type': 'Feature',
            'geometry': {
                'type': 'MultiLineString',
                'coordinates': n_coords,
            },
            'properties': {
                'times': n_times,
                'style': {
                    'color': 'red',
                    'width': 20,
                }
            }
        }
    
        plugins.TimestampedGeoJson({
            'type': 'FeatureCollection',
            'features': [features_edges, features_nodes]},
            transition_time=500, auto_play=False).add_to(self.animation)

    def graph_to_leaflet(self):
        quasi_centroid = self.polygon_area.representative_point()
        self.map = folium.Map(location=(quasi_centroid.y, quasi_centroid.x),
                              zoom_start=14, tiles='OpenStreetMap')
        p = shapely.ops.cascaded_union([pl for pl in self.polygon_area])
        point_list = list(zip(*p.exterior.coords.xy))
        folium.PolyLine(locations=[(y, x) for (x, y) in point_list],
                        fill_color="green", weight=1,
                        color='green').add_to(self.map)
        max_event = max(nx.get_node_attributes(self.net.graph, 'event').values())
        for node in self.net.graph.nodes(data=True):
            (lat, lon) = node[1]['pos']
            try:
                label="Node: %d<br>Antennas:<br> %s<br> min_bw: %s" %\
                      (node[0], node[1]['node'], node[1]['min_bw'])
            except KeyError:
                label="Node: %d<br>Antennas:<br> %s<br>" %\
                    (node[0], node[1]['node'])
            opacity = node[1]['event']/max_event
            if node[0] == self.net.gateway:
                folium.Marker([lon, lat],
                              icon=folium.Icon(color='red'),
                              popup=label
                              ).add_to(self.map)
            else:
                folium.CircleMarker([lon, lat],
                                    fill=True,
                                    popup=label,
                                    fill_opacity=opacity).add_to(self.map)
        for frm, to, p in self.net.graph.edges(data=True):
            lat_f, lon_f = nx.get_node_attributes(self.net.graph, 'pos')[frm]
            lat_t, lon_t = nx.get_node_attributes(self.net.graph, 'pos')[to]
            label = "Loss: %d dB<br>Rate: %d mbps<br>link_per_antenna: %d<br> src_orient %f <br> dst_orient %f" % \
                    (p['loss'], p['rate'], p['link_per_antenna'], p['src_orient'][0], p['dst_orient'][0])
            weight = 1 + 8/p['link_per_antenna']  # reasonable defaults
            color = poor_mans_color_gamma(p['rate'])
            folium.PolyLine(locations=[[lon_f, lat_f], [lon_t, lat_t]],
                            weight=weight, popup=label,
                            color=color).add_to(self.map)

    def plot_map(self):
        self.graph_to_leaflet()
        mapname = self.mapfolder + "map-" + self.filename + ".html"
        self.map.save(mapname)
        return mapname

    def save_evolution(self):
        self.graph_to_animation()
        mapname = self.mapfolder + "map-" + self.filename + "-animation.html"
        self.animation.save(mapname)
        return mapname

    def print_metrics(self):
        m = self.net.compute_metrics()
        if not self.debug_file:
            statsname = self.datafolder + "stats-" + self.filename + ".csv"
            self.debug_file = open(statsname, "w+", buffering=1) # line-buffered
            header_line = "#" + str(vars(self.args))
            print(header_line, file=self.debug_file)
            print("nodes,", ",".join(m.keys()), file=self.debug_file)
        print(len(self.net.graph), ",",  ",".join(map(str, m.values())), 
              file=self.debug_file)


def killtree(pid, including_parent=False):
    parent = psutil.Process(pid)
    for child in parent.children(recursive=True):
        try:
            child.terminate()
        except psutil.NoSuchProcess:
            pass

    if including_parent:
        parent.kill()
