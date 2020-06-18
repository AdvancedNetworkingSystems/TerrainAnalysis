from functools import partial
import pyproj
from shapely.ops import transform, cascaded_union

class Susceptible_Buffer():
    def set_shape(self, geoms):
        shape = cascaded_union(geoms)
        self.orig_shape = shape
        self.shape = shape

    def get_buffer(self, m):
        return self.shape.buffer(m)


class NoGWError(Exception):
    pass
