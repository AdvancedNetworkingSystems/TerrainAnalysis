from psycopg2.pool import ThreadedConnectionPool
from building import Building
from link import Link
import random


class terrain():
    def __init__(self, DSN, working_area, dataset):
        self.DSN = DSN
        self.working_area = working_area
        self.dataset = dataset
        # Connection to PSQL
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        conn = self.tcp.getconn()
        self.cur = conn.cursor()
        self.srid = '4326'
        self.dataset = dataset
        self.working_area = working_area
        self._set_dataset()
        self._get_buildings()

    def _set_dataset(self):
        if self.dataset == 'toscana':
            self.osm_table = 'centro_buildings'
            self.lidar_table = 'lidar_toscana'
            self.buff = 0.5  # 1 point per meter
        elif self.dataset == 'lyon':
            self.osm_table = 'lyon_buildings'
            self.lidar_table = 'lidar_lyon'
            self.buff = 0.15  # 3-5 point per meter
        elif self.dataset == 'lyon_srtm':
            self.osm_table = 'lyon_buildings'
            self.lidar_table = 'srtm_lyon'
            self.buff = 12.5  # 1/25 point per meter
        else:
            raise Exception("Dataset not found")

    def _get_buildings(self):
        self.cur.execute("""SELECT gid, z, ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom))  FROM {0}
                            WHERE geom && ST_MakeEnvelope({1}, {2}, {3}, {4}, {5})
                        """.format(self.osm_table,
                                   self.working_area[0], self.working_area[1], self.working_area[2], self.working_area[3],
                                   self.srid))
        self.buildings = []
        for b in self.cur:
            self.buildings.append(Building(b))

    def get_building(self):
        return random.choice(self.buildings)
    
    def _profile_osm(self, id1, id2):
        self.cur.execute("""WITH p1 AS(
                            SELECT ST_Centroid(geom) as pt FROM {0}
                            WHERE  gid={2}
                            ),
                            p2 as(
                                SELECT ST_Centroid(geom) as pt FROM {0}
                                WHERE  gid={3}
                            ),
                            buffer AS(
                                SELECT ST_Buffer_Meters(ST_MakeLine(p1.pt, p2.pt), {4}) AS line FROM p1,p2
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
                                PC_Get(pts, 'z') AS z, ST_Distance(pts::geometry, p1.pt, true) as distance
                                FROM building_pts, p1
                                )
                            SELECT DISTINCT on (lidar.distance)
                            lidar.distance,
                            lidar.z
                            FROM lidar ORDER BY lidar.distance;
                        """.format(self.osm_table, self.lidar_table, id1, id2, self.buff))
        q_result = self.cur.fetchall()
        if self.cur.rowcount == 0:
            raise ProfileException("No profile")
        # remove invalid points
        profile = filter(lambda a: a[0] != -9999, q_result)
        # cast everything to float
        d, y = zip(*profile)
        y = [float(i) for i in y]
        d = [float(i) for i in d]
        profile = zip(d, y)
        return profile
        
    def get_loss(self, b1, b2):
        profile = self._profile_osm(b1.gid, b2.gid)
        try:
            link = Link(profile)
        except (ZeroDivisionError, ProfileException), e:
            return -1
        return link.loss

if __name__ == '__main__':
    DSN = "postgresql://gabriel:qwerasdf@192.168.184.102/postgres"
    #DSN = "postgresql://dboperator:pippo123@192.168.160.11/terrain_ans"
    working_area = (4.8411, 45.7613, 4.8528, 45.7681)
    dataset = 'lyon'
    t = terrain(DSN, working_area, dataset)
    b1 = t.get_building()
    b2 = t.get_building()
    print(t.get_loss(b1, b2))
