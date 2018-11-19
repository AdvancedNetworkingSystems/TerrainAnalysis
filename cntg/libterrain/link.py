from shapely.geometry import *
from shapely.affinity import rotate, translate, scale
from random import choice
import math
import copy
import numpy as np
import math as m


class ProfileException(Exception):
    pass


class Link:
    def __init__(self, profile, p1, p2, h1=2, h2=2, ple=2):
        # Constants
        self.ple = ple
        self.R = 6370986  # 6371km
        self.c = 0.299792458  # Gm/s
        self.h1 = h1
        self.h2 = h2
        if profile is None or len(profile) < 2:
            raise ProfileException("No profile")
        d, y = zip(*profile)
        if not all(x < y for x, y in zip(d, d[1:])):
            raise ProfileException("Not monotonic list")
        self.d = copy.deepcopy(list(d))
        self.y = copy.deepcopy(list(y))
        self.A = Point(d[0], y[0] + h1)
        self.B = Point(d[-1], y[-1] + h2)
        self.Borient = (0, 0)
        self.pA = [p1.x, p1.y, y[0] + h1]
        self.pB = [p2.x, p2.y, y[-1] + h2]
        self.distance = self.A.distance(self.B)
        self.Aorient = self._calc_angles(self.pA, self.pB)
        self.Borient = self._calc_angles(self.pB, self.pA)
        self.loss, self.status = self._loss_calculator()
        
    def _calc_angles(self, src, trg):
        rel_pos = np.subtract(trg, src)
        yaw = m.atan2(rel_pos[1], rel_pos[0])
        pitch = m.atan2(rel_pos[2], self.distance)
        #yaw and pitch are in the range -pi - pi
        #lets add 180° (to avoid pi approx) to the degree to have them in the space
        # 0-360°
        return (m.degrees(yaw) + 180, m.degrees(pitch) + 180)

    def _apply_earth_curvature(self):
        n_points = len(self.d)
        y_curved = [None] * n_points
        for i in range(n_points):
            y_curved[i] = self.y[i] - (math.sqrt(self.d[i]**2 + self.R**2) - self.R)
        # update point after curvature
        self.B = Point(self.d[-1], self.y[-1] + self.h2)
        self.distance = self.A.distance(self.B)
        self.y = y_curved

    def _downscale(self, downscale):
        # keep 1 on n points
        old_profile = zip(self.d, self.y)
        profile = []
        for i in range(len(old_profile)):
            if i % downscale == 0:
                profile.append(choice(old_profile[i:i + downscale]))
        self.d, self.y = zip(*profile)
        self.y = list(self.y)
        self.d = list(self.d)

    def _polygonize(self):
        min_y = min(self.y) - 10
        self.y.insert(0, min_y)
        self.d.insert(0, self.d[0])
        self.y.append(min_y)
        self.d.append(self.d[-1])
        self.y.append(self.y[0])
        self.d.append(self.d[0])
        self.terrain = Polygon(zip(self.d, self.y))

    def _fresnel(self, clearance=False):
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

    def _kirkoff_fresnel(self, knife):
        d1 = knife.centroid.distance(self.A)
        d2 = knife.centroid.distance(self.B)
        v = knife.height * math.sqrt(2 / self.l * (1 / d1 + 1 / d2))
        loss = 6.9 + 10 * self.ple * math.log10(math.sqrt((v - 0.1)**2 + 1) + v - 0.1)
        return loss

    def _FSPL(self, distance):
        return 10 * self.ple * math.log10(4 * math.pi * distance / self.l)

    def _knife_method(self, knifes):
        loss = 0
        knifes_list = []
        if isinstance(knifes, MultiPolygon):
            for knife in knifes:
                knife.height = -knife.distance(self.LOS)
                knifes_list.append(knife)
            knifes_list.sort(key=lambda x: x.height, reverse=True)
            loss += self._kirkoff_fresnel(knife=knifes_list.pop(0))
            loss += self._kirkoff_fresnel(knife=knifes_list.pop(0))
        else:
            knifes.height = -knifes.distance(self.LOS)
            loss += self._kirkoff_fresnel(knife=knifes)
        return loss

    def _loss_calculator(self, frequency=5, downscale=0):
        self.f = frequency  # GHz
        self.l = self.c / self.f  # m
        self._apply_earth_curvature()
        if downscale > 0:
            self._downscale(downscale)
        self._polygonize()
        self.F60 = self._fresnel(clearance=True)
        self.LOS = LineString([self.A, self.B])
        self.F = self._fresnel()
        if self.terrain.intersects(self.LOS):
            # Los passing trough terrain
            obstacles = self.terrain.intersection(self.LOS)
            self.status = 0  # LOS OBSTR
            self.loss = 0
        else:
            # LOS is free
            self.loss = 0
            self.status = 1  # LOS FREE
            if self.terrain.intersects(self.F60):
                # Fresnel unclear
                knifes = self.F60.intersection(self.terrain)
                self.loss += self._knife_method(knifes)
                self.status = 3  # F60 obstructed
            self.loss += self._FSPL(self.distance)
        return self.loss, self.status
