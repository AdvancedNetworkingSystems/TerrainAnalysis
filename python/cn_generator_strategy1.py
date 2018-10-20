from shapely.ops import transform, cascaded_union
from functools import partial
import pyproj
from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator


class Susceptible_Buffer():
    project = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:4326'),  # source coordinate system
        pyproj.Proj(init='epsg:3003'))  # destination coordinate system

    deproject = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:3003'),  # source coordinate system
        pyproj.Proj(init='epsg:4326'))  # destination coordinate system

    def set_shape(self, shape):
        self.orig_shape = shape
        self.shape = transform(self.project, shape)

    def get_buffer(self, m):
        return transform(self.deproject, self.shape.buffer(m))


class CN_Generator_Strategy1(CN_Generator):

    def __init__(self, DSN, dataset):
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, DSN, dataset)

    def get_gateway(self):
        return self.t.get_building_gid(gid=54922)

    def get_newnode(self):
        new_node = random.sample(self.susceptible, 1)[0]
        self.susceptible.remove(new_node)
        return new_node

    def get_susceptibles(self):
        geoms = [g.shape() for g in self.infected]
        self.sb.set_shape(cascaded_union(geoms))
        self.susceptible = set(self.t.get_building(self.sb.get_buffer(1000))) - set(self.infected)

    def stop_condition(self):
        if len(self.infected) > 100:
            return True
        return False

    def check_link(self, source, destination):
        loss = self.t.get_loss(destination, source, h1=2, h2=2)
        if loss > 0:
            # print("Loss between %d and %d is %f" % (i.gid, new_node.gid, loss))
            return (destination, source, loss)

    def check_connectivity(self, new_node):
        visible_links = []
        for i in self.infected:
            link = self.check_link(source=new_node, destination=i)
            if link:
                visible_links.append(link)
        # with Pool(5) as p:
        #     self.new_node = new_node
        #     visible_links = list(set(p.map(self.check_link, self.infected)) - None)
        return visible_links

    def add_links(self, new_node):
        visible_links = self.check_connectivity(new_node)
        # if there's at least one vaild link add the node to the network
        if len(visible_links) > 0:
            visible_links.sort(key=lambda x: x[2], reverse=True)
            link = visible_links.pop()
            self.infected.append(link[0])
            self.graph.add_node(link[0].gid, pos=link[0].xy())
            self.graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
            if len(visible_links) > 1:
                link = visible_links.pop()
                self.graph.add_edge(link[0].gid, link[1].gid, weight=link[2])
            return True
        return False


if __name__ == '__main__':
    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"
    dataset = "quarrata"
    g = CN_Generator_Strategy1(DSN, dataset)
    g.main()
