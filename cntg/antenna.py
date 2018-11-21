from shapely.geometry import Point, Polygon
import ubiquiti as ubnt


class Antenna:
    def __init__(self, device, orientation, channel):
        self.orientation = orientation
        self.channel = 0
        self.ubnt_device = device
        self.device = ubnt.read_device(device[0])
        self.beamwidth = (self.device['beamwidth_az'], self.device['beamwidth_el'])
        self.beamwidth_area = self.get_beamwidth_area()

    def __str__(self):
        return str(self.orientation)

    def get_beamwidth_area(self):
        p1 = ((self.orientation[0] + self.beamwidth[0] / 2) % 360, (self.orientation[1] - self.beamwidth[1] / 2) % 360)
        p2 = ((self.orientation[0] - self.beamwidth[0] / 2) % 360, (self.orientation[1] - self.beamwidth[1] / 2) % 360)
        p3 = ((self.orientation[0] - self.beamwidth[0] / 2) % 360, (self.orientation[1] + self.beamwidth[1] / 2) % 360)
        p4 = ((self.orientation[0] + self.beamwidth[0] / 2) % 360, (self.orientation[1] + self.beamwidth[1] / 2) % 360)
        return Polygon([p1, p2, p3, p4])

    def check_node_vis(self, link_angles):
        if self.beamwidth_area.contains(Point(link_angles)):
            return True
        return False
