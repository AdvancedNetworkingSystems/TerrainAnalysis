from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Unicode, and_
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
import shapely

Base = declarative_base()


class Comune(Base):
    __tablename__ = 'comuni_toscana'
    gid = Column(Integer, primary_key=True)
    nome = Column(String)
    codcom = Column(String)
    codcatasto = Column(String)
    sigla_prov = Column(String)
    distr_asl = Column(String)
    asl = Column(String)
    geom = Column(Geometry('POLYGON'))

    def __repr__(self):
        return self.nome

    def shape(self):
        return to_shape(self.geom)

    @classmethod
    def get_by_gid(cls, session, gid):
        """Get building by gid
        gid: identifier of building
        """
        element = session.query(cls) \
            .filter_by(gid=gid).first()
        return element
    
    @classmethod
    def get_by_name(cls, session, name):
        """Get building by gid
        gid: identifier of building
        """
        element = session.query(cls) \
            .filter_by(nome=name).first()
        return element
