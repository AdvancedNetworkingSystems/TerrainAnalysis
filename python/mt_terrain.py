import threading
import math
import psycopg2
import numpy
import os
import itertools
import Queue
import sys
from shapely import errors
from random import shuffle
from link import Link
from terrain_rf import terrain_RF
from psycopg2.pool import ThreadedConnectionPool
from more_itertools import chunked

class MT_Terrain():
    def __init__(self, n_querier, n_calc):
        self.workers_query_result_q = Queue.Queue()
        DSN = "postgresql://gabriel:qwerasdf@192.168.184.102/postgres"
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        conn = self.tcp.getconn()
        cur = conn.cursor()
        self.querier = []
        self.calc = []
        self.go = True
        tf = terrain_RF(cur=cur, dataset='lyon')
        tf.set_workingarea(4.8411, 45.7613, 4.8528, 45.7681)
        buildings = tf.get_buildings()
        gid, h = zip(*buildings)
        self.tcp.putconn(conn, close=True)
        buildings_pair = list(itertools.combinations(gid, 2))
        chunk_size = len(buildings_pair)/n_querier
        chunks = list(chunked(buildings_pair, chunk_size))
        self.link_filename = "../data/"+tf.dataset+"_links.csv"
        with open(self.link_filename, 'a') as fl:
            print >> fl, "b1,b2,status,loss,status_downscale,loss_downscale"
        
        for i in range(n_querier):
            t = threading.Thread(target=self.queryWorker, args=[i, chunks[i]])
            self.querier.append(t)
            t.daemon = True
            t.start()
        for i in range(n_calc):
            t = threading.Thread(target=self.calcWorker, args=[i])
            self.calc.append(t)
            t.daemon = True
            t.start()
        [self.querier[i].join() for i in range(n_querier)]
        self.go = False
        [self.calc[i].join() for i in range(n_calc)]

    def queryWorker(self, worker_id, buildings_pairs):
        print("I am %d"%(worker_id))
        conn = self.tcp.getconn()
        cur = conn.cursor()
        for buildings_pair in buildings_pairs:
            id1 = buildings_pair[0]
            id2 = buildings_pair[1]
            tf = terrain_RF(cur=cur, dataset='lyon')
            profile = tf.profile_osm(id1, id2)
            result = {"id1": id1,
                      "id2": id2,
                      "profile": profile}
            self.workers_query_result_q.put(result)
        self.tcp.putconn(conn, close=True)

    def calcWorker(self, worker_id):
        while(self.go):
            # Take ORDER
            order = self.workers_query_result_q.get()
            profile = order["profile"]
            id1 = order["id1"]
            id2 = order["id2"]
            try:
                link = Link(profile)
                link_ds = Link(profile)
                loss, status = link.loss_calculator()
                loss_ds, status_ds = link_ds.loss_calculator(downscale=3)
            except errors.TopologicalError:
                loss = 0
                status = -1
                loss_ds = 0
                status_ds = -1
            with open(self.link_filename, 'a') as fl:
                print >> fl, "%s,%s,%d,%f,%d,%f" % (id1, id2, status, loss, status_ds, loss_ds)
                if status > 0:
                    print "Worker %d: %s to %s has status %d with loss %f, received pwr %f" % (worker_id, id1, id2, status, loss, 23 + 16 + 16 - loss)

if __name__ == '__main__':
    n_query = int(sys.argv[1])
    n_calc = int(sys.argv[2])
    mt = MT_Terrain(n_query, n_calc)
