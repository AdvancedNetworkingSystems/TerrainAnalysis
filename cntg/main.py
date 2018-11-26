#! /usr/bin/env python

from cn_generator import CN_Generator
from misc import NoGWError
from strategies.growing_network import Growing_network
from strategies.growing_network_exposed import Growing_network_exposed
import configargparse


STRATEGIES = {
    'growing_network': Growing_network,
    'growing_network_exposed': Growing_network_exposed

}


def parse_args():
    s_list = STRATEGIES.keys()
    parser = configargparse.get_argument_parser(default_config_files=['config.yml', 'experiment.yml'])
    parser.add_argument("-s", "--strategy",
                        help="a strategy to be used",
                        choices=s_list,
                        required=True)
    args, unknown = parser.parse_known_args()
    return args, unknown


if __name__ == '__main__':
    args, unknown_args = parse_args()
    try:
        s = STRATEGIES.get(args.strategy)(args=args, unk_args=unknown_args)
    except NoGWError:
        print("Gateway Not provieded")
    else:
        s.main()
