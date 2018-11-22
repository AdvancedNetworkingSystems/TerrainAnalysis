import wifi
import ubiquiti as ubnt
import random
from antenna import Antenna


class AntennasExahustion(Exception):
    pass


class LinkUnfeasibilty(Exception):
    pass


class ChannelExahustion(Exception):
    pass


class Antennas:
    def __init__(self, max_ant):
        self.antennas = []
        self.max_ant = max_ant
        self.free_channels = wifi.channels[:]

    def add_antenna(self, loss, orientation, device=None, channel=None):
        # If the device is not provided we must find the best one for this link
        if not device:
            device = ubnt.get_fastest_link_hardware(loss)[1]
        if not device:
            raise LinkUnfeasibilty
        if(len(self.antennas) >= self.max_ant):
            raise AntennasExahustion
        if not channel:
            channel = self._pick_channel()
        # If there's a feasible device and the node hasn't too many antennas
        ant = Antenna(device, orientation, channel)
        self.antennas.append(ant)
        return ant

    def get_best_antenna(self, link):
        result = None
        # filter the antennas that are directed toward the src
        visible_antennas = [ant for ant in self.antennas
                            if ant.check_node_vis(link_angles=link['dst_orient'])]
        # sort them by the bitrate and take the fastest one
        if visible_antennas:
            best_ant = max(visible_antennas,
                           key=lambda x: ubnt.get_fastest_link_hardware(link['loss'],
                                                                        target=x.ubnt_device[0])[0])
            result = best_ant
        return result

    def _pick_channel(self):
        try:
            channel = random.sample(self.free_channels, 1)[0]
            self.free_channels.remove(channel)
            return channel
        except ValueError:
            raise ChannelExahustion
