import math
import psycopg2
import numpy
import os
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from shapely.geometry import *
from shapely.affinity import rotate, translate, scale
import itertools
from random import shuffle


class terrain_RF:
    def __init__(self, cur, dataset, frequency=5):
        self.c = 0.299792458  # Gm/s
        self.f = frequency  # GHz
        self.l = self.c / self.f  # m
        self.R = 6370986  # 6371km
        self.srid = '4326'
        self.cur = cur
        self.dataset = dataset
        if self.dataset == 'toscana':
            self.osm_table = 'centro_buildings'
            self.lidar_table = 'lidar_toscana'
            self.buff = 0.5  #1 point per meter
        elif self.dataset == 'lyon':
            self.osm_table = 'lyon_buildings'
            self.lidar_table = 'lidar_lyon'
            self.buff = 0.15  #1 point each 30cm
        else:
            raise Exception("Dataset not found")

    def profile_osm(self, p1, p2):
        self.cur.execute("""   WITH p1 AS(
                            SELECT ST_Centroid(geom) as pt FROM {0}
                            WHERE  gid={2}
                        ),
                        p2 as(
                            SELECT ST_Centroid(geom) as pt FROM {0}
                            WHERE  gid={3}
                        ),
                        building AS(
                            SELECT ST_Buffer_Meters(ST_MakeLine(p1.pt, p2.pt), {4}) AS line FROM p1,p2
                        ),
                        lidar AS(
                            WITH
                            patches AS (
                            SELECT pa FROM {1}
                            JOIN building ON PC_Intersects(pa, line)
                            ),
                            pa_pts AS (
                            SELECT PC_Explode(pa) AS pts FROM patches
                            ),
                            building_pts AS (
                            SELECT pts, line FROM pa_pts JOIN building
                            ON ST_Intersects(line, pts::geometry)
                            )
                            SELECT
                            PC_Get(pts, 'z') AS z, ST_Distance(pts::geometry, p1.pt, true) as distance
                            FROM building_pts, p1
                            )
                        SELECT lidar.z, lidar.distance  FROM lidar ORDER BY distance;""".format(self.osm_table, self.lidar_table, p1, p2, self.buff))
        q_result = cur.fetchall()
        if cur.rowcount == 0:
            raise Exception("No profile")
        # remove invalid points
        profile = filter(lambda a: a[0] != -9999, q_result)
        n_points = len(profile)
        # cast everything to float
        y, d = zip(*profile)
        y = [float(i) for i in y]
        d = [float(i) for i in d]
        # Close the ring to make a polygon
        #print "%d points, %f meters: %f density ppm"%(n_points, d[-1], n_points/d[-1])
        min_y = min(y)
        y.insert(0, min_y)
        d.insert(0, d[0])
        y.append(min_y)
        d.append(d[-1])
        y.append(y[0])
        d.append(d[0])
        return zip(d, y)

    def apply_earth_curvature(self, profile):
        d, y = zip(*profile)
        n_points = len(d)
        y_curved = [None] * n_points
        for i in range(n_points):
            y_curved[i] = y[i] - (math.sqrt(d[i]**2 + self.R**2) - self.R)
        return d, y_curved

    def fresnel(self, A, B, clearance=False):
        distance = A.distance(B)
        f1 = math.sqrt(self.l * distance / 4)
        radius = f1
        if clearance:
            radius *= 0.6
        S = Point(A.x + distance / 2, A.y)
        alpha = math.atan2(B.y - A.y, B.x - A.x)
        C = S.buffer(distance / 2)
        C = scale(C, 1, radius / (distance / 2))
        C = rotate(C, alpha, origin=A, use_radians=True)
        return C

    def kirkoff_fresnel(self, A, B, knife):
        d1 = knife.centroid.distance(A)
        d2 = knife.centroid.distance(B)
        v = knife.height * math.sqrt(2 / self.l * (1 / d1 + 1 / d2))
        loss = 6.9 + 20 * math.log10(math.sqrt((v - 0.1)**2 + 1) + v - 0.1)
        return loss

    def FSPL(self, distance):
        return 20 * math.log10(4 * math.pi * distance / self.l)

    def knife_method(self, A, B, knifes):
        loss = 0
        knifes_list = []
        if isinstance(knifes, MultiPolygon):
            for knife in knifes:
                minx, miny, maxx, maxy = knife.bounds
                knife.height = maxy - miny
                knifes_list.append(knife)
            knifes_list.sort(key=lambda x: x.height, reverse=True)
            loss += self.kirkoff_fresnel(A, B, knife=knifes_list.pop(0))
            loss += self.kirkoff_fresnel(A, B, knife=knifes_list.pop(0))
        else:
            minx, miny, maxx, maxy = knifes.bounds
            knifes.height = maxy - miny
            loss += self.kirkoff_fresnel(A, B, knife=knifes)
        return loss

    def sommer_obs(self, A, B, obstacles):
        # Unused loss trough buildings
        loss = 0
        n_obst = len(obstacles)
        tot_dist = 0
        for line in obstacles:
            tot_dist += line.length
        loss += self.FSPL(A.distance(B) - tot_dist)
        #print "There are %d obstacles for a length of %f" % (n_obst, tot_dist)
        loss += 9.6 * 2 * n_obst + 0.45 * tot_dist
        return loss

    def link_calculator(self, b1, b2, h1=1, h2=1, plot=False):
        profile = self.profile_osm(b1, b2)
        d, y = self.apply_earth_curvature(profile)
        shap_profile = Polygon(zip(d, y))
        A = Point(d[1], y[1] + h1)
        B = Point(d[-3], y[-3] + h2)
        # plot fresnel zone
        c = 0.299792458  # Gm/s
        # Calculate 60% of first fresnel ellypse
        fig, ax = plt.subplots()
        C60 = self.fresnel(A, B, clearance=True)
        LOS = LineString([A, B])
        ax.plot(d, y, label="Terrain profile")
        C = self.fresnel(A, B)
        f_x, f_y = C.exterior.xy
        ax.plot((A.x, B.x), (A.y, B.y), 'ro', label="Antennas")
        ax.plot(f_x, f_y, label='First fresnel zone')
        # plot 60% of fresnel zone
        f_x, f_y = C60.exterior.xy
        ax.plot(f_x, f_y, label='60% of First fresnel zone')
        # # plot LOS line
        l_x, l_y = LOS.xy
        ax.plot(l_x, l_y, label="Line of Sight")
        if shap_profile.intersects(LOS):
            # Los passing trough terrain
            obstacles = shap_profile.intersection(LOS)
            status = 0  # LOS OBSTR
            try:
                loss = self.sommer_obs(A, B, obstacles)
            except:
                loss = 0
                status = 4
        else:
            # LOS is free
            loss = 0
            status = 1  # LOS FREE
            if shap_profile.intersects(C60):
                # Fresnel unclear
                knifes = C60.intersection(shap_profile)
                loss += self.knife_method(A, B, knifes)
                #print "The 60% of the 1st fresnel zone is unclear"
                status += 2  # F60 obstructed
            loss += self.FSPL(A.distance(B))
            #print "The path is free with loss between A and B distant %f m is %f" % (A.distance(B), loss)
        plt.xlabel("distance (m)")
        plt.ylabel("height a.s.l. (m)")
        plt.legend(loc="upper left", bbox_to_anchor=(1,1))
        if status is 0:
            status_t = "LOS Obstructed"
        elif status is 1:
            status_t = "LOS Free"
        elif status is 3:
            status_t = "Fresnel Obstructed"
            if plot:
                plt.show()
        elif status is 4:
            status_t = "Error"
        text = "LOSS: %fdB\n"%((loss))+status_t
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=14,verticalalignment='top', bbox=props)
        plt.close()
        # plt.axes().set_aspect('equal')
        return loss, status

    def get_buildings(self, xmin, ymin, xmax, ymax):
        self.cur.execute("""SELECT gid FROM {0}
                            WHERE geom && ST_MakeEnvelope({1}, {2}, {3}, {4}, {5})
                        """.format(self.osm_table, xmin, ymin, xmax, ymax, self.srid))
        buildings = list(self.cur)
        return buildings
        
    def get_buildings_height(self, buildings, filename='heigts.csv'):
        heights = []
        if os.path.isfile(filename):
            with open("heigts.csv", 'rb') as f:
                csv_heights = list(csv.reader(f))
                for building in csv_heights[1:]:
                    heights.append((int(building[0]), float(building[1][1:])))
        else:
            for building in buildings:
                self.cur.execute("""WITH
                                -- Get the buildings
                                building AS (
                                  SELECT gid, geom FROM {0}
                                  WHERE gid = {2}
                                ),
                                -- All the patches that intersect buildings
                                patches AS (
                                  SELECT pa FROM {1}
                                  JOIN building ON PC_Intersects(pa, geom)
                                ),
                                -- All the points in that patch
                                pa_pts AS (
                                  SELECT PC_Explode(pa) AS pts FROM patches
                                ),
                                -- All the points in our one building
                                building_pts AS (
                                  SELECT pts, gid FROM pa_pts JOIN building
                                  ON ST_Intersects(geom, pts::geometry)
                                )
                                -- Summarize those points by elevation
                                SELECT Avg(PC_Get(pts, 'z')) AS height
                                FROM building_pts
                                """.format(self.osm_table, self.lidar_table, building[0]))
                result = self.cur.fetchall()
                with open("heigts.csv", 'a') as f:
                    print >> f, "%d, %f"%(building[0], float(result[0][0]))
                heights.append((int(building[0]), float(result[0][0])))
        return heights

if __name__ == '__main__':
    conn = psycopg2.connect(dbname='postgres', port=5432, user='gabriel', password='qwerasdf', host='192.168.184.102')
    cur = conn.cursor()
    tf = terrain_RF(cur=cur, dataset='toscana')
    buildings = tf.get_buildings(11.234, 43.758, 11.285, 43.787)
    heights = tf.get_buildings_height(buildings)
    dic_h = dict(heights)
    gid, h = zip(*heights)
    mean_height = numpy.mean(h)
    buildings_pair = itertools.combinations(buildings, 2)
    for building in buildings_pair:
        id1 = building[0][0]
        id2 = building[1][0]
        if dic_h[id1] >= mean_height and dic_h[id2] >= mean_height:
            loss, status = tf.link_calculator(id1, id2, plot=False)
            if status is 1 or status is 3:
                with open("links.csv", 'a') as fl:
                    print >> fl, "%s,%s,%d,%f" % (id1,id2,status,loss)
                print "%s to %s has status %d with loss %f, received pwr %f" % (id1, id2, status, loss, 23+16+16-loss)
        else:
            pass
            #print "%s to %s is unprobable to be feasible"% (id1, id2)
# 
    # loss, status = tf.link_calculator(1465205, 1466188, plot=True)
    #print(tf.link_calculator(841985, 73907, plot=True))
    #print(tf.link_calculator(752497, 73907, 5, 5, plot=True))

    # for i in range(10):
    #     for j in range(10):
    #         id1 = 1465200 + i
    #         id2 = 1466180 + j
    #         try:
    #             loss, status = tf.link_calculator(id1, id2, 5, 5, plot=False, buf = 0.5)
    #             if status != 0:
    #                 print "%s to %s has status %d with loss %f" % (id1, id2, status, loss)
    #         except Exception as e:
    #             print e
