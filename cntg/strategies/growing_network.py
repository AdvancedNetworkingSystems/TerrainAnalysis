from multiprocessing import Pool
import random
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import argparse
import time
from antenna import Antenna
import code


class Growing_network(CN_Generator):

    def __init__(self, args, unk_args=None, DSN=None):
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, args.d, DSN=None, args=args,
                              unk_args=unk_args)
        self.feasible_links = []
        self.filename = "graph-%s-%s-%d-%s-%d.graphml"\
                        % (args.d, self.n, int(self.e), self.b, time.time())
        self._post_init()

    def stop_condition(self):
        if self.n:
            return self.stop_condition_maxnodes() or self.stop_condition_minbw()
        return self.stop_condition_minbw()

    def get_newnode(self):
        return self.get_random_node()

    def restructure(self):
        return self.restructure_edgeeffect_mt()

    def add_links(self, new_node):
        visible_links = [link for link in self.check_connectivity(
                         list(self.infected.values()), new_node) if link]
        
        # if there's at least one vaild link add the node to the network
        print("testing node %r" % (new_node))
        event = 0
        if not visible_links:
            return False
        visible_links.sort(key=lambda x: x['loss'], reverse=True)
        link = visible_links.pop()
        self.infected[link['src'].gid] = link['src']
        # check if current node has already antennas and try to connect to them
        self.add_node(link['src'])
        src_ant = self.add_link(link)
        if not src_ant:
            # if this link is not feasible the following ones (worser) aren't either
            self.net.del_node(link['src'])
            del self.infected[link['src'].gid]
            return False

        link_in_viewshed = [link for link in visible_links
                            if src_ant.check_node_vis(link['src_orient'])]
        while link_in_viewshed:
            link = link_in_viewshed.pop()
            visible_links.remove(link)  # remove it from visible_links af
            self.add_link(link)
        # add the remaining links to a list of feasible links for edgeffect
        self.feasible_links += visible_links
        return True
