import math
import psycopg2
import numpy
import os
import itertools
from shapely import errors
from random import shuffle
from link import Link
from terrain_rf import terrain_RF

if __name__ == '__main__':
    conn = psycopg2.connect(dbname='postgres', port=5432, user='gabriel', password='qwerasdf', host='192.168.184.102')
    cur = conn.cursor()
    tf = terrain_RF(cur=cur, dataset='lyon')
    #buildings = tf.get_buildings(11.234, 43.758, 11.285, 43.787) FIRENZE
    tf.set_workingarea(4.8411, 45.7613, 4.8528, 45.7681)
    buildings = tf.get_buildings()
    dic_h = dict(buildings)
    gid, h = zip(*buildings)
    mean_height = numpy.mean(h)
    ninth_percentile_heigth = numpy.percentile(h, 90)
    buildings_pair = list(itertools.combinations(gid, 2))
    shuffle(buildings_pair)
    link_filename = "../data/"+tf.dataset+"_links.csv"
    with open(link_filename, 'a') as fl:
        print >> fl, "b1,b2,status,loss,status_downscale,loss_downscale"
    for building in buildings_pair:
        id1 = building[0]
        id2 = building[1]
        # if (dic_h[id1] >= mean_height and dic_h[id2] >= mean_height) or \
        #         dic_h[id1] >= ninth_percentile_heigth or \
        #         dic_h[id2] >= ninth_percentile_heigth or \
        #         tf.distance(id1, id2) < 100:
        try:
            profile = tf.profile_osm(id1, id2)
            link = Link(profile)
            link_ds = Link(profile)
            loss, status = link.loss_calculator()
            loss_ds, status_ds = link_ds.loss_calculator(downscale=3)
        except errors.TopologicalError:
            loss = 0
            status = 2
            loss_ds = 0
            status_ds = 2
        with open(link_filename, 'a') as fl:
            print >> fl, "%s,%s,%d,%f,%d,%f" % (id1, id2, status, loss, status_ds, loss_ds)
            if status > 0:
                print "%s to %s has status %d with loss %f, received pwr %f" % (id1, id2, status, loss, 23+16+16-loss)
        # else:
        #     with open(tf.dataset + "_links.csv", 'a') as fl:
        #         print >> fl, "%s,%s,%d,%f,%d,%f" % (id1, id2, 4, 0, 4, 0)
            #print "%s to %s is unprobable to be feasible" % (id1, id2)
            
