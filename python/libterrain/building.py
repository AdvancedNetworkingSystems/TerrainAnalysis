from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
import shapely

Base = declarative_base()


class Building_CTR(Base):
    __tablename__ = 'ctr_firenze'
    gid = Column(Integer, primary_key=True)
    foglio = Column(String)
    codice = Column(String)
    record = Column(Integer)
    topon = Column(String)
    area = Column(Float)
    identif = Column(String)
    geom = Column(Geometry('POLYGON'))

    def __str__(self):
        return "Building ID: {0} \nLongitude: {1} \nLatitude: {2}".format(self.gid, self.coords().x, self.coords().y)

    def shape(self):
        return to_shape(self.geom)

    def coords(self):
        return self.shape().centroid
