from shapely.geometry import Point, Polygon
import ubiquiti as ubnt
import uuid


class Antenna:
    def __init__(self, device, orientation, channel=None):
        self.orientation = orientation
        self.ubnt_device = device
        self.channel = channel
        self.device = ubnt.read_device(device[0])
        self.beamwidth = (self.device['beamwidth_az'], self.device['beamwidth_el'])
        self.set_beamwidth_area()
        self.id = uuid.uuid4()

    def __repr__(self):
        return('(' + str(self) + ')')

    def __str__(self):
        return "%.2f+/-%.2f, %s, %dMhz" % (self.orientation[0], self.beamwidth[0] / 2, self.ubnt_device[0], self.channel)

    def set_beamwidth_area(self):
        self.az_area = ((self.orientation[0] - self.beamwidth[0] / 2) % 360, (self.orientation[0] + self.beamwidth[0] / 2) % 360)
        self.el_area = ((self.orientation[1] - self.beamwidth[1] / 2) % 360, (self.orientation[1] + self.beamwidth[1] / 2) % 360)

    def check_node_vis(self, link_angles):
        if self.az_area[0] <= link_angles[0] <= self.az_area[1] and self.el_area[0] <= link_angles[1] <= self.el_area[1]:
            return True
        return False
