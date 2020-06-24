from shapely.geometry import Point

class Building:
    def __init__(self, osm_id, geom):
        self.gid = osm_id
        self.pos = (geom.x, geom.y)
        self.point = geom

    def __repr__(self):
        return str(self.gid)

    def __eq__(self, item):
        return self.gid == item.gid

    def __hash__(self):
        return hash(self.__dict__.values())

    def set_neighbors(graph_dict):
        if self.gid in graph_dict.keys():
            neighbors = grap_dict[gid].keys()[:,0]
        self.neighbors = set(neighbors)
