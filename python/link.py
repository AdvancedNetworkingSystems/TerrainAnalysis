from shapely.geometry import *
from shapely.affinity import rotate, translate, scale
from random import choice
import math
import matplotlib.pyplot as plt
import copy


class Link:
    def __init__(self, profile, h1=2, h2=2):
        # Constants
        self.R = 6370986  # 6371km
        self.c = 0.299792458  # Gm/s
        self.h1 = h1
        self.h2 = h2
        d, y = zip(*profile)
        self.d = copy.deepcopy(list(d))
        self.y = copy.deepcopy(list(y))
        self.A = Point(d[1], y[1] + h1)
        self.B = Point(d[-1], y[-1] + h2)
        self.distance = self.A.distance(self.B)

    def apply_earth_curvature(self):
        n_points = len(self.d)
        y_curved = [None] * n_points
        for i in range(n_points):
            y_curved[i] = self.y[i] - (math.sqrt(self.d[i]**2 + self.R**2) - self.R)
        #update point after curvature
        self.B = Point(self.d[-1], self.y[-1] + self.h2)
        self.distance = self.A.distance(self.B)
        self.y = y_curved
    
    def downscale(self, downscale):
        #keep 1 on n points
        old_profile = zip(self.d, self.y)
        profile = []
        for i in range(len(old_profile)):
            if i % downscale == 0:
                profile.append(choice(old_profile[i:i + downscale]))
        self.d, self.y = zip(*profile)
        self.y = list(self.y)
        self.d = list(self.d)
    
    def polygonize(self):
        min_y = min(self.y) - 10
        self.y.insert(0, min_y)
        self.d.insert(0, self.d[0])
        self.y.append(min_y)
        self.d.append(self.d[-1])
        self.y.append(self.y[0])
        self.d.append(self.d[0])
        self.terrain = Polygon(zip(self.d, self.y))

    def fresnel(self, clearance=False):
        f1 = math.sqrt(self.l * self.distance / 4)
        radius = f1
        if clearance:
            radius *= 0.6
        S = Point(self.A.x + self.distance / 2, self.A.y)
        alpha = math.atan2(self.B.y - self.A.y, self.B.x - self.A.x)
        C = S.buffer(self.distance / 2)
        C = scale(C, 1, radius / (self.distance / 2))
        C = rotate(C, alpha, origin=self.A, use_radians=True)
        return C

    def kirkoff_fresnel(self, knife):
        d1 = knife.centroid.distance(self.A)
        d2 = knife.centroid.distance(self.B)
        v = knife.height * math.sqrt(2 / self.l * (1 / d1 + 1 / d2))
        loss = 6.9 + 20 * math.log10(math.sqrt((v - 0.1)**2 + 1) + v - 0.1)
        return loss

    def FSPL(self, distance):
        return 20 * math.log10(4 * math.pi * distance / self.l)

    def knife_method(self, knifes):
        loss = 0
        knifes_list = []
        if isinstance(knifes, MultiPolygon):
            for knife in knifes:
                knife.height = -knife.distance(self.LOS)
                knifes_list.append(knife)
            knifes_list.sort(key=lambda x: x.height, reverse=True)
            loss += self.kirkoff_fresnel(knife=knifes_list.pop(0))
            loss += self.kirkoff_fresnel(knife=knifes_list.pop(0))
        else:
            knifes.height = -knifes.distance(self.LOS)
            loss += self.kirkoff_fresnel(knife=knifes)
        return loss

    def sommer_obs(self, obstacles):
        # Unused loss trough buildings
        loss = 0
        n_obst = len(obstacles)
        tot_dist = 0
        for line in obstacles:
            tot_dist += line.length
        loss += self.FSPL(self.distance - tot_dist)
        #print "There are %d obstacles for a length of %f" % (n_obst, tot_dist)
        loss += 9.6 * 2 * n_obst + 0.45 * tot_dist
        return loss

    def loss_calculator(self, frequency=5, downscale=0):
        self.f = frequency  # GHz
        self.l = self.c / self.f  # m
        self.apply_earth_curvature()
        if downscale>0:
            self.downscale(downscale)
        self.polygonize()
        self.F60 = self.fresnel(clearance=True)
        self.LOS = LineString([self.A, self.B])
        self.F = self.fresnel()
        if self.terrain.intersects(self.LOS):
            # Los passing trough terrain
            obstacles = self.terrain.intersection(self.LOS)
            self.status = 0  # LOS OBSTR
            self.loss = 0
            #self.loss = self.sommer_obs(obstacles)
        else:
            # LOS is free
            self.loss = 0
            self.status = 1  # LOS FREE
            if self.terrain.intersects(self.F60):
                # Fresnel unclear
                knifes = self.F60.intersection(self.terrain)
                self.loss += self.knife_method(knifes)
                self.status = 3  # F60 obstructed
            self.loss += self.FSPL(self.distance)
        return self.loss, self.status
        
    def plot(self):
        fig, ax = plt.subplots()
        ax.plot(d, y, label="Terrain profile")
        ax.plot((self.A.x, self.B.x), (self.A.y, self.B.y), 'ro', label="Antennas")
        f_x, f_y = self.F.exterior.xy
        ax.plot(f_x, f_y, label='First fresnel zone')
        # plot 60% of fresnel zone
        f_x, f_y = self.F60.exterior.xy
        ax.plot(f_x, f_y, label='60% of First fresnel zone')
        # # plot LOS line
        l_x, l_y = self.LOS.xy
        ax.plot(l_x, l_y, label="Line of Sight")
        plt.xlabel("distance (m)")
        plt.ylabel("height a.s.l. (m)")
        plt.legend(loc="upper left", bbox_to_anchor=(1,1))
        if self.status is 2:
            status_t = "LOS Obstructed"
        elif self.status is 1:
            status_t = "LOS Free"
        elif self.status is 3:
            status_t = "Fresnel Obstructed"
        elif self.status < 0:
            status_t = "Error"
        text = "LOSS: %fdB\n"%((self.loss))+status_t
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(0.05, 0.95, text, transform=ax.transAxes, fontsize=14,verticalalignment='top', bbox=props)
        # plt.axes().set_aspect('equal')
        plt.show()
