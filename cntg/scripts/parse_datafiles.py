#!/usr/bin/env python3
import glob
import argparse
import csv
import numpy
import sys
import os
import matplotlib.pyplot as plt
from pprint import pprint

def parse_data(f):
    bw = {}
    with open(f, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        next(csv_reader, None)
        for n, bw_m in csv_reader:
            bw[n] = float(bw_m)
    return bw


def parse_stats(f):
    bw = {}
    with open(f, 'r') as csv_file:
        header = next(csv_file, None)
        conf = eval(header[header.find("#")+1:])
        csv_reader = csv.DictReader(csv_file)
        for line in csv_reader:
            price = line['price_per_user']
            try:
                price_m = line['price_per_mbit']
            except KeyError:
                price_m = 0
            antennas_per_node = line['antennas_per_node']
    return price, price_m, conf, antennas_per_node


def plot_hist(data, bins=100):
    plt.hist(x=data, bins=bins, density=True, log=True)  # arguments are passed to np.histogram
    plt.title("BW per node")
    plt.show()


def plot_results(runs):
    data_per_bw = {}
    for run_id, values in runs.items():
        avg_nodes = numpy.average(values['nodes_array'])
        std_nodes = numpy.std(values['nodes_array'])
        conf = values['conf']
        print(conf['bandwidth'], values['nodes_array'])
        avg_price = values['price']/values['num_runs']
        avg_price_m = values['price_m']/values['num_runs']
        antennas_per_node = values['antennas_per_node']/values['num_runs']
        print('#' + run_id + "," + str(conf), file=outfile)
        print('avg_nodes, ', avg_nodes, file=outfile)
        print('std_nodes, ', avg_nodes, file=outfile)
        print('price_per_user, ', avg_price, file=outfile)
        print('price_per_user_per_Mb, ', avg_price_m, file=outfile)
        print('\n', file=outfile)
        print('#B_' + str(conf['bandwidth'].split(" ")[0]),  file=outfile)
        for b in sorted(values['data']):
            print(b, file=outfile)
        print('\n', file=outfile)
        hist, bins = numpy.histogram(values['data'], bins=100)

        for i, h in enumerate(hist):
            print(bins[i+1], ",",  h, file=outfile)
        print('\n', file=outfile)
        data_per_bw[conf['bandwidth'][0]] = [avg_nodes, std_nodes, avg_price, avg_price_m, antennas_per_node] 
    print('#comparison', file=outfile)
    for b in sorted(data_per_bw):
        print(b, ",", ",".join([str(x) for x in data_per_bw[b]]), file=outfile)
    print('\n', file=outfile)
            


args = None
outfile = None

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('-f', help="files to parse", nargs='+')
    p.add_argument('-o', help="output file")
    args = p.parse_args()
    if args.o:
        outfile = open(args.o, 'w')
    else:
        outfile = sys.stderr

    runs = {}
    bw_samples = []
    for f in args.f:
        try:
            (kind, db, strategy, gw, seed, _, radius, BW, restructure, V, max_dev, time) = os.path.basename(f).split('-')
        except ValueError:
            print("a problem occurred with file %s" % f)
            raise
        run_id = db + "_" + radius + "_" + BW + "_" + restructure
        if run_id not in runs:
            runs[run_id] = {'data': [], 'stats': [], 'num_nodes': 0,
                    'num_runs': 0, 'conf':{}, 'price': 0, 'price_m': 0,
                    'nodes_array': [], 'antennas_per_node': 0}
        if kind == 'data':
            bw = parse_data(f)
            runs[run_id]['data'] += bw.values()
            runs[run_id]['num_nodes'] += len(bw)
            runs[run_id]['num_runs'] += 1
            runs[run_id]['nodes_array'].append(len(bw))
        if kind == 'stats':
            price, price_m, conf, antennas_per_node = parse_stats(f)
            runs[run_id]['conf'] = conf
            runs[run_id]['price'] += float(price)
            runs[run_id]['price_m'] += float(price_m)
            runs[run_id]['antennas_per_node'] += float(antennas_per_node)
    plot_results(runs)
    #hist, bins = numpy.histogram(bw_samples, bins=100)
    #print(hist,bins)
    #plot_hist(bw_samples)
