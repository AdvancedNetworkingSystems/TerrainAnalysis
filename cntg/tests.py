import unittest
import network
import ubiquiti as ubnt
from antennas import AntennasExahustion, ChannelExahustion, LinkUnfeasibilty
import numpy as np
import math as m


class FakeBuilding():
    def __init__(self, gid, xy, z=2):
        self.gid = gid
        self.pos = xy
        self.z = z

    def xy(self):
        return self.pos

    def xyz(self):
        return (self.pos[0], self.pos[1], self.z)


class NetworkTests(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super(NetworkTests, self).__init__(*args, **kwargs)
        self.n = network.Network()
        ubnt.load_devices()
        self.n.set_maxdev(4)

    def _calc_angles(self, src, trg):
        rel_pos = np.subtract(trg, src)
        yaw = m.atan2(rel_pos[1], rel_pos[0])
        pitch = m.atan2(rel_pos[2], m.sqrt(rel_pos[0]**2 + rel_pos[1]**2))
        #yaw and pitch are in the range -pi - pi
        #lets add 180° (to avoid pi approx) to the degree to have them in the space
        # 0-360°
        return (m.degrees(yaw) + 180, m.degrees(pitch) + 180)

    def gen_link(self, src, dst):
        link = {}
        link['src'] = src
        link['dst'] = dst
        link['loss'] = 50  # Fixed
        link['src_orient'] = self._calc_angles(src.xyz(), dst.xyz())
        link['dst_orient'] = self._calc_angles(dst.xyz(), src.xyz())
        return link

    def test_onelink(self):
        b1 = FakeBuilding(1, (0, 0))
        self.n.add_gateway(b1)
        b2 = FakeBuilding(2, (5, 5))
        self.n.add_node(b2)
        link = self.gen_link(b2, b1)
        self.n.add_link_generic(link)
        # Check that the two antennas are aligned
        self.assertEqual((self.n.graph.nodes[1]['antennas'].antennas[0].orientation[0] + 180) % 360,
                        self.n.graph.nodes[2]['antennas'].antennas[0].orientation[0])
        # Check that the channel is the same
        self.assertEqual(self.n.graph.nodes[1]['antennas'].antennas[0].channel,
                        self.n.graph.nodes[2]['antennas'].antennas[0].channel)

    def test_twolink_in_viewshed(self):
        b1 = FakeBuilding(1, (-0.1, -0.1))
        self.n.add_gateway(b1)
        b2 = FakeBuilding(2, (10, 10))
        self.n.add_node(b2)
        link = self.gen_link(b2, b1)
        self.n.add_link_generic(link)
        b3 = FakeBuilding(3, (5.1, 5.1))
        self.n.add_node(b3)
        self.n.add_link_generic(self.gen_link(b3, b2))
        # verify that there is only 1 antenna per node
        for n in self.n.graph.nodes(data=True):
            self.assertEqual(len(n[1]['antennas']), 1)
        for e in self.n.graph.out_edges(2, data=True):
            self.assertEqual(e[2]['link_per_antenna'], 4)


    def test_twolink_lind_viewshed(self):
        b1 = FakeBuilding(1, (0, 0))
        self.n.add_gateway(b1)
        b2 = FakeBuilding(2, (5, 5))
        self.n.add_node(b2)
        link = self.gen_link(b2, b1)
        self.n.add_link_generic(link, existing=True)
        b3 = FakeBuilding(3, (10, 10))
        self.n.add_node(b3)
        self.n.add_link_generic(self.gen_link(b3, b2), existing=True)
        # verify that there is only 1 antenna per node (2 for the node in between)
        self.assertEqual(len(self.n.graph.nodes[1]['antennas']), 1)
        self.assertEqual(len(self.n.graph.nodes[2]['antennas']), 2)
        self.assertEqual(len(self.n.graph.nodes[3]['antennas']), 1)

    def test_twoisland_merge(self):
        b1 = FakeBuilding(1, (1, 1))
        self.n.add_gateway(b1)
        b2 = FakeBuilding(2, (1, 2))
        self.n.add_node(b2)
        link = self.gen_link(b2, b1)
        self.n.add_link_generic(link)
        b3 = FakeBuilding(3, (2, 1))
        self.n.add_node(b3)
        self.n.add_link_generic(self.gen_link(b3, b1))
        b4 = FakeBuilding(4, (3, 1))
        b5 = FakeBuilding(5, (3, 2))
        self.n.add_node(b5)
        self.n.add_link_generic(self.gen_link(b5, b2))
        self.n.add_node(b4)
        self.n.add_link_generic(self.gen_link(b4, b5))

        self.n.add_link_generic(self.gen_link(b4, b1), existing=True)
        self.assertEqual(len(self.n.graph.nodes[1]['antennas']), 3)
        self.assertEqual(len(self.n.graph.nodes[2]['antennas']), 2)
        self.assertEqual(len(self.n.graph.nodes[3]['antennas']), 1)
        self.assertEqual(len(self.n.graph.nodes[4]['antennas']), 2)
        self.assertEqual(len(self.n.graph.nodes[5]['antennas']), 2)

    def test_ant_exaustion(self):
        b1 = FakeBuilding(1, (0, 0))
        b2 = FakeBuilding(2, (1, 0))
        b3 = FakeBuilding(3, (0, 1))
        b4 = FakeBuilding(4, (-1, 0))
        b5 = FakeBuilding(5, (0, -1))
        b6 = FakeBuilding(6, (1, 1))

        self.n.add_gateway(b1)
        self.n.add_node(b2)
        self.n.add_link_generic(self.gen_link(b2, b1))
        self.n.add_node(b3)
        self.n.add_link_generic(self.gen_link(b3, b1))
        self.n.add_node(b4)
        self.n.add_link_generic(self.gen_link(b4, b1))
        self.n.add_node(b5)
        self.n.add_link_generic(self.gen_link(b5, b1))
        self.n.add_node(b6)
        with self.assertRaises(AntennasExahustion):
            self.n.add_link_generic(self.gen_link(b6, b1))

    def test_extralink(self):
        b1 = FakeBuilding(1, (1, 1))
        b2 = FakeBuilding(2, (2, 2))
        b3 = FakeBuilding(3, (1, 3))
        b4 = FakeBuilding(4, (1, 2))
        self.n.add_gateway(b1)
        self.n.add_node(b2)
        self.n.add_link_generic(self.gen_link(b2, b1))
        self.n.add_node(b3)
        self.n.add_link_generic(self.gen_link(b3, b2))
        self.n.add_node(b4)
        self.n.add_link_generic(self.gen_link(b3, b4))
        link = self.gen_link(b3, b1)
        #We must reverse the link because the antenna must be added on the dst, not the src
        self.n.add_link_generic(link, reverse=True)
        assert(len(self.n.graph.nodes[3]['antennas']) == 2)
        for e in self.n.graph.out_edges(3, data=True):
            if e[1] in [1, 4]:
                self.assertEqual(e[2]['link_per_antenna'], 4)

if __name__ == '__main__':
    unittest.main()
