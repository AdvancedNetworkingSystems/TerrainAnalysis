from multiprocessing import Pool
import random
import matplotlib.pyplot as plt
from cn_generator import CN_Generator
from strategies import growing_network as gn

if __name__ == '__main__':
    DSN = "postgresql://dbreader@192.168.160.11/terrain_ans"
    dataset = "quarrata"
    g = gn.Growing_network(DSN, dataset)
    g.main()

