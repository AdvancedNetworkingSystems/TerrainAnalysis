import unittest
import sys
sys.path.insert(0, "../")
import ubiquiti


class TestDataStr(unittest.TestCase):

    ubiquiti.load_devices()

    def test_fastest_link(self):
        for p in range(80, 160, 10):
            print(ubiquiti.get_fastest_link_hardware(p))

    def test_feasible_modulations(self):
        mod_list = ubiquiti.get_feasible_modulation_list("AM-LiteBeam5ACGEN2",
                                                         "AM-LiteBeam5ACGEN2",
                                                         100)
