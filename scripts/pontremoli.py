import requests
import re
from multiprocessing import Pool, Manager
import itertools
manager = Manager()
Global = manager.Namespace()
bbox = "559497.11594305,4909256.1649248,582907.56720259,4922314.7330716"
xmax = 1511
ymax = 978

def worker(xy):
    url = "http://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmscartoteca&version=1.3.0\
&map_resolution=91&map_mnt=cartoteca&SERVICE=WMS&FORMAT=image/png&REQUEST=GetFeatureInfo\
&LAYERS=rt_cartoteca.lidar2k&QUERY_LAYERS=rt_cartoteca.lidar2k&STYLES=solo_contorno_con_etichette\
&FEATURE_COUNT=50&HEIGHT={0}&WIDTH={1}&SRS=EPSG:25832&VERSION=1.1.1&TRANSPARENT=TRUE\
&X={2}&Y={3}&BBOX={4}&INFO_FORMAT=text/html".format(ymax, xmax, xy[0], xy[1], bbox)
    r = requests.get(url)
    match = re.findall('(http|ftp|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])>DSM?', r.text)
    if match:
        url = "{}://{}{}".format(*match[0])
        return url

if __name__ == '__main__':
    with Pool(10) as p:
        tuple_space = itertools.product(range(0, xmax, 10), range(0, ymax, 10))
        urls = p.map(worker, tuple_space)
        urls = set(urls)
        for u in urls:
            if u:
                print(u)
