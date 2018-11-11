import json
import os
import csv
import wifi
#from collections import defaultdict
#import random
#import numpy as np
#import networkx as nx
#import matplotlib.pyplot as plt
#from itertools import groupby
#import copy
#from collections import OrderedDict


devices_airfiber = ["AF-11FX", "AF-24", "AF-24HD", "AF-2X", "AF-3X",
                    "AF-4X", "AF-5_AF-5U", "AF-5X",
                    "AF-5XHD"]

devices_airmax = ["AM-IsoStation5AC",
                  "AM-IsoStationM5", "AM-LiteBeam5AC16120",
                  "AM-LiteBeam5AC23", "AM-LiteBeam5ACGEN2",
                  "AM-LiteBeamM523", "AM-NanoBeam2AC13",
                  "AM-NanoBeam5ACGEN2", "AM-NanoBeamM516",
                  "AM-NanoBeamM519", "AM-NanoStation5AC",
                  "AM-NanoStation5ACL", "AM-PowerBeam2AC400",
                  "AM-PowerBeam5AC300", "AM-PowerBeam5AC300ISO",
                  "AM-PowerBeam5AC400", "AM-PowerBeam5AC400ISO",
                  "AM-PowerBeam5AC500", "AM-PowerBeam5AC500ISO",
                  "AM-PowerBeam5AC620", "AM-PowerBeam5ACGEN2",
                  "AM-PowerBeam5ACISOGEN2", "AM-PowerBeamM2400",
                  "AM-PowerBeamM5300", "AM-PowerBeamM5400",
                  "AM-PowerBeamM5620"]


angles = [90, 75, 60, 45, 30, 15, 0, -15, -30, -45, -60, -75, -90]

band = ['sensitivity(3.5)', 'sensitivity(5)',
        'sensitivity(7)', 'sensitivity(10)',
        'sensitivity(14)', 'sensitivity(20)',
        'sensitivity(28)', 'sensitivity(30)',
        'sensitivity(40)', 'sensitivity(50)',
        'sensitivity(56)', 'sensitivity(60)',
        'sensitivity(80)', 'sensitivity(100)']

devices = {}

json_folder = '80211/devices_ubiquiti'


def read_device(x):
    try:
        dev_path = x + '.json'
        file = open(os.path.join(json_folder, dev_path))
        res = json.loads(file.read())
        file.close()
        return res
    except FileNotFoundError:
        return dict()


def load_devices(airmax=True, airfiber=False):
    wifi.load_mcs_tables()
    if airmax:
        for i in devices_airmax:
            devices[i] = read_device(i)
    if airfiber:
        for i in devices_airfiber:
            devices[i] = read_device(i)


def get_attribute(dev, attribute):
    try:
        return devices[dev][attribute]
    except KeyError:
        return ''


def get_rx_power(x):
    res = []
    if get_attribute(x, 'name') == 'AirMax':
        try:
            for i in devices[x]['rx_power']:
                res.append((str(i), devices[x]['rx_power'][i]))
            return res
        except KeyError:
            return res
    else:
        try:
            for i in devices[x]['rx_power']:
                for j in devices[x]['rx_power'][i]:
                    res.append((str(i), str(j), devices[x]['rx_power'][i][j]))
            return res
        except KeyError:
            return res


def get_rx_power_mod(x, mod):
    try:
        if get_attribute(x, 'name') == 'AirFiber':
            return 0
        else:
            return devices[x]['rx_power'][mod]
    except KeyError:
        return 0


def get_rx_power_af_mod(x, mod):
    res = []
    try:
        if get_attribute(x, 'name') == 'AirFiber':
            for i in devices[x]['rx_power'][mod]:
                res.append((str(i), devices[x]['rx_power'][mod][i]))
            return res
        else:
            return res
    except KeyError:
        return res


def get_tx_power(x):
    res = []
    try:
        for i in devices[x]['tx_power']:
            res.append((str(i), devices[x]['tx_power'][i]))
        return res
    except KeyError:
        return res


def get_tx_power_mod(x, mod):
    try:
        return devices[x]['tx_power'][mod]
    except KeyError:
        return 0


def get_capacity_af(x):
    res = []
    try:
        if get_attribute(x, 'name') == 'AirFiber':
            for i in devices[x]['capacity']:
                for j in devices[x]['capacity'][i]:
                    res.append((str(i), str(j), devices[x]['capacity'][i][j]))
            return res
        else:
            return res
    except KeyError:
        return res


def get_capacity_af_mod(x, mod):
    res = []
    try:
        if get_attribute(x, 'name') == 'AirFiber':
            for i in devices[x]['capacity'][mod]:
                res.append((str(i), devices[x]['capacity'][mod][i]))
            return res
        else:
            return res
    except KeyError:
        return res


def get_capacity_af_mod_band(x, mod, band):
    try:
        return devices[x]['capacity'][mod][band]
    except KeyError:
        return 0


def get_feasible_modulation_list(x, y, pathloss, cap_tx_power=True):

    if not check_link(x, y, pathloss):
        return ''

    res = []
    if get_attribute(x, 'technology') == 'AirMax ac':
        for i in get_tx_power(x):
            tx_pow = i[1] + get_attribute(x, 'gain_tx')
            if cap_tx_power:
                tx_pow = min(tx_pow,
                             wifi.tx_power_regulation_eu[
                                 get_attribute(x, 'frequency')])
            pr = tx_pow + get_attribute(y, 'gain_rx') - pathloss
            if pr > get_rx_power_mod(y, i[0]):
                res.append(i[0])
    elif get_attribute(x, 'technology') == '802.11n' and \
            get_attribute(x, 'name') == 'AirMax':
        for i in wifi.mcs_N.keys():
            tx_pow = get_tx_power_mod(x, i) + get_attribute(y, 'gain_tx')
            if cap_tx_power:
                tx_pow = min(tx_pow,
                             wifi.tx_power_regulation_eu[
                                 get_attribute(x, 'frequency')])
            pr = tx_pow + get_attribute(y, 'gain_rx') - pathloss
            if pr > get_rx_power_mod(y, i):
                res.append(i)
    else:
        for i in get_tx_power(x):
            tx_pow = i + get_attribute(x, 'gain_tx')
            if cap_tx_power:
                tx_pow = min(tx_pow,
                             wifi.tx_power_regulation_eu[
                                 get_attribute(x, 'frequency')])
            pr = tx_powe + get_attribute(x, 'gain_rx') - pathloss
            for j in get_rx_power_af_mod(x, i[0]):
                if pr > j[1]:
                    res.append((i[0], str(j[0])))
    return res


def check_link(x, y, pathloss):

    try:
        devices[x]
        devices[y]
    except KeyError:
        return False

    if get_attribute(x, 'frequency') != get_attribute(y, 'frequency'):
        return False
    elif get_attribute(x, 'technology') != get_attribute(y, 'technology'):
        return False
    elif pathloss <= 0:
        return False
    else:
        return True


def get_fastest_link_hardware(pathloss, target=None):
    tmp = []
    for d in devices:
        if not target:
            target = d
        possible_mod = get_feasible_modulation_list(d, target, pathloss)
        if possible_mod:
            tmp.append((d, possible_mod.pop()))
    max_mod = 0
    device = ''
    if tmp:
        for d in tmp:
            if get_attribute(d[0], 'technology') == 'AirMax ac':
                streams = int(get_attribute(d[0], 'max_streams'))
                if max_mod < wifi.mcs_AC[d[1]][streams]\
                                        [wifi.default_channel_width]:
                    max_mod = wifi.mcs_AC[d[1]][streams]\
                                        [wifi.default_channel_width]
                    device = d
            elif get_attribute(d[0], 'technology') == '802.11n':
                if max_mod < wifi.mcs_N[d[1]][wifi.default_channel_width]:
                    max_mod = wifi.mcs_N[d[1]][wifi.default_channel_width]
                    device = d
        return max_mod, device
    else:
        return 0, ''


def print_device_list():
    res = {}
    for i in devices:
        res[i] = get_attribute(i, 'average_price')
    for n, p in sorted(res.items(), key=lambda x: x[1]):
        print(n, " ", p)
