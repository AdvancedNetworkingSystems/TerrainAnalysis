import random
from cn_generator import CN_Generator, NoMoreNodes
from node import LinkUnfeasibilty, AntennasExahustion, ChannelExahustion


class MM(CN_Generator):

    def __init__(self, args, unk_args=None):
        CN_Generator.__init__(self, args=args, unk_args=unk_args)
        self.feasible_links = []
        self._post_init()


    def restructure(self):
        return True

    def add_links(self, new_node):
        #returns all the potential links in LoS with the new node
        #print("testing node %r, against %d potential nodes"%
                #(new_node, len(self.infected)))
        visible_links = [link for link in self.check_connectivity(
                         list(self.infected.values()), new_node) if link]
        if not visible_links:
            return False
        src_ant = False
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
            return False
        except (AntennasExahustion, ChannelExahustion, LinkTooBad) as e:
            # If the antennas/channel of dst are finished i can try with another node
            self.net.del_node(link['src'])
            del self.infected[link['src'].gid]
        if not src_ant:
            #I finished all the dst node
            return False
        # Add the remaining links if needed
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
                link_added += 1
        self.feasible_links += visible_links
        return True
