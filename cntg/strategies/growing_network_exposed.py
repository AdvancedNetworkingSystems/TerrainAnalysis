from multiprocessing import Pool
import random
from strategies.growing_network import Growing_network
from misc import Susceptible_Buffer
import argparse
import time
import ubiquiti as ubnt
import networkx as nx


class Growing_network_exposed(Growing_network):
    def __init__(self, args, unk_args={}, DSN=None):
        self.exposed = set()
        Growing_network.__init__(self, args=args, unk_args=unk_args, DSN=None)

    def stop_condition(self):
        if self.n:
            bol = self.stop_condition_maxnodes() or self.stop_condition_minbw()
        return self.stop_condition_minbw()

    def add_links(self, new_node):
        visible_links_infected = [link for link in self.check_connectivity(self.infected, new_node) if link]
        visible_links_exposed = [link for link in self.check_connectivity(list(self.exposed), new_node) if link]
        self.add_node(new_node)
        node_added = False
        # FIXME: there is a bug involving infected. sometimes there are more nodes in the graph than infected
        if visible_links_infected:
            visible_links_infected.sort(key=lambda x: x['loss'], reverse=True)
            print(visible_links_infected)
            link = visible_links_infected.pop()
            if self.add_link(link):
                # If i can connect to an infected node I'm infected too,
                # separate island connected to main net
                self.infected.append(link['src'])
                node_added = True
        if visible_links_exposed:
            visible_links_exposed.sort(key=lambda x: x['loss'], reverse=True)
            print(visible_links_exposed)
            link = visible_links_exposed.pop()
            if self.add_link(link):
                if link['src'] not in self.infected:
                    self.infected.append(link['src'])  # If i wasn't conncted to anybody but i connected to an Exposed
                    self.infected.append(link['dst'])      # we are both infected (separate island though)
                    #TODO: Must remove the list of infected and exposed and use only the graph infos (grado)
                    #self.exposed.remove(link['dst'])
                node_added = True
        if not node_added:  # Node not connectable to anybody
            self.exposed.add(new_node)
        self.feasible_links += visible_links_exposed + visible_links_infected
        return True
