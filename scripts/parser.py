import requests
import re
import sys
from multiprocessing import Pool#, Manager
import itertools
import argparse


class Parser:
    def __init__(self, content, dataset, processes):
        self.dataset = dataset.upper()
        self.processes = processes
        if self.dataset == 'FIRENZE':
            bbox = "668580.03692787,4843058.5087554,692597.18143529,4856455.4960566"
        elif self.dataset == 'QUARRATA':
            bbox = "649435.88294369,4852406.1113483,666877.91130513,4862135.4375135"
        elif self.dataset == 'PONTREMOLI':
            bbox = "559497.11594305,4909256.1649248,582907.56720259,4922314.7330716"
        elif self.dataset == 'VAIANO':
            bbox = "663742.05272453,4864435.7612468,677742.63734903,4872245.4179846"
        else:
            print("Wrong dataset")
            bbox = None

        self.bbox = bbox
        self.content = content.upper()
        self.xmax = 1470
        self.ymax = 827
        # self.manager = Manager()
        # self.Global = manager.Namespace()

    def worker(self, xy):
        url = "http://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmscartoteca&version=1.3.0\
&map_resolution=91&map_mnt=cartoteca&SERVICE=WMS&FORMAT=image/png&REQUEST=GetFeatureInfo\
&LAYERS=rt_cartoteca.lidar2k&QUERY_LAYERS=rt_cartoteca.lidar2k&STYLES=solo_contorno_con_etichette\
&FEATURE_COUNT=50&HEIGHT={0}&WIDTH={1}&SRS=EPSG:25832&VERSION=1.1.1&TRANSPARENT=TRUE\
&X={2}&Y={3}&BBOX={4}&INFO_FORMAT=text/html".format(self.ymax, self.xmax, xy[0], xy[1], self.bbox)
        r = requests.get(url)
        #print(r.text)
        match = re.findall('(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])>{}?'.format(self.content), r.text)
        if match:
            url = "{}://{}{}".format(*match[0])
            print(url, file=sys.stderr)
            return url

    def main(self):
        with Pool(self.processes) as p:
            tuple_space = itertools.product(range(0, self.xmax, 10), range(0, self.ymax, 10))
            urls = p.map(self.worker, tuple_space)
        with open("%s_%s.urls" % (self.dataset.lower(), self.content.lower()), "w") as fw:
            urls = set(urls)
            for u in urls:
                if u:
                    print(u, file=fw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Multithread scraper of data from the web')
    parser.add_argument("-D", help="debug: print metrics at each iteration"
                             " and save metrics in the './data' folder",
                             action='store_true')
    parser.add_argument("-P", "--processes", help="number of parallel processes",
                             default=1, type=int)
    parser.add_argument('-c', "--content", help="DSM or DTM",
                             type=str, required=True)
    parser.add_argument('-d', "--dataset", help="Dataset between: Firenze, Pontremoli, Vaiano or Quarrata")
    args = parser.parse_args()
    p = Parser(args.content, args.dataset, args.processes)
    p.main()
