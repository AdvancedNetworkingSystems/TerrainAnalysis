from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Unicode, and_
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
import numpy as np
import shapely
from geoalchemy2.functions import ST_Intersects

Base = declarative_base()


class Building(Base):
    __abstract__ = True
    gid = Column(Integer, primary_key=True)
    geom = Column(Geometry('POLYGON'))
    height = 4

    def __hash__(self):
        return hash(self.gid)

    def __eq__(self, other):
        # equality performed only on gid (unique in the db)
        return self.gid == other.gid

    def __repr__(self):
        return str(self.gid)

    def shape(self):
        return to_shape(self.geom)

    def coords(self):
        return self.shape().representative_point()

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
    __tablename__ = 'ctr_toscana'
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
                        Building_CTR.geom.ST_Intersects(wkb_element),
                        Building_CTR.geom.ST_Intersects(wkb_area)) \
                .order_by(Building_CTR.gid)
        else:
            building = libterrain.session.query(Building_CTR) \
                .filter(and_(Building_CTR.codice.in_(libterrain.codici),
                             Building_CTR.geom.ST_Intersects(wkb_element))) \
                .order_by(Building_CTR.gid)

        return building.all()
    
    @staticmethod
    def count_buildings(libterrain, shape):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        building = libterrain.session.query(Building_CTR) \
            .filter(and_(Building_CTR.codice.in_(libterrain.codici),
                         Building_CTR.geom.ST_Intersects(wkb_element)))
        return building.count()


class Building_OSM(Building):
    __tablename__ = 'osm_centro'
    osm_id = Column(Integer)
    code = Column(Integer)
    fclass = Column(String)
    name = Column(Unicode)
    t_type = Column('type', String)

    def __str__(self):
        if(self.name):
            return "Name: {3} \nBuilding ID: {0} \nLongitude: {1} \nLatitude: {2}"\
                .format(self.gid, self.coords().x, self.coords().y, self.name)
        return "Building ID: {0} \nLongitude: {1} \nLatitude: {2}"\
            .format(self.gid, self.coords().x, self.coords().y)

    @staticmethod
    def get_buildings(libterrain, shape, area=None):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        if area:
            wkb_area = from_shape(area, srid=libterrain.srid)
            building = libterrain.session.query(Building_OSM) \
                .filter(and_(Building_OSM.geom.ST_Intersects(wkb_area),
                             Building_OSM.geom.ST_Intersects(wkb_element)))\
                .order_by(Building_OSM.gid)
        else:
            building = libterrain.session.query(Building_OSM) \
                .filter(Building_OSM.geom.ST_Intersects(wkb_element))\
                .order_by(Building_OSM.gid)
        return building.all()

    @staticmethod
    def count_buildings(libterrain, shape):
        """Get the buildings intersecting a shape
        point: shapely object
        """
        wkb_element = from_shape(shape, srid=libterrain.srid)
        building = libterrain.session.query(Building_OSM) \
            .filter(Building_OSM.geom.ST_Intersects(wkb_element))
        result = building.count()
        return result
