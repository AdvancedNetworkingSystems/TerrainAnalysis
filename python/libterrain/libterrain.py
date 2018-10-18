import random
import shapely
from sqlalchemy import create_engine, and_
from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy.orm import sessionmaker
from geoalchemy2.functions import GenericFunction
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point

from link import Link, ProfileException
from building import Building_CTR


class ST_MakeEnvelope(GenericFunction):
    name = 'ST_MakeEnvelope'
    type = Geometry


class terrain():
    def __init__(self, DSN, dataset, codici):
        self.DSN = DSN
        self.dataset = dataset
        # Connection to PSQL
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        conn = self.tcp.getconn()
        self.cur = conn.cursor()
        engine = create_engine(DSN, echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.srid = '4326'
        self._set_dataset()
        self.set_building_filter(codici)
        self._get_buildings_ctr()
        
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

    def _set_dataset(self):
        self.lidar_table = 'lidar_toscana'
        self.buff = 0.5  # 1 point per metre
        if self.dataset == "firenze":
            self.working_area = [11.1610, 43.8487, 11.3026, 43.7503]
        elif self.dataset == "pontremoli":
            self.working_area = [9.7848, 44.4507, 9.9864, 44.3324]
        elif self.dataset == "quarrata":
            self.working_area = [10.9165, 43.8987, 11.0816, 43.7995]

    def _get_buildings_ctr(self):
        self.buildings = self.session.query(Building_CTR) \
            .filter(and_(Building_CTR.codice.in_(self.codici),
                         Building_CTR.geom.intersects(ST_MakeEnvelope(*self.working_area))
                         )
                    ).all()

    def set_building_filter(self, codici):
        """Set the filter for the building from CTR.
        codici: set of strings representing the codici
        """
        self.codici = codici

    def get_random_building(self):
        """Extract a random building from the buildings of the working area
        """
        return random.choice(self.buildings)

    def get_building(self, point):
        """Get the building around a point
        point: shapely Point object
        """
        wkb_element = from_shape(point, srid=self.srid)
        building = self.session.query(Building_CTR) \
            .filter(and_(Building_CTR.codice.in_(self.codici),
                         Building_CTR.geom.intersects(wkb_element)))
        return building.first()

    def get_loss(self, b1, b2, h1=2, h2=2):
        """Calculate the path loss between two buildings_pair
        b1: source Building object
        b2: destination Building object
        h1: height of the antenna on the roof of b1
        h2: height of the antenna on the roof of b2
        """
        p1 = to_shape(b1.geom).centroid.wkt
        p2 = to_shape(b2.geom).centroid.wkt
        try:
            profile = self._profile_osm(p1, p2)
            link = Link(profile, h1, h2)
        except (ZeroDivisionError, ProfileException) as e:
            return -1
        return link.loss

if __name__ == '__main__':
    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"
    #dataset = "firenze"
    #dataset = "pontermoli"
    dataset = "quarrata"
    t = terrain(DSN, dataset, ['0201', '0202'])
    # p1 = Point(11.2029274, 43.8485573)
    # b1 = t.get_building(p1, ['0201', '0202'])
    while 1:
        b1 = t.get_random_building()
        b2 = t.get_random_building()
        print(t.get_loss(b1,b2))
