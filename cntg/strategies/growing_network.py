from multiprocessing import Pool
import random
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import time
from antenna import Antenna
import code
from node import LinkUnfeasibilty, AntennasExahustion, ChannelExahustion


class Growing_network(CN_Generator):

    def __init__(self, args, unk_args=None):
        self.sb = Susceptible_Buffer()
        CN_Generator.__init__(self, args=args, unk_args=unk_args)
        self.feasible_links = []
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
        #returns all the potential links in LoS with the new node
        print("testing node %r, against %d potential nodes,"
              "already tested against %d nodes" %
                (new_node, len(self.infected) - len(self.noloss_cache[new_node]),
                len(self.noloss_cache[new_node])))
        visible_links = [link for link in self.check_connectivity(
                         list(self.infected.values()), new_node) if link]
        if not visible_links:
            return False
        # Value of the bw of the net before the update
        min_bw = self.net.compute_minimum_bandwidth()
        # Let's create a dict that associate each link to a new net object.
        metrics = self.pool.map(self.net.calc_metric, visible_links)
        # Filter out unwanted links
        clean_metrics = []
        for m in metrics:
            if m['min_bw'] == 0:
                print("First Node")
                # This is the first node we add so we have to ignore the metric and add it
                self.infected[m['link']['src'].gid] = m['link']['src']
                self.add_node(m['link']['src'])
                src_ant = self.add_link(m['link'])
                return True
            if not m['min_bw']:
                # If is none there was an exception (link unaddable) thus we add it to cache
                self.noloss_cache[new_node].add(m['link']['dst'])
            else:
                clean_metrics.append(m)
        # We want the link that maximizes the difference of the worse case
        if not clean_metrics:
            # All the links are unfeasible for some reasnon (strange)
            return False
        # Order the links for min_bw difference and then for abs(loss) because we order from smallest to biggest
        ordered_metrics = sorted(clean_metrics,
                                 key=lambda m: (min_bw[m['node']] - m['min_bw'],
                                                m['link']['loss']),
                                 reverse=True)
        link = ordered_metrics.pop()['link']
        self.infected[link['src'].gid] = link['src']
        self.add_node(link['src'])
        # Don't need to try since the unvalid link have been excluded by calc_metric()
        src_ant = self.add_link(link)
        # Add the remaining links if needed
        link_in_viewshed = [m['link'] for m in ordered_metrics
                            if src_ant.check_node_vis(m['link']['src_orient'])]
        link_added = 0
        while link_in_viewshed and link_added < self.V:
            link = link_in_viewshed.pop()
            visible_links.remove(link)  # remove it from visible_links af
            try:
                self.add_link(link, reverse=True)
            except (LinkUnfeasibilty, AntennasExahustion, ChannelExahustion) as e:
                print(e.msg)
            else:
                link_added += 1
        self.feasible_links += visible_links
        return True
