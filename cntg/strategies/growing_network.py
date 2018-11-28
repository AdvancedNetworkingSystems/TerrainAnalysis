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
        
        # if there's at least one vaild link add the node to the network
        event = 0
        while (visible_links):
            visible_links.sort(key=lambda x: x['loss'], reverse=True)
            link = visible_links.pop()
            self.infected[link['src'].gid] = link['src']
            self.add_node(link['src'])
            try:
                src_ant = self.add_link(link)
            except (LinkUnfeasibilty) as e:
                # If the link is unfeasible I don't need to try on the followings
                print(e.msg)
                self.net.del_node(link['src'])
                del self.infected[link['src'].gid]
                self.noloss_cache[new_node].add(link['dst'].gid)
                return False
            except (AntennasExahustion, ChannelExahustion) as e:
                # If the antennas/channel of dst are finished i can to try with another node
                self.net.del_node(link['src'])
                del self.infected[link['src'].gid]
                self.noloss_cache[new_node].add(link['dst'].gid)
        if not visible_links:
            #I finished all the dst node
            return False
        link_in_viewshed = [link for link in visible_links
                            if src_ant.check_node_vis(link['src_orient'])]
        link_in_viewshed.sort(key=lambda x: x['loss'], reverse=True)
        link_added = 0
        while link_in_viewshed and link_added < self.V:
            link = link_in_viewshed.pop()
            visible_links.remove(link)  # remove it from visible_links af
            try:
                self.add_link(link, reverse=True)
            except (LinkUnfeasibilty, AntennasExahustion, ChannelExahustion) as e:
                print(e.msg)
            else:
                link_added +=1

        # add the remaining links to a list of feasible links for edgeffect
        self.feasible_links += visible_links
        return True
