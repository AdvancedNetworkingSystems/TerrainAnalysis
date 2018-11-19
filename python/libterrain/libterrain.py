import random
import shapely
from sqlalchemy import create_engine, and_
from psycopg2.pool import PersistentConnectionPool, ThreadedConnectionPool
from sqlalchemy.orm import sessionmaker
from geoalchemy2.functions import GenericFunction
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
import multiprocessing as mp
from more_itertools import chunked
from libterrain.link import Link, ProfileException
from libterrain.building import Building_CTR, Building_OSM
from libterrain.comune import Comune


class ST_MakeEnvelope(GenericFunction):
    name = 'ST_MakeEnvelope'
    type = Geometry


class terrain():
    def __init__(self, DSN, dataset, ple, processes=1):
        self.DSN = DSN
        self.dataset = dataset
        self.ple = ple
        self.processes = processes
        self.querier = []
        self.srid = '4326'
        # Connection to PSQL
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        engine = create_engine(DSN, client_encoding='utf8', echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self._set_dataset()
        # MT Queryier
        self.workers_query_order_q = mp.Queue()
        self.workers_query_result_q = mp.Queue()
        self.conns = [self.tcp.getconn() for i in range(processes)]
        for i in range(self.processes):
            t = mp.Process(target=self.querty_worker, args=[self.conns[i]])
            self.querier.append(t)
            t.daemon = True
            t.start()

    def querty_worker(self, conn):
        while(True):
            order = self.workers_query_order_q.get(block=True)
            link = self._profile_osm(order, conn)
            self.workers_query_result_q.put(link)

    def _set_building_filter(self, codici=['0201', '0202', '0203', '0211',
                                           '0212', '0215', '0216', '0223',
                                           '0224', '0225', '0226', '0227', '0228']):
        """Set the filter for the building from CTR.
        codici: set of strings representing the codici
            '0201': Civil Building
            '0202': Industrial Building
            '0203': Religion Building
            '0204': Unfinished Building
            '0206': Portico
            '0207': Baracca/Edicola
            '0208': Tettoia/Pensilina
            '0209': Tendone Pressurizzato
            '0210': Serra
            '0211': Casello / Stazione Ferroviaria
            '0212': Centrale Elettrica/Sottostazione
            '0215': Capannone Vivaio
            '0216': Stalla/ Fienile
            '0223': Complesso Ospedaliero
            '0224': Complesso Scolastico
            '0225': Complesso Sportivo
            '0226': Complesso Religioso
            '0227': Complesso Sociale
            '0228': Complesso Cimiteriale
            '0229': Campeggio/ Villaggio
        """
        self.codici = codici

    def _set_dataset(self):
        self.lidar_table = 'lidar_toscana'
        self.buff = 0.5  # 1 point per metre
        comune = Comune.get_by_name(self.session, self.dataset.upper())
        self.polygon_area = comune.shape()
        self._set_building_filter()
        n_build_ctr = Building_CTR.count_buildings(self, self.polygon_area)
        n_build_osm = Building_OSM.count_buildings(self, self.polygon_area)
        if n_build_ctr > n_build_osm:
            self.building_class = Building_CTR
            print("Buildings from CTR")
        else:
            self.building_class = Building_OSM
            print("Buildings from OSM")

    def get_loss(self, b1, b2, h1=2, h2=2):
        """Calculate the path loss between two buildings_pair
        b1: source Building object
        b2: destination Building object
        h1: height of the antenna on the roof of b1
        h2: height of the antenna on the roof of b2
        """
        return self.get_link(b1, b2, h1, h2).loss

    def get_link_parallel(self, source_b, dst_b_list, h1=2, h2=2):
        """Calculate the path loss between two lists of building
        """
        links = []
        params = [{'src': source_b,
                   'dst': dst_b_list[i],
                   'srid': self.srid,
                   'lidar_table': self.lidar_table,
                   'buff': self.buff,
                   'h1': h1,
                   'h2': h2
                   }for i in range(len(dst_b_list))]
        # add orders in the queue
        for order in params:
            self.workers_query_order_q.put(order)
        # wait for all the orders to come back
        while len(links) < len(dst_b_list):
            links.append(self.workers_query_result_q.get(block=True))
        return links

    def _profile_osm(self, param_dict, con):
        # loop over all the orders that we have and process them sequentially.
        src = param_dict['src']
        dst = param_dict['dst']
        srid = param_dict['srid']
        lidar_table = param_dict['lidar_table']
        buff = param_dict['buff']
        h1 = param_dict['h1']
        h2 = param_dict['h2']
        cur = con.cursor()
        p1 = src.coords().wkt
        p2 = dst.coords().wkt
        #TODO: use query formatting and not string formatting
        cur.execute("""WITH buffer AS(
                                SELECT
                                ST_Buffer_Meters(
                                    ST_MakeLine(
                                                ST_GeomFromText('{2}', {0}),
                                                ST_GeomFromText('{3}', {0})
                                                ), {4}
                                ) AS line
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
                                PC_Get(pts, 'z') AS z,
                                ST_Distance(pts::geometry,
                                            ST_GeomFromText('{2}', {0}),
                                            true
                                            ) as distance
                                FROM building_pts
                                )
                            SELECT DISTINCT on (lidar.distance)
                            lidar.distance,
                            lidar.z
                            FROM lidar ORDER BY lidar.distance;
                        """.format(srid, lidar_table, p1, p2, buff))
        q_result = cur.fetchall()
        if cur.rowcount == 0:
            return None
        # remove invalid points
        # TODO: Maybe DBMS can clean this up
        profile = filter(lambda a: a[0] != -9999, q_result)
        # cast everything to float
        d, y = zip(*profile)
        y = [float(i) for i in y]
        d = [float(i) for i in d]
        profile = list(zip(d, y))
        try:
            phy_link = Link(profile, src.coords(), dst.coords(), h1, h2)
            if phy_link and phy_link.loss > 0:
                link = {}
                link['src'] = src
                link['dst'] = dst
                link['loss'] = phy_link.loss
                link['src_orient'] = phy_link.Aorient
                link['dst_orient'] = phy_link.Borient
                return link
        except (ZeroDivisionError, ProfileException) as e:
            pass
        return None

    def get_building_gid(self, gid):
        return self.building_class.get_building_gid(self.session, gid)

    def get_buildings(self, shape):
        b = self.building_class.get_buildings(self, shape, area=self.polygon_area)
        return b
