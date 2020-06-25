from multiprocessing import Pool
import random
from cn_generator import CN_Generator
from misc import Susceptible_Buffer
import time
from antenna import Antenna
import code
import numpy as np
from pprint import pprint
from building import Building
from node import LinkUnfeasibilty, AntennasExahustion, ChannelExahustion, LinkTooBad


class Growing_network_candidate(CN_Generator):

    def __init__(self, args, unk_args=None):
        CN_Generator.__init__(self, args=args, unk_args=unk_args)
        self._post_init()

    def stop_condition(self):
        if self.n:
            return self.stop_condition_maxnodes() or self.stop_condition_minbw()
        return self.stop_condition_minbw()

    def restructure(self):
        return True

    def get_newnode(self):
        while(self.candidate_len > 0):
            self.candidate_len -= 1
            n = self.candidate_nodes.pop(0)
            self.last_gid = n.gid
            return n
        gid = int(np.random.choice(self.gid_pop_prop[:,0], p =self.gid_pop_prop[:,1]/self.pop_tot))
        self.pop_tot -= self.soc_df.loc[gid].P1
        self.soc_df = self.soc_df.drop(gid)
        self.gid_pop_prop = self.soc_df[["gid", "P1"]].to_numpy()
        return Building(gid, self.buildings.loc[gid].geometry)

    def add_links(self, new_node):
        if not self._add_links(new_node):
            self.candidate_nodes.append(new_node)
            return False
        self.candidate_len = len(self.candidate_nodes)
        return True

    def finalize(self):
        for b in self.candidate_nodes:
            self.add_node(b)

    def _add_links(self, new_node):
        #returns all the potential links in LoS with the new node
        # print("testing node %r, against %d nodes, %d potentian nodes" %
        #      (new_node, len(self.infected), len(self.candidate_nodes)))
        visible_links = [link for link in self.check_connectivity(
                         list(self.infected.values()), new_node) if link]
        # if there's at least one vaild link add the node to the network
        visible_links.sort(key=lambda x: x['loss'], reverse=True)
        src_ant = False
        while (visible_links):
            link = visible_links.pop()
            self.infected[link['src'].gid] = link['src']
            self.add_node(link['src'])
            try:
                src_ant = self.add_link(link)
            except (LinkUnfeasibilty) as e:
                # If the link is unfeasible I don't need to try on the followings
                self.net.del_node(link['src'])
                del self.infected[link['src'].gid]
                return False
            except (AntennasExahustion, ChannelExahustion, LinkTooBad) as e:
                # If the antennas/channel of dst are finished i can try with another node
                self.net.del_node(link['src'])
                del self.infected[link['src'].gid]
                src_ant = False
        if not src_ant:
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
            except (LinkUnfeasibilty, AntennasExahustion, ChannelExahustion, LinkTooBad) as e:
                print(e.msg)
            else:
                link_added +=1

        # add the remaining links to a list of feasible links for edgeffect
        print("Added link from %s to %s, with loss %d"%(link['src'], link['dst'], link['loss']))
        return True
