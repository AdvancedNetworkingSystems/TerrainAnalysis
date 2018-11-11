from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Unicode, and_
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
import numpy as np
import shapely

Base = declarative_base()


class Building(Base):
    __abstract__ = True
    gid = Column(Integer, primary_key=True)
    geom = Column(Geometry('POLYGON'))

    def __repr__(self):
        return str(self.gid)

    def shape(self):
        return to_shape(self.geom)

    def coords(self):
        return self.shape().centroid

    def xy(self):
        return (self.coords().x, self.coords().y)

    @classmethod
    def get_building_gid(cls, session, gid):
        """Get building by gid
        gid: identifier of building
        """
        building = session.query(cls) \
            .filter_by(gid=gid).first()
        return building

    @staticmethod
    def get_buildings(libterrain, shape):
        raise NotImplementedError


class Building_CTR(Building):
    __tablename__ = 'ctr_firenze'
    foglio = Column(String)
    codice = Column(String)
    record = Column(Integer)
    topon = Column(String)
    area = Column(Float)
    identif = Column(String)

    def __str__(self):
        return "Building ID: {0} \nLongitude: {1} \nLatitude: {2} \nCodice: {3}".format(self.gid, self.coords().x, self.coords().y, self.codice)

    @staticmethod
    def get_buildings(libterrain, shape, area=None):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        if area:
            wkb_area = from_shape(area, srid=libterrain.srid)
            building = libterrain.session.query(Building_CTR) \
                .filter(Building_CTR.codice.in_(libterrain.codici),
                        Building_CTR.geom.intersects(wkb_element),
                        Building_CTR.geom.intersects(wkb_area))
        else:
            building = libterrain.session.query(Building_CTR) \
                .filter(and_(Building_CTR.codice.in_(libterrain.codici),
                             Building_CTR.geom.intersects(wkb_element)))
        return building.all()
    
    @staticmethod
    def count_buildings(libterrain, shape):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        building = libterrain.session.query(Building_CTR) \
            .filter(and_(Building_CTR.codice.in_(libterrain.codici),
                         Building_CTR.geom.intersects(wkb_element)))
        return building.count()


class Building_OSM(Building):
    __tablename__ = 'osm_centro'
    osm_id = Column(Integer)
    code = Column(Integer)
    fclass = Column(String)
    name = Column(Unicode)
    t_type = Column('type', String)

    def __str__(self):
        if(len(self.name) > 0):
            return "Name: {4} \nBuilding ID: {0} \nLongitude: {1} \nLatitude: {2} \nCodice: {3}"\
                .format(self.gid, self.coords().x, self.coords().y, self.codice, self.name)
        return "Building ID: {0} \nLongitude: {1} \nLatitude: {2} \nCodice: {3}"\
            .format(self.gid, self.coords().x, self.coords().y, self.codice)

    @staticmethod
    def get_buildings(libterrain, shape, area=None):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        if area:
            wkb_area = from_shape(area, srid=libterrain.srid)
            building = libterrain.session.query(Building_CTR) \
                .filter(Building_CTR.geom.intersects(wkb_element),
                        Building_CTR.geom.intersects(wkb_area))
        else:
            building = libterrain.session.query(Building_OSM) \
                .filter(Building_OSM.geom.intersects(wkb_element))
        return building.all()

    @staticmethod
    def count_buildings(libterrain, shape):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        building = libterrain.session.query(Building_OSM) \
            .filter(Building_OSM.geom.intersects(wkb_element))
        result = building.count()
        return result
