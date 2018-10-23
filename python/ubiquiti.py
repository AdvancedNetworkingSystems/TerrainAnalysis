import json
#from collections import defaultdict
#import random
#import numpy as np
#import networkx as nx
#import matplotlib.pyplot as plt
#from itertools import groupby
#import copy
#from collections import OrderedDict


devices_name = ["AF-11FX", "AF-24", "AF-24HD", "AF-2X", "AF-3X",
                "AF-4X", "AF-5_AF-5U", "AF-5X",
                "AF-5XHD", "AM-IsoStation5AC",
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

af_modulations = ['1/4 QPSK SISO', 'QPSK SISO',
                  '16 QAM SISO', '64 QAM SISO',
                  '256 QAM SISO', '1024 QAM SISO',
                  '1/4 QPSK xRT', '1/2 QPSK xRT',
                  'QPSK MIMO', '16 QAM MIMO', '64 QAM MIMO',
                  '256 QAM MIMO', '1024 QAM MIMO']

am_modulations = ["MCS0", "MCS1", "MCS2", "MCS3", "MCS4",
                  "MCS5", "MCS6", "MCS7", "MCS8", "MCS9",
                  "MCS10", "MCS11", "MCS12", "MCS13", "MCS14",
                  "MCS15"]

angles = [90, 75, 60, 45, 30, 15, 0, -15, -30, -45, -60, -75, -90]

band = ['sensitivity(3.5)', 'sensitivity(5)',
        'sensitivity(7)', 'sensitivity(10)',
        'sensitivity(14)', 'sensitivity(20)',
        'sensitivity(28)', 'sensitivity(30)',
        'sensitivity(40)', 'sensitivity(50)',
        'sensitivity(56)', 'sensitivity(60)',
        'sensitivity(80)', 'sensitivity(100)']

devices = {}

bitrate_ac = {'MCS0': 32.5, 'MCS1': 130, 'MCS2': 195,
              'MCS3': 520, 'MCS4': 780,
              'MCS5': 1560, 'MCS6': 1755,
              'MCS7': 1950, 'MCS8': 3120, 'MCS9': 3466}

bitrate_n = {'MCS0': 15, 'MCS1': 30, 'MCS2': 45,
             'MCS3': 60, 'MCS4': 90, 'MCS5': 120,
             'MCS6': 135, 'MCS7': 150, 'MCS8': 30,
             'MCS9': 60, 'MCS10': 90, 'MCS11': 120,
             'MCS12': 180, 'MCS13': 240, 'MCS14': 270,
             'MCS15': 300}

json_folder = 'devices_ubiquiti'


def read_device(x):
    try:
        dev_path = x + '.json'
        file = open(os.path.join(json_folder, dev_path))
        res = json.loads(file.read())
        file.close()
        return res
    except FileNotFoundError:
        return dict()


def load_devices():
    for i in devices_name:
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


def find_possible_link(x, y, pathloss, v1=0, h1=0, v2=0, h2=0):

    if not check_link(x, y, pathloss):
        return ''

    res = []
    if get_attribute(x, 'technology') == 'AirMax ac':
        for i in get_tx_power(x):
            pr = i[1] + get_attribute(x, 'gain_tx') + \
                get_attribute(y, 'gain_rx') - pathloss
            if pr > get_rx_power_mod(y, i[0]):
                res.append(i[0])
    elif get_attribute(x, 'technology') == '802.11n' and \
            get_attribute(x, 'name') == 'AirMax':
        for i in am_modulations:
            pr = get_tx_power_mod(x, i) + get_attribute(x, 'gain_tx') + \
                get_attribute(y, 'gain_rx') - pathloss
            if pr > get_rx_power_mod(y, i):
                res.append(i)
    else:
        for i in get_tx_power(x):
            pr = i[1] + get_attribute(x, 'gain_tx') + \
                get_attribute(x, 'gain_rx') - pathloss
            for j in get_rx_power_af_mod(x, i[0]):
                if pr > j[1]:
                    res.append((i[0], str(j[0])))
    return res


def check_link(x, y, pathloss, v1=0, h1=0, v2=0, h2=0):

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


def find_max_possible_link(pathloss):
    tmp = []
    if type(pathloss) != float:
        return 0
    if pathloss < 0:
        return 0
    for i in devices:
        if 'AirMax' in get_attribute(i, 'name'):
            possible_mod = find_possible_link(i, i, pathloss)
            if not len(possible_mod) == 0:
                tmp.append((i, find_possible_link(i, i, pathloss).pop()))
    max_mod = 0
    if not len(tmp) == 0:
        for j in tmp:
            if max_mod == 0:
                if get_attribute(j[0], 'technology') == 'AirMax ac':
                    max_mod = bitrate_ac[j[1]]
                elif get_attribute(j[0], 'technology') == '802.11n':
                    max_mod = bitrate_n[j[1]]
            else:
                if get_attribute(j[0], 'technology') == 'AirMax ac':
                    if max_mod < bitrate_ac[j[1]]:
                        max_mod = bitrate_ac[j[1]]
                elif get_attribute(j[0], 'technology') == '802.11n':
                    if max_mod < bitrate_n[j[1]]:
                        max_mod = bitrate_n[j[1]]
        return max_mod
    else:
        return 0


def print_price_list():
    res = []
    for i in devices:
        res.append((i, get_attribute(i, 'average_price')))
    print(sorted(res))


def less_cost(graph, dev):
    if type(graph) != type(nx.Graph()):
        return(0, 0, 0)
    if type(dev) != str:
        return (0, 0, 0)
    if dev not in devices_name:
        return (0, 0, 0)
    g = nx.Graph()
    g.add_nodes_from(graph)
    total_device = 0
    cost = 0
    res = []
    not_possible = 0
    for i in graph.edges():
        possible_mod = find_possible_link(
            dev, dev, float(graph[i[0]][i[1]]['weight']))
        if len(possible_mod) > 0:
            total_device += 2
            cost += get_attribute(dev, 'average_price')*2
            res.append(possible_mod.pop())
            g.add_edge(i[0], i[1])
        else:
            not_possible += 1
    return (total_device, cost, nx.number_connected_components(g))


def max_link(graph):
    if type(graph) != type(nx.Graph()):
        return (0, 0, 0)
    g = nx.Graph()
    g.add_nodes_from(graph)
    total_device = 0
    cost = 0
    not_possible = 0
    for i in graph.edges():
        res = []
        for j in devices:
            if get_attribute(j, 'name') == 'AirMax':
                pos_mod = find_possible_link(
                    j, j, float(graph[i[0]][i[1]]['weight']))
                if len(pos_mod) > 0:
                    g.add_edge(i[0], i[1])
                    res.append((j, pos_mod.pop(),
                                get_attribute(j, 'average_price')*2))
        if len(res) == 0:
            not_possible += 1
        else:
            total_device += 2

        sort_res = sorted(res, key=lambda x: x[2])

        tmp_max = ()
        for i in sort_res:
            if tmp_max == ():
                tmp_max = i
            elif get_attribute(tmp_max[0], 'technology') == '802.11n':
                if get_attribute(i[0], 'technology' == '802.11n'):
                    if bitrate_n[i[1]] > bitrate_n[tmp_max[1]]:
                        tmp_max = i
                elif bitrate_ac[i[1]] > bitrate_n[tmp_max[1]]:
                    tmp_max = i
            elif get_attribute(i[0], 'technology') == '802.11n':
                if bitrate_n[i[1]] > bitrate_ac[tmp_max[1]]:
                    tmp_max = i
            elif bitrate_ac[i[1]] > bitrate_ac[tmp_max[1]]:
                tmp_max = i
        if not tmp_max == ():
            cost += get_attribute(tmp_max[0], 'average_price')*2
    return (total_device, cost, nx.number_connected_components(g))


def generate_graph(start_pathloss, end_pathloss):
    graph = []

    if type(start_pathloss) != int or type(end_pathloss) != int:
        return nx.Graph()
    if start_pathloss < 0 or end_pathloss < 0:
        return nx.Graph()

    for i in [50, 75, 100]:
        for j in [0.05, 0.15, 0.25]:
            graph.append(nx.gnp_random_graph(i, j))
    res = []
    for i in graph:
        res = []
        for j in i.edges():
            i[j[0]][j[1]]['weight'] = random.randrange(
                start_pathloss, end_pathloss)
    return graph


def plot_difference_cost_capacity_generate(average_pathloss):
    if type(average_pathloss[0]) != int:
        return
    if type(average_pathloss[1]) != int:
        return
    if average_pathloss[0] < 0 or\
            average_pathloss[1] < 0:
        return
    for j, k in average_pathloss:
        graph = generate_graph(j, k)

        yl = []
        ym = []
        capacity_less = []
        capacity_max = []

        count = 0

        for i in graph:
            print('--- visit ', count, 'graph---')
            yl.append(less_cost(i, 'AM-LiteBeamM523')[1])
            ym.append(max_link(i)[1])
            capacity_less.append(graph_capacity(i, True))
            capacity_max.append(graph_capacity(i, False))
            print('---finish ', count, 'graph---')
            count += 1

        x = [i for i in range(len(graph))]

        acc = 0
        edge = 0
        for k in graph:
            edge += k.number_of_edges()
            for j in k.edges():
                acc += float(k[j[0]][j[1]]['weight'])

        plt.figure()
        plt.plot(x, sorted(capacity_less), color='r',
                 label='capacity with cheap device')
        plt.plot(x, sorted(capacity_max), color='b',
                 label='capacity with max modulation')
        plt.xlabel('number of graph')
        plt.ylabel('capacity in Mbit/s')
        plt.legend()
        plt.show()

        title = 'avg pathloss: ' + str(acc/edge)

        plt.bar(x, sorted(ym), color='blue', label='max thrupught')
        plt.bar(x, sorted(yl), color='red', label='less cost')

        plt.xlabel('number of ghraph')
        plt.ylabel('dollars')
        plt.title(title)
        plt.legend()
        plt.figure()
        plt.plot()

    plt.show()


def calculate_capacity(g):
    max_capacity = 0
    if type(g) != type(nx.Graph()):
        return 0
    for i in g.edges():
        try:
            max_capacity += g[i[0]][i[1]]['band']
        except KeyError:
            pass

    return max_capacity


def graph_capacity(g, cheap):

    if type(g) != type(nx.Graph()):
        return 0
    if type(cheap) != bool:
        return 0

    g_less = g.copy()
    g_max = g.copy()

    if cheap:
        for i in g_less.edges():
            possible_mod = find_possible_link(
                'AM-LiteBeamM523', 'AM-LiteBeamM523',
                float(g[i[0]][i[1]]['weight']))
            if not len(possible_mod) == 0:
                g_less[i[0]][i[1]]['band'] = bitrate_n[possible_mod.pop()]
        return calculate_capacity(g_less)
    else:
        for i in g_max.edges():
            g_max[i[0]][i[1]]['band'] = find_max_possible_link(
                float(g_max[i[0]][i[1]]['weight']))
        return calculate_capacity(g_max)


def plot_difference_cost_capacity_real():
    graph_list = [os.path.join(os.path.abspath('Graphs'), i)
                  for i in os.listdir(os.path.abspath('Graphs'))]
    yl = []
    ym = []
    bottle_neckl = []
    bottle_neckm = []
    capacity_less = []
    capacity_max = []
    count = 0

    for i in graph_list:
        print('---visit graph: ', count, '---')
        a = nx.read_graphml(i)
        capacity_less.append(graph_capacity(a, True))
        capacity_max.append(graph_capacity(a, False))
        print('--finish capacity--')
        yl.append(less_cost(a, 'AM-LiteBeamM523')[1])
        ym.append(max_link(a)[1])
        print('--finish cost --')
        bottle_neckl.append(find_bottle_neck(a, True))
        bottle_neckm.append(find_bottle_neck(a, False))
        print('--finish bottleneck--')
        print('---finish graph :', count, '---')
        count += 1
    x = [i for i in range(len(graph_list))]

    edge = 0
    acc = 0
    for k in graph_list:
        i = nx.read_graphml(os.path.join(os.getcwd(), k))
        edge += i.number_of_edges()
        for j in i.edges():
            acc += float(i[j[0]][j[1]]['weight'])

    plt.figure()
    plt.plot(x, bottle_neckl, color='r',
             label='bottle neck capacity chap device')
    plt.plot(x, bottle_neckm, color='b',
             label='bottle neck capacity max capacity')
    plt.xlabel('number of graph')
    plt.ylabel('capacity of the bottle neck')
    plt.legend()
    plt.show()

    plt.figure()
    plt.plot(x, sorted(capacity_less), color='r',
             label='capacity with cheap device')
    plt.plot(x, sorted(capacity_max), color='b',
             label='capacity with max modulation')
    plt.xlabel('number of graph')
    plt.ylabel('capacity in Mbit/s')
    plt.legend()
    plt.show()

    title = 'avg pathloss : ' + str(acc/edge)
    plt.bar(x, sorted(ym), color='b', label='max_capacity')
    plt.bar(x, sorted(yl), color='r', label='less cost')
    plt.xlabel('graphs number')
    plt.ylabel('dollars')
    plt.title(title)
    plt.legend()
    plt.plot()
    plt.show()


def find_bottle_neck(g, cheap):

    g_less = g.copy()
    g_max = g.copy()
    bottle_neck = []

    if cheap:
        for i in g_less.edges():
            possible_mod = find_possible_link(
                'AM-LiteBeamM523', 'AM-LiteBeamM523',
                float(g[i[0]][i[1]]['weight']))
            if not len(possible_mod) == 0:
                g_less[i[0]][i[1]]['band'] = bitrate_n[possible_mod.pop()]
        for i in g_less.edges():
            bottle_neck.append(g_less[i[0]][i[1]]['band'])
        return min(bottle_neck)
    else:
        for i in g_max.edges():
            g_max[i[0]][i[1]]['band'] = find_max_possible_link(
                float(g_max[i[0]][i[1]]['weight']))
            bottle_neck.append(g_max[i[0]][i[1]]['band'])
        return min(bottle_neck)


def shortest_path_capacity(graph):
    print(graph.number_of_nodes(), graph.number_of_edges())

    path = []

    all_path = dict(nx.all_pairs_shortest_path(graph))

    for i in graph.nodes():
        for j in graph.nodes():
            try: 
                path.append(all_path[i][j])
            except KeyError :
                pass

    acc_less = []
    acc_max = []

    yl = []
    ym = []
    for i in path:
        for j in range(len(i)):
            if j != len(i)-1:
                pathloss = float(graph[i[j]][i[j+1]]['weight'])
                if find_possible_link('AM-LiteBeamM523', 'AM-LiteBeamM523', pathloss) != '':
                    acc_less.append(bitrate_n[find_possible_link('AM-LiteBeamM523', 'AM-LiteBeamM523', pathloss).pop()])
                acc_max.append(find_max_possible_link(pathloss))
        if len(acc_less) != 0:
            yl.append(min(acc_less))
            if min(acc_less) > 150:
                print(min(acc_less))
        if len(acc_max) != 0:
            ym.append(min(acc_max))
        acc_less.clear()
        acc_max.clear()
    
    x1 = [i for i in range(len(yl))]
    x2 = [i for i in range(len(ym))]
    plt.figure()
    plt.grid()
    plt.plot(x1, sorted(yl), color='r', label='less cost')
    plt.plot(x2, sorted(ym), color='b', label='max capacity')
    plt.xlabel('number_of_path')
    plt.ylabel('capacity Mbit/s')
    plt.legend()
    plt.show()


def shortest_path_capacity_csv():
    data = pd.read_csv('graph1.csv', names=['node', 'lon', 'lat'])
    graph = nx.Graph()
    node = data['node']
    lon = data['lon']
    lat = data['lat']

    for i in range(len(node)):
        graph.add_node(str(node[i]), lon=lon[i], lat=lat[i])
    
    a = nx.read_graphml('graph1.graphml')
    node_to_removve = []

    """

    for i in node_to_removve:
        graph.remove_node(i)"""
    print(graph.number_of_nodes(), a.number_of_edges())
    print(graph.nodes(data = True))
    for i in a.edges():
        if i[0] in graph and i[1] in graph:
            graph.add_edge(i[0], i[1])
    print(graph.number_of_edges())
    print('data dopo aggiungimento archi: ')
    print(graph.nodes(data = True))
    for i in graph.edges():
        lat_a = math.radians(graph.node[i[0]]['lat'])
        lon_a = math.radians(graph.node[i[0]]['lon'])
        lat_b = math.radians(graph.node[i[1]]['lat'])
        lon_b = math.radians(graph.node[i[1]]['lon'])
        
        d = 6372.795477598 * math.acos(math.sin(lat_a) * math.sin(lat_b)\
         + math.cos(lat_a) * math.cos(lat_b) * math.cos(lon_a - lon_b))
        
        pathloss = 20 * math.log(d) + 20 * math.log(5) + 92
        graph[i[0]][i[1]]['weight'] = pathloss
    shortest_path_capacity(graph) 
