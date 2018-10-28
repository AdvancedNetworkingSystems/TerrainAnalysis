from functools import partial
import pyproj
from shapely.ops import transform, cascaded_union

class Susceptible_Buffer():
    project = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:4326'),  # source coordinate system
        pyproj.Proj(init='epsg:3003'))  # destination coordinate system

    deproject = partial(
        pyproj.transform,
        pyproj.Proj(init='epsg:3003'),  # source coordinate system
        pyproj.Proj(init='epsg:4326'))  # destination coordinate system

    def set_shape(self, geoms):
        shape = cascaded_union(geoms)
        self.orig_shape = shape
        self.shape = transform(self.project, shape)

    def get_buffer(self, m):
        return transform(self.deproject, self.shape.buffer(m))


class NoGWError(Exception):
    pass
