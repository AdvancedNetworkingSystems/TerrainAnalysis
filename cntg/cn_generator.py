import random
import time
import networkx as nx
import network
import folium
import pickle
import os
import wifi
import yaml
import numpy as np
import geopandas as gpd
import pandas as pd
import ubiquiti as ubnt
from folium import plugins
from misc import NoGWError
from node import AntennasExahustion, ChannelExahustion, LinkUnfeasibilty
from edgeffect import EdgeEffect
from building import Building
from pyproj import Proj, transform
import shapely.ops
from functools import partial
from shapely.geometry import box, Point
import pyproj
from shapely.ops import transform
from shapely import wkt
import gc
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning) #problem with pyproj
import logging
import tqdm

class NoMoreNodes(Exception):
    pass


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

class CN_Generator():

    def __init__(self, args={}, unk_args={}, cache={}):
        self.round = 0
        self.below_bw_nodes = 0
        self.infected = {}
        self.susceptible = set()
        self.net = network.Network()
        with open("gws.yml", "r") as gwf:
            self.gwd = yaml.safe_load(gwf)
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
        self.datafolder = self.args.base_folder + "results/"
        self.graphfolder = self.args.base_folder + "graph/"
        self.mapfolder = self.args.base_folder + "map/"
        for f in [self.datafolder, self.graphfolder, self.mapfolder]:
            os.makedirs(f, exist_ok=True)
        if self.args.restructure:
            restructure = "edgeffect"
        else:
            restructure = "no_restructure"
        self.filename = "%s-%s-%d-%d-%s-%d-%d-%s-%d-%d-%d"\
                        % (self.dataset,
                           self.args.strategy,
                           self.b,
                           self.random_seed,
                           self.n,
                           int(self.e),
                           self.B[0],
                           restructure,
                           self.V,
                           self.args.max_dev,
                           time.time())
        self.open_log()

        try:
            self.loss_graph_dict = cache['loss_graph_dict']
            self.logger.info("Using cached loss graph dict")
        except:
            self.read_loss_graph()
            cache['loss_graph_dict'] = self.loss_graph_dict
        try:
            self.graph_dict = cache['graph_dict']
            self.logger.info("Using cached graph dict")
        except:
            self.read_intervis_graph()
            cache['graph_dict'] = self.graph_dict

        try:
            self.buildings = cache['buildings'].copy()
            self.logger.info("Using cached buildings set")
        except KeyError:
            self.read_buildings()
            cache['buildings'] = self.buildings.copy()

        try:
            self.soc_df = cache['soc_df'].copy()
            self.logger.info("Using cached socioeconomic data set")
        except KeyError:
            self.read_socdataset()
            cache['soc_df'] = self.soc_df.copy()

        self.gid_pop_prop = self.soc_df[["gid", "P1"]].to_numpy()
        self.pop_tot = self.soc_df.P1.sum()
        self.buildings_idx = self.buildings.sindex
        self.event_counter = 0
        self.candidate_nodes = []
        self.candidate_len = 0
        ubnt.load_devices()

    def _post_init(self):
        gateway = self.get_gateway()
        self.soc_df = self.soc_df.drop(gateway.gid)
        self.gid_pop_prop = self.soc_df[["gid", "P1"]].to_numpy()
        self.pop_tot = self.soc_df.P1.sum()
        self.gateway = gateway
        self.infected[gateway.gid] = gateway
        self.net.add_gateway(gateway, attrs={'event': 0})
        self.event_counter += 1
        self.logger.info("The gateway is " + repr(gateway))

    def read_buildings(self):
        self.logger.info("Loading buildings set from disk")
        df = pd.read_csv("%s/best_p.csv"%(self.args.data_dir), names=['id', 'x', 'y'], header=0)
        self.buildings = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y)).set_index(df.id)
        #Remove nodes that are not in the connected component of the graph
        self.to_rem = []
        for b in self.buildings.itertuples():
            if b.id not in self.graph_dict.keys():
                self.to_rem.append(b.id)
        self.logger.info("Removing %d nodes that are unconnectable"%(len(self.to_rem)))
        self.buildings = self.buildings.drop(self.to_rem)

    def read_socdataset(self):
        self.logger.info("Loading socioeconomic data set from disk")
        self.soc_df = gpd.read_file("%s/socecon.csv"%(self.args.data_dir))
        soc_df = pd.read_csv("%s/socecon.csv"%(self.args.data_dir))
        soc_df['geom'] = soc_df['geom'].apply(wkt.loads)
        self.soc_df = gpd.GeoDataFrame(soc_df, geometry='geom')
        self.soc_df['id'] = self.soc_df.gid
        self.soc_df = self.soc_df.set_index('id')
        self.soc_df = self.soc_df.drop(self.to_rem)

    def read_loss_graph(self):
        self.logger.info("Loading loss graph dict from disk")
        if os.path.exists(self.loss_graph_path+".dump"):
            with open(self.loss_graph_path+".dump", 'rb') as handle:
                gc.disable()
                self.loss_graph_dict = pickle.load(handle)
                gc.enable()
        else:
            self.loss_graph_dict = {}
            with open(self.loss_graph_path) as gr:
                for line in gr:
                    l = line[:-1].split(' ')
                    if(len(l)<=1):
                        continue
                    src = int(l[0])
                    dst = int(l[1])
                    #check if there's the opposite edge to save 50% of memory
                    try:
                        self.loss_graph_dict[dst,src]
                    except KeyError:
                        self.loss_graph_dict[src,dst] = [np.int8(l[2]),
                                                          np.float16(l[3]),
                                                          np.float16(l[4])]
                with open(self.loss_graph_path+".dump", 'wb') as handle:
                    pickle.dump(self.loss_graph_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def read_intervis_graph(self):
        self.logger.info("Loading graph dict from disk")
        if os.path.exists(self.loss_graph_path+".dump_int"):
            with open(self.loss_graph_path+".dump_int", 'rb') as handle:
                gc.disable()
                self.graph_dict = pickle.load(handle)
                gc.enable()
        else:
            self.graph_dict= {}
            with open(self.loss_graph_path) as gr:
                for line in gr:
                    l = line[:-1].split(' ')
                    if(len(l)<=1):
                        continue
                    src = int(l[0])
                    dst = int(l[1])
                    #check if there's the opposite edge to save 50% of memory
                    if src not in self.graph_dict.keys():
                        self.graph_dict[src] = []
                    self.graph_dict[src].append(dst)
                with open(self.loss_graph_path+".dump_int", 'wb') as handle:

                    pickle.dump(self.graph_dict, handle, protocol=pickle.HIGHEST_PROTOCOL)


    def open_log(self):
        self.loss_graph_path = "%s/loss_graph.edgelist"%(self.args.data_dir)
        logfile = self.datafolder + self.filename + ".log"

        self.logger = logging.getLogger("cntg_logger")
        self.logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        self.fl = logging.FileHandler(filename=logfile)
        self.fl.setLevel(level=logging.DEBUG)

        ch = TqdmLoggingHandler()
        ch.setLevel(level=self.args.log_level)

        ch.setFormatter(formatter)

        self.logger.addHandler(ch)
        self.logger.addHandler(self.fl)

    def close_log(self):
        for hndl in self.logger.handlers[:]:
            hndl.close()
            self.logger.removeHandler(hndl)

    def get_gateway(self):
        project = partial(
            pyproj.transform,
                pyproj.Proj(init='epsg:4326'), # source coordinate system
                pyproj.Proj(init='epsg:3003')) # destination coordinate system
        (lat, long) =  self.gwd['gws'][self.dataset][self.b]
        gw = transform(project, Point(long, lat))  # apply projection
        buildings = self.soc_df[self.soc_df.contains(gw)]
        if len(buildings) == 0:
            self.logger.error("Selected gw is invalid")
        try:
            id = list(buildings.itertuples())[0].gid
            p = self.buildings.loc[id].geometry
        except IndexError:
            self.logger.error("Gw not found in dataset" % (self.b))
            raise NoGWError
        except KeyError:
            self.logger.error("Dataset %s is not in gw file" % (self.dataset))
            raise NoGWError
        self.logger.debug("Selected GW at %f,%f with id %d"%(long, lat, id))
        return Building(id, p)

    def get_susceptibles(self):
        #self.susceptible = set(self.db_buildings) - set(self.infected.values())
        return

        # geoms =[g.point for g in self.infected.values()]
        # prova = gpd.GeoDataFrame(pd.DataFrame([(g.gid, g.point) for g in self.infected.values()], columns=["id", "geometry"]))
        # self.sb = box(*prova.total_bounds).buffer(self.e)
        # #self.sb = cascaded_union(geoms).buffer(self.e)
        # possible_matches_index = list(self.buildings_idx.intersection(self.sb.bounds))
        # buildings = self.buildings.iloc[possible_matches_index]
        # #buildings = possible_matches[possible_matches.intersects(self.sb)]
        #db_buildings = [Building(b.osm_id, b.geometry) for b in self.buildings.itertuples()] #use bounds of buffer, much faster
        #db_buildings = self.t.get_buildings(self.sb.get_buffer(self.e))

        #self.susceptible = set(db_buildings) - set(self.infected.values())

    def get_newnode(self):
        return False


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
                if self.net.graph.nodes[n]['min_bw'] < bw:
                    self.below_bw_nodes += 1
                    if self.below_bw_nodes/len(self.infected) > self.B[1]:
                        self.logger.info("%f nodes below"%(self.below_bw_nodes/len(self.infected)))
                        return True
            except KeyError:
                #if the nod has no 'min_bw' means that it is not connected
                pass
        return False

    def add_links(self, new_node):
        raise NotImplementedError

    def check_connectivity(self, nodes, new_node):
        links = []
        n_id = int(new_node.gid)
        neighbors = []
        try:
            for n in nodes:
                if n.gid in self.graph_dict[n_id]:
                    neighbors.append(n)
        except KeyError:
            self.logger.warn("Node out of area %d"%(n_id))
        for n in neighbors:
            link = {}
            link['src'] = new_node
            link['dst'] = n
            try:
                tupl = self.loss_graph_dict[n_id,n.gid]
            except KeyError:
                tupl =  self.loss_graph_dict[n.gid, n_id]
            link['src_orient'] = tupl[1:]
            az = (link['src_orient'][0] + 180) % 360
            el = -link['src_orient'][1] + 360
            link['dst_orient'] = (az, el)
            link['loss'] = tupl[0]
            links.append(link)
        #must return links in LOS that are in the buffer
        return links

    def restructure(self):
        return False

    def finalize(self):
        return False

    def main(self):
        try:
            while not self.stop_condition():
                self.round += 1
                # pick random node
                try:
                    new_node = self.get_newnode()
                except NoMoreNodes:
                    self.logger.warn("No more nodes to test")
                    break
                # connect it to the network
                if(self.add_links(new_node)):
                    # update area of susceptible nodes
                    self.get_susceptibles()
                    self.restructure()
                    self.logger.info("Number of nodes:%d, number of links:%d, infected:%d, susceptible:%d, unconnectable %d"
                          "Nodes below bw:%s"
                          % (self.net.size(), len(self.net.graph.edges())/2, len(self.infected),
                             len(self.susceptible), len(self.candidate_nodes), self.below_bw_nodes))
                    if self.args.D and len(self.net.graph) > 2:
                        self.print_metrics()
                        #self.plot_map()
                    #input("stop me")
        except KeyboardInterrupt:
            #trick to save with ctrl-c
            pass
        # save result
        for k, v in self.net.compute_metrics().items():
            self.logger.info("%s: %s"%(k, v))
        if self.debug_file:
            dataname = self.datafolder + "data-" + self.filename + ".csv"
            with open(dataname, "w+") as f:
                header_line = "# node, min_bw"
                print(header_line, file=f)
                min_b = self.net.compute_minimum_bandwidth()
                for n, b in sorted(min_b.items(), key = lambda x: x[1]):
                    print(n, "," ,  b, file=f)
                self.logger.info("A data file was saved in " + dataname)
            self.fl.close()
            self.debug_file.close()
        if self.args.plot:
            #animationfile = self.save_evolution()
            #mapfile = self.plot_map()
            graphfile = self.save_graph()
            #print("A browsable map was saved in " + mapfile)
            #print("A browsable animated map was saved in " + animationfile)
            self.logger.info("A graphml was saved in " + graphfile)
        self.finalize()
        self.close_log()

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
        quasi_centroid = self.gateway.point
        self.animation = folium.Map(location=(quasi_centroid.x,
                                    quasi_centroid.y),
                                    zoom_start=14, tiles='OpenStreetMap')
        point_list = list(zip(*self.sb.exterior.coords.xy))
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
        inProj = Proj('epsg:3003')
        outProj = Proj('epsg:4326')
        s_project = partial(transform, inProj, outProj)
        quasi_centroid = shapely.ops.transform(s_project, self.gateway.point)
        self.map = folium.Map(location=(quasi_centroid.x, quasi_centroid.y),
                              zoom_start=14, tiles='OpenStreetMap')
        # p = shapely.ops.transform(s_project, self.sb)
        # point_list = list(zip(*p.exterior.coords.xy))
        # folium.PolyLine(locations=[(x, y) for (x, y) in point_list],
        #                 fill_color="green", weight=1,
        #                 color='green').add_to(self.map)
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
                folium.Marker(transform(inProj,outProj,lat, lon),
                              icon=folium.Icon(color='red'),
                              popup=label
                              ).add_to(self.map)
            else:
                folium.CircleMarker(transform(inProj,outProj,lat, lon),
                                    fill=True,
                                    popup=label,
                                    fill_opacity=opacity).add_to(self.map)
        for frm, to, p in self.net.graph.edges(data=True):
            lat_f, lon_f = nx.get_node_attributes(self.net.graph, 'pos')[frm]
            lat_t, lon_t = nx.get_node_attributes(self.net.graph, 'pos')[to]
            label = "Loss: %d dB<br>Rate: %d mbps<br>link_per_antenna: %d<br> src_orient %f <br> dst_orient %f" % \
                    (p['loss'], p['rate'], p['link_per_antenna'], p['src_orient'][0], p['dst_orient'][0])
            weight = 1 + 8/p['link_per_antenna']  # reasonable defaults
            folium.PolyLine(locations=[transform(inProj,outProj,lat_f, lon_f), transform(inProj,outProj,lat_t, lon_t)],
                            weight=weight, popup=label).add_to(self.map)

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
            print("nodes,unconnected,", ",".join(m.keys()), file=self.debug_file)
        print(len(self.net.graph),",",len(self.candidate_nodes), ",",  ",".join(map(str, m.values())),
              file=self.debug_file)
