from libterrain.libterrain import terrain
from functools import partial
from shapely.ops import transform, cascaded_union
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry.polygon import Polygon
import pyproj
import shapely
import random
import networkx as nx
import matplotlib.pyplot as plt

project = partial(
    pyproj.transform,
    pyproj.Proj(init='epsg:4326'),# source coordinate system
    pyproj.Proj(init='epsg:3003'))# destination coordinate system

deproject = partial(
    pyproj.transform,
    pyproj.Proj(init='epsg:3003'),# source coordinate system
    pyproj.Proj(init='epsg:4326'))# destination coordinate system


DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"
dataset = "quarrata"

# initialize from gateway 
infected = []
susceptible = set()
infected_graph = nx.Graph()
t = terrain(DSN, dataset, ['0201'])
gateway = t.get_building_gid(gid=54922)
infected.append(gateway)
infected_graph.add_node(gateway.gid, pos=gateway.xy())
print("The gateway is " + repr(gateway))
susceptible_buffer = transform(project, gateway.shape()).buffer(500)
susceptible = set(t.get_building(transform(deproject, susceptible_buffer))) - set(infected)
run = True
fig, ax = plt.subplots()
img = plt.imread("quarrata.png")
ax.imshow(img, extent=[10.9657, 10.9927, 43.8394, 43.8584])
fig, ax = plt.subplots()
img = plt.imread("quarrata.png")
plt.ion()
plt.show()

while run:
    # pick random node from susceptible set and check connectivity with network
    new_node = random.sample(susceptible, 1)[0]
    susceptible.remove(new_node)
    visible_links = []
    for i in infected:
        loss = t.get_loss(i, new_node, h1=2, h2=2)
        if loss > 0:
            #print("Loss between %d and %d is %f" % (i.gid, new_node.gid, loss))
            visible_links.append((new_node, i, loss))
    # if there's at least one vaild link add the node to the network
    if len(visible_links) > 0:
        visible_links.sort(key=lambda x: x[2], reverse=True)
        link = visible_links.pop()
        infected.append(link[0])
        infected_graph.add_node(link[0].gid, pos=link[0].xy())
        infected_graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
        if len(visible_links) > 1:
            link = visible_links.pop()
            infected_graph.add_edge(link[0].gid, link[1].gid, weight=link[2])

        geoms = [g.shape() for g in infected]
        susceptible_buffer = transform(project, cascaded_union(geoms)).buffer(200)
        print("Area of susceptible nodes: %f"%(susceptible_buffer.area))
                # create list of geoms
        susceptible = set(t.get_building(transform(deproject, susceptible_buffer))) - set(infected)
        print(infected)
        pos=nx.get_node_attributes(infected_graph, 'pos')
        if len(infected) > 100:
            run = False
        #fig.clf()
        ax.imshow(img, extent=[10.9657, 10.9927, 43.8394, 43.8584])
        nx.draw(infected_graph, pos=pos, ax=ax)
        plt.draw()
        #plt.show()
        plt.pause(0.001)

#remove tuple attribute to save the graphml and save x and y separately
for node in infected_graph:
    infected_graph.node[node]['x'] = infected_graph.node[node]['pos'][0]
    infected_graph.node[node]['y'] = infected_graph.node[node]['pos'][1]
    del infected_graph.node[node]['pos']
nx.write_graphml(infected_graph, "graph1.graphml")
