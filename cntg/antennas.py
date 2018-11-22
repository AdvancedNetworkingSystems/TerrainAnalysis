import wifi
import ubiquiti as ubnt
import random
from antenna import Antenna


class AntennasExahustion(Exception):
    msg = "No more antennas"
    pass


class LinkUnfeasibilty(Exception):
    msg = "Link Unfeasibile"
    pass


class ChannelExahustion(Exception):
    msg = "No more channels"
    pass


class Antennas:
    def __init__(self, max_ant):
        self.antennas = []
        self.max_ant = max_ant
        self.free_channels = wifi.channels[:]

    def __str__(self):
        string = ""
        for a in self.antennas:
            string += str(a) + "<br>"
        return string

    def add_antenna(self, loss, orientation, device=None, channel=None):
        # If the device is not provided we must find the best one for this link
        if not device:
            src_device = ubnt.get_fastest_link_hardware(loss)[1]
        # If it is provided we have to find the best one wrt that device
        else:
            src_device = ubnt.get_fastest_link_hardware(loss, device[0])[1]
        if not src_device:
            raise LinkUnfeasibilty
        if(len(self.antennas) >= self.max_ant):
            raise AntennasExahustion
        if not channel:
            channel = self._pick_channel()
        ant = Antenna(src_device, orientation, channel)
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
        else:
            result = self.add_antenna(loss=link['loss'],orientation=link['dst_orient'])
        #print(result.ubnt_device)
        return result

    def _pick_channel(self):
        try:
            channel = random.sample(self.free_channels, 1)[0]
            self.free_channels.remove(channel)
            return channel
        except ValueError:
            raise ChannelExahustion
