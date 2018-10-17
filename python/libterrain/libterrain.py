from psycopg2.pool import ThreadedConnectionPool
from link import Link
import random
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from geoalchemy2.functions import GenericFunction
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
import shapely

from building import Building_CTR

class ST_MakeEnvelope(GenericFunction):
    name = 'ST_MakeEnvelope'
    type = Geometry

class terrain():
    def __init__(self, DSN, working_area):
        self.DSN = DSN
        self.working_area = working_area
        # Connection to PSQL
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        conn = self.tcp.getconn()
        self.cur = conn.cursor()
        engine = create_engine(DSN, echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.srid = '4326'
        self.working_area = working_area
        self._set_dataset()
        self._get_buildings_ctr(codici=['0201','0202'])

    def _set_dataset(self):
        self.lidar_table = 'lidar_toscana'
        self.buff = 0.5  # 1 point per meter
        

    def _get_buildings_ctr(self, codici):
        self.buildings = self.session.query(Building_CTR) \
            .filter(and_(Building_CTR.codice.in_(codici),
                         Building_CTR.geom.intersects(ST_MakeEnvelope(*self.working_area))
                         )
                    ).all()

    def get_building(self):
        return random.choice(self.buildings)
    
    def _profile_osm(self, p1, p2):
        self.cur.execute("""WITH buffer AS(
                                SELECT ST_Buffer_Meters(ST_MakeLine(ST_GeomFromText('{2}', {0}), ST_GeomFromText('{3}', {0})), {4}) AS line
                            ),
                            lidar AS(
                                WITH
                                patches AS (
                                SELECT pa FROM {1}
                                JOIN buffer ON PC_Intersects(pa, line)
                                ),
                                pa_pts AS (
                                SELECT PC_Explode(pa) AS pts FROM patches
                                ),
                                building_pts AS (
                                SELECT pts, line FROM pa_pts JOIN buffer
                                ON ST_Intersects(line, pts::geometry)
                                )
                                SELECT
                                PC_Get(pts, 'z') AS z, ST_Distance(pts::geometry, ST_GeomFromText('{2}', {0}), true) as distance
                                FROM building_pts
                                )
                            SELECT DISTINCT on (lidar.distance)
                            lidar.distance,
                            lidar.z
                            FROM lidar ORDER BY lidar.distance;
                        """.format(self.srid, self.lidar_table, p1, p2, self.buff))
        q_result = self.cur.fetchall()
        if self.cur.rowcount == 0:
            raise ProfileException("No profile")
        # remove invalid points
        profile = filter(lambda a: a[0] != -9999, q_result)
        # cast everything to float
        d, y = zip(*profile)
        y = [float(i) for i in y]
        d = [float(i) for i in d]
        profile = list(zip(d, y))
        return profile
        
    def get_loss(self, b1, b2, h1=2, h2=2):
        p1 = to_shape(b1.geom).centroid.wkt
        p2 = to_shape(b2.geom).centroid.wkt
        profile = self._profile_osm(p1, p2)
        try:
            link = Link(profile, h1, h2)
        except (ZeroDivisionError, ProfileException) as e:
            return -1
        return link.loss

if __name__ == '__main__':
    DSN = "postgresql://dboperator:secret@192.168.160.11/terrain_ans"
    working_area = [11.26127, 43.77333, 11.27136, 43.76695]
    t = terrain(DSN, working_area)
    b1 = t.get_building()
    b2 = t.get_building()
    print(b1)
    print(t.get_loss(b1, b2))
