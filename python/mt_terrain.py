import multiprocessing as mp
import math
import psycopg2
import numpy
import os
import itertools
import sys
import csv
import time
from shapely import errors
from random import shuffle
from link import Link
from terrain_rf import terrain_RF
from psycopg2.pool import ThreadedConnectionPool
from more_itertools import chunked

class MT_Terrain():
    def __init__(self, n_querier, n_calc):
        self.workers_query_result_q = mp.Queue()
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
        gid = set(gid)
        self.tcp.putconn(conn, close=True)
        buildings_pair = set(itertools.combinations(gid, 2))
        self.link_filename = "../data/"+tf.dataset+"_links.csv"
        
        try:
            with open(self.link_filename+"_0", 'rb') as fr:
                link_csv = csv.reader(fr, delimiter=',')
                already_proc = set()
                for line in link_csv:
                    already_proc.add((int(line[0]), int(line[1])))
                buildings_pair = buildings_pair - already_proc
        except IOError:
            pass
        print "%d links left to estimate"%len(buildings_pair)
        chunk_size = len(buildings_pair)/n_querier
        chunks = list(chunked(buildings_pair, chunk_size))

        # with open(self.link_filename, 'a') as fl:
        #     print >> fl, "b1,b2,status,loss,status_downscale,loss_downscale"
        self.start_time=time.time()
        for i in range(n_querier):
            t = mp.Process(target=self.queryWorker, args=[i, chunks[i]])
            self.querier.append(t)
            t.daemon = True
            t.start()
        for i in range(n_calc):
            t = mp.Process(target=self.calcWorker, args=[i])
            self.calc.append(t)
            t.daemon = True
            t.start()
        t = mp.Process(target=self.monitor)
        t.daemon = True
        t.start()
        [self.querier[i].join() for i in range(n_querier)]
        self.go = False
        [self.calc[i].join() for i in range(n_calc)]
    
    def monitor(self):
        time.sleep(5)
        while(self.go):
            for i in range(n_calc):
                n = 0
                with open("%s_%d" % (self.link_filename, i), 'r') as f:
                    n += len(f.readlines())
            elapsed_s = time.time() - self.start_time
            avg_speed = elapsed_s / n
            print("%d seconds passed, %d links estimated.Avg time per link%f"%(elapsed_s, n, avg_speed))
            time.sleep(3)

    def queryWorker(self, worker_id, buildings_pairs):
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
            except (errors.TopologicalError, ZeroDivisionError), e:
                print e
                loss = 0
                status = -1
                loss_ds = 0
                status_ds = -1
            with open("%s_%d" % (self.link_filename, worker_id), 'a') as fl:
                print >> fl, "%s,%s,%d,%f,%d,%f" % (id1, id2, status, loss, status_ds, loss_ds)
                # if status > 0:
                #     print "Worker %d: %s to %s has status %d with loss %f, received pwr %f" % (worker_id, id1, id2, status, loss, 23 + 16 + 16 - loss)

if __name__ == '__main__':
    n_query = int(sys.argv[1])
    n_calc = int(sys.argv[2])
    mt = MT_Terrain(n_query, n_calc)
