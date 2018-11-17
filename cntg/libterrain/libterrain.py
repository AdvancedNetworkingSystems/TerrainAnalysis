import random
import shapely
from sqlalchemy import create_engine, and_
from psycopg2.pool import ThreadedConnectionPool
from sqlalchemy.orm import sessionmaker
from geoalchemy2.functions import GenericFunction
from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape, from_shape
from shapely.geometry import Point
import time
import matplotlib.pyplot as plt

from libterrain.link import Link, ProfileException
from libterrain.building import Building_CTR, Building_OSM
from libterrain.comune import Comune
from shapely import wkb
from shapely.ops import transform
import pyproj
from functools import partial

project = partial(
    pyproj.transform,
    pyproj.Proj(init='EPSG:4326'),
    pyproj.Proj(init='EPSG:3003'))

pin = pyproj.Proj(init='EPSG:4326')
pout = pyproj.Proj(init='EPSG:3003')

class ST_MakeEnvelope(GenericFunction):
    name = 'ST_MakeEnvelope'
    type = Geometry


class terrain():
    def __init__(self, DSN, dataset, ple=2):
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

    def _profiles_osm(self, p1, tuple_pd):
        query = """WITH p1 as(
                                SELECT gid as gid1, ST_Centroid(geom) as pt FROM {5}
                                WHERE  gid = {2}
                            ),
                            p2 as(
                                SELECT gid as gid2, ST_Centroid(geom) as pt FROM {5}
                                WHERE  gid IN %s
                            ),
                            buffer AS(
                                SELECT gid1, gid2, ST_Buffer_Meters(ST_MakeLine(p1.pt, p2.pt), {4}) AS line FROM p1,p2
                            ),
                            patches AS (
                                SELECT pa FROM {1}
                                JOIN buffer ON PC_Intersects(pa, line)
                            ),
                            pa_pts AS (
                                SELECT PC_Explode(pa) AS pts FROM patches
                            )
                            SELECT gid1, gid2, ST_COLLECT(pts::geometry) as p FROM pa_pts JOIN buffer
                            ON ST_Intersects(line, pts::geometry)
                            GROUP BY gid1, gid2
                        """.format(self.srid, self.lidar_table, p1, tuple_pd, self.buff, self.building_table)
        self.cur.execute(query, (tuple_pd,))
        q_result = self.cur.fetchall()
        if self.cur.rowcount == 0:
            raise ProfileException("No profiles")
        # remove invalid points
        profiles = []
        for r in q_result:
            profile = []
            multipoint = wkb.loads(r[2], hex=True)
            p0 = Point(pyproj.transform(p1=pin, p2=pout, x=multipoint[0].x, y=multipoint[0].y))
            for point in multipoint:
                p = Point(pyproj.transform(p1=pin, p2=pout, x=point.x, y=point.y))
                if(point.z != -9999):
                    profile.append((p.distance(p0), float(point.z)))
            profile.sort(key=lambda x: x[0])
            uniq_profile = []
            # order preserving
            seen = {}
            for item in profile:
                marker = item[0]
                if marker in seen:
                    continue
                seen[marker] = 1
                uniq_profile.append(item)
            profiles.append({'src': r[0], 'dst': r[1], 'profile': uniq_profile, 'src_p': multipoint[0], 'dst_p': multipoint[-1]})
        return profiles

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
            self.building_table = 'ctr_firenze'
            print("Buildings from CTR")
        else:
            self.building_table = 'osm_centro'
            self.building_class = Building_OSM
            print("Buildings from OSM")

    def get_links(self, b1, set_b, h1=2, h2=2):
        """Calculate the path loss between two buildings_pair
        b1: source Building object
        b2: destination Building object
        h1: height of the antenna on the roof of b1
        h2: height of the antenna on the roof of b2
        """
        bs = [i.gid for i in set_b]
        b_dict = {el.gid: el for el in set_b}
        links = []
        try:
            profiles = self._profiles_osm(b1.gid, tuple(bs))
            for profile in profiles:
                phy_link = Link(profile['profile'], h1=h1, h2=h2, ple=self.ple, p1=profile['src_p'], p2=profile['dst_p'])
                if phy_link and phy_link.loss > 0:
                    link = {}
                    link['src'] = b1
                    link['dst'] = b_dict[profile['dst']]
                    link['loss'] = phy_link.loss
                    link['src_orient'] = phy_link.Aorient
                    link['dst_orient'] = phy_link.Borient
                    links.append(link)
            # fig = plt.figure()
            # link.plot(fig, pltid=221, text="prova")
            # plt.show()
        except (ZeroDivisionError, ProfileException) as e:
            print(e)
            return []
        return links

    def get_building_gid(self, gid):
        return self.building_class.get_building_gid(self.session, gid)

    def get_buildings(self, shape):
        b = self.building_class.get_buildings(self, shape, area=self.polygon_area)
        return b
