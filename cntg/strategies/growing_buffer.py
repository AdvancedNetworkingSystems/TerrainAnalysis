import random
from cn_generator import CN_Generator
from antenna import Antenna
import code
import numpy as np
from building import Building

from node import LinkUnfeasibilty, AntennasExahustion, ChannelExahustion, LinkTooBad


class Growing_network(CN_Generator):

    def __init__(self, args, unk_args=None, cache={}):
        CN_Generator.__init__(self, args=args, unk_args=unk_args, cache=cache)
        self._post_init()

    def stop_condition(self):
        if self.n:
            return self.stop_condition_maxnodes() or self.stop_condition_minbw()
        return self.stop_condition_minbw()

    def _post_init(self):
        gateway = self.get_gateway()
        # self.soc_df = self.soc_df.drop(gateway.gid)
        # self.gid_pop_prop = self.soc_df[["gid", "P1"]].to_numpy()
        # self.pop_tot = self.soc_df.P1.sum()
        self.gateway = gateway
        self.infected[gateway.gid] = gateway
        self.net.add_gateway(gateway, attrs={'event': 0})
        self.event_counter += 1
        #self.db_buildings = [Building(b.id, b.geometry) for b in self.buildings.itertuples()]
        self.get_susceptibles()
        self.logger.info("The gateway is " + repr(gateway))

    def restructure(self):
        return True

    def get_susceptibles(self):
        #self.susceptible = set(self.db_buildings) - set(self.infected.values())
        #return

        # geoms =[g.point for g in self.infected.values()]
        prova = gpd.GeoDataFrame(pd.DataFrame([(g.gid, g.point) for g in self.infected.values()], columns=["id", "geometry"]))
        self.sb = box(*prova.total_bounds).buffer(self.e)
        # #self.sb = cascaded_union(geoms).buffer(self.e)
        possible_matches_index = list(self.buildings_idx.intersection(self.sb.bounds))
        ids = self.buildings.iloc[possible_matches_index].id
        self.buildings_idx_in_buffer = set(ids)
#        buildings = self.buildings.iloc[possible_matches_index]
        # #buildings = possible_matches[possible_matches.intersects(self.sb)]
        #db_buildings = [Building(b.osm_id, b.geometry) for b in self.buildings.itertuples()] #use bounds of buffer, much faster
        #db_buildings = self.t.get_buildings(self.sb.get_buffer(self.e))

        #self.susceptible = set(db_buildings) - set(self.infected.values())

    def get_newnode(self):
        #must cast into list and order because sample on set is unpredictable
        # susceptible_tmp = sorted(list(self.susceptible), key=lambda x: x.gid)
        # if not susceptible_tmp:
        #     raise NoMoreNodes
        infected = {x.gid for x in self.infected.values()}
        susceptibles_idx = self.buildings_idx_in_buffer - infected
        #print(susceptibles_idx)
        #print(self.buildings)
        self.susceptible = self.soc_df.loc[susceptibles_idx]
        pop_tot = self.susceptible.P1.sum()
        gid_pop_prop = self.susceptible[["gid", "P1"]].to_numpy()

        gid = int(np.random.choice(gid_pop_prop[:,0], p =gid_pop_prop[:,1]/pop_tot))
        return Building(gid, self.buildings.loc[gid].geometry)
        #new_node = random.sample(susceptible_tmp, 1)[0]
        #self.susceptible.remove(new_node)
        #return new_node

    def add_links(self, new_node):
        #returns all the potential links in LoS with the new node
        # print("testing node %r, against %d potential nodes,"
        #       "already tested against %d nodes" %
        #         (new_node, len(self.infected) - len(self.noloss_cache[new_node]),
        #         len(self.noloss_cache[new_node])))
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
                #self.noloss_cache[new_node].add(link['dst'])
                return False
            except (AntennasExahustion, ChannelExahustion, LinkTooBad) as e:
                # If the antennas/channel of dst are finished i can try with another node
                self.net.del_node(link['src'])
                del self.infected[link['src'].gid]
                src_ant = False
                #self.noloss_cache[new_node].add(link['dst'])
            if(src_ant):
                break

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
                self.logger.debug(e.msg)
            else:
                link_added +=1

        # add the remaining links to a list of feasible links for edgeffect
        self.logger.debug("Added link from %s to %s, with loss %d and additional %d links"%(link['src'], link['dst'], link['loss'], link_added))
        return True
