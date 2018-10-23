from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from strategies.growing_network import Growing_network
import argparse
import pkgutil
import ubiquiti as ubnt


STRATEGIES = {
        'growing_network': Growing_network,
        }

def parse_args():
    s_list = STRATEGIES.keys()

    datasets = ["quarrata", "firenze", "pontremoli"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-s", help="a strategy to be used",
                        choices=s_list, required=True)

    parser.add_argument("-d", help="a data set from the available ones",
                        choices=datasets, required=True)

    parser.add_argument("--min_dev",
                        help="minimum number of devices per node",
                        type=int, const=1, nargs='?', default=1)

    parser.add_argument("--max_dev",
                        help="maximum number of devices per node",
                        type=int, const=float('inf'), nargs='?',
                        default=float('inf'))

    args, unknown = parser.parse_known_args()
    return args, unknown


if __name__ == '__main__':
    ubnt.load_devices()
    args, unknown_args = parse_args()
    s = STRATEGIES.get(args.s)(args.d, args=unknown_args)
    s.main()
