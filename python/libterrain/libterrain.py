import random
import shapely
from sqlalchemy import create_engine, and_
from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy.orm import sessionmaker
from geoalchemy2.functions import GenericFunction
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point

import matplotlib.pyplot as plt

from libterrain.link import Link, ProfileException
from libterrain.building import Building_CTR, Building_OSM
from libterrain.comune import Comune


class ST_MakeEnvelope(GenericFunction):
    name = 'ST_MakeEnvelope'
    type = Geometry


class terrain():
    def __init__(self, DSN, dataset, ple):
        self.DSN = DSN
        self.dataset = dataset
        self.ple = ple
        # Connection to PSQL
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        conn = self.tcp.getconn()
        self.cur = conn.cursor()
        engine = create_engine(DSN, client_encoding='utf8', echo=False)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.srid = '4326'
        self._set_dataset()

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
        #if self.dataset == "firenze":
        #     self.working_area = [11.1610, 43.8487, 11.3026, 43.7503]
        #     self.building_class = Building_OSM
        # elif self.dataset == "pontremoli":
        #     self.working_area = [9.7848, 44.4507, 9.9864, 44.3324]
        #     self.building_class = Building_CTR
        #     self._set_building_filter(['0201'])
        # elif self.dataset == "quarrata":
        #     self.working_area = [10.9165, 43.8987, 11.0816, 43.7995]
        #     self.building_class = Building_OSM

    def get_loss(self, b1, b2, h1=2, h2=2):
        """Calculate the path loss between two buildings_pair
        b1: source Building object
        b2: destination Building object
        h1: height of the antenna on the roof of b1
        h2: height of the antenna on the roof of b2
        """
        p1 = b1.coords().wkt
        p2 = b2.coords().wkt
        try:
            profile = self._profile_osm(p1, p2)
            link = Link(profile, h1, h2, self.ple, p1=b1.coords(), p2=b2.coords())
            # fig = plt.figure()
            # link.plot(fig, pltid=221, text="prova")
            # plt.show()
        except (ZeroDivisionError, ProfileException) as e:
            return -1
        return link.loss

    def get_link(self, b1, b2, h1=2, h2=2):
        """Calculate the path loss between two buildings_pair
        b1: source Building object
        b2: destination Building object
        h1: height of the antenna on the roof of b1
        h2: height of the antenna on the roof of b2
        """
        p1 = b1.coords().wkt
        p2 = b2.coords().wkt
        try:
            profile = self._profile_osm(p1, p2)
            link = Link(profile, h1=h1, h2=h2, ple=self.ple, p1=b1.coords(), p2=b2.coords())
            # fig = plt.figure()
            # link.plot(fig, pltid=221, text="prova")
            # plt.show()
        except (ZeroDivisionError, ProfileException) as e:
            return None
        return link


    def get_building_gid(self, gid):
        return self.building_class.get_building_gid(self.session, gid)

    def get_buildings(self, shape):
        b = self.building_class.get_buildings(self, shape, area=self.polygon_area)
        return b
