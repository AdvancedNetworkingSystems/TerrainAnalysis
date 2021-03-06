#! /usr/bin/env python

from cn_generator import CN_Generator
from misc import NoGWError
from strategies.growing_network import Growing_network
from strategies.pref_attachment import Pref_attachment
from strategies.mm import MM
import configargparse
import itertools
from pprint import pprint

STRATEGIES = {
    'growing_network': Growing_network,
    'pref_attachment': Pref_attachment,
    'mm': MM
}


class Bunch(object):
    def __init__(self, adict):
        self.__dict__.update(adict)


def parse_args():
    s_list = STRATEGIES.keys()
    parser = configargparse.get_argument_parser(default_config_files=['config.yml', 'batch.yml'])
    # configuration arguments:
    parser.add_argument("--dsn", help="DSN to for the connection to PostGIS", required=True)
    parser.add_argument("--lidar_table", help="pointcloud table containing lidar/srtm data", required=True)
    parser.add_argument("--base_folder", help="Output base folder for the data", required=True)
    parser.add_argument("-P", "--processes", help="number of parallel processes",
                        default=1, type=int)
    # simulation parameters:
    # iterables
    parser.add_argument("-s", "--strategy",
                        help="a strategy to be used",
                        required=True,
                        action="append")
    parser.add_argument("-d", "--dataset",
                             help="a data set from the available ones",
                             required=True,
                             action="append")

    parser.add_argument("--max_dev",
                             help="maximum number of devices per node",
                             type=int, default=float('inf'), nargs='+')
    parser.add_argument('-g', "--gateway", help="gateway number in [0,n] from gws.yml",
                             type=int, required=True,  nargs='+')
    parser.add_argument('-n', "--max_size", help="number of nodes", type=int, nargs='+')
    parser.add_argument('-e', "--expansion", help="expansion range (in meters),"
                             " defaults to buildings at 30km", type=float,
                             default=30000, nargs='+')
    parser.add_argument('-V', "--viewshed_extra", help="Add at most v links extra link if"
            "these are in the viewshed of the current one.", type=int, default=0, nargs='+')
    parser.add_argument("-C", "--channel_width", help="802.11 channel width",
                    choices=[20,40,80,160], default=20, type=int, nargs="+")

    # not iterables
    parser.add_argument('-B', "--bandwidth", help="Accepts three arguments: bw frac min_n."
            "Stop when a fraction of frac nodes has less than bw bandwidth. "
            "Start measuring after min_n nodes (initially things may behave strangely "
            "(in Mbps). Ex: '1 0 1' will stop when any node has less than 1Mbps "
            "(in Mbps). Ex: '5 0.15 10' will stop when 15% of nodes has less than 5Mbps "
            "but not before we have at least 10 nodes",
            default="1 0 1")
    parser.add_argument('-R', "--restructure", help="restructure with edgeffect every r"
            " rounds, adding l links. Accepts two arguments: r l", default=[])

    parser.add_argument('-r', "--seed", help="random seed,", type=int)
    parser.add_argument("--runs", help="number of repeated runs", default=1, type=int)

    # flags
    parser.add_argument("-D", help="debug: print metrics at each iteration"
                             " and save metrics in the './data' folder",
                             action='store_true')

    parser.add_argument("-p", help="plot the graph using the browser",
                             dest='plot', action='store_true', default=False)
    args, unknown = parser.parse_known_args()
    return args, unknown


if __name__ == '__main__':
    args, unknown_args = parse_args()
    runs = args.runs
    args = vars(args)
    for k in args:
        if type(args[k]) is not list:
            temp = []
            temp.append(args[k])
            args[k] = temp
    product = [x for x in itertools.product(*args.values())]
    executions = [Bunch(dict(zip(args.keys(), p))) for p in product]
    for e in executions:
        for i in range(runs):
            try:
                s = STRATEGIES.get(e.strategy)(args=e, unk_args=None)
            except NoGWError:
                print("Gateway Not provieded")
            else:
                s.main()
