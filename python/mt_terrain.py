import multiprocessing as mp
import math
import psycopg2
import numpy
import os
import itertools
import sys
import csv
import time
import progressbar
from shapely import errors
from random import shuffle
from link import Link, ProfileException
from terrain_rf import terrain_RF
from psycopg2.pool import ThreadedConnectionPool
from more_itertools import chunked

class MT_Terrain():
    def __init__(self, n_querier, n_calc, working_area, dataset):
        self.workers_query_result_q = mp.Queue()
        DSN = "postgresql://gabriel:qwerasdf@192.168.184.102/postgres"
        self.tcp = ThreadedConnectionPool(1, 100, DSN)
        conn = self.tcp.getconn()
        cur = conn.cursor()
        self.querier = []
        self.calc = []
        self.go = True
        self.dataset = dataset
        self.working_area = working_area
        self.processed_link = mp.Value('i', 0)
        self._counter_lock = mp.Lock()
        tf = terrain_RF(cur=cur, dataset=self.dataset, working_area=self.working_area)
        buildings = tf.get_buildings()
        self.dict_h = dict(buildings)
        gid, h = zip(*buildings)
        gid = set(gid)
        self.tcp.putconn(conn, close=True)
        buildings_pair = set(itertools.combinations(gid, 2))
        self.link_filename = "../data/" + tf.dataset + "_links.csv"
        try:
            with open(self.link_filename + "_0", 'rb') as fr:
                link_csv = csv.reader(fr, delimiter=',')
                already_proc = set()
                for line in link_csv:
                    already_proc.add((int(line[0]), int(line[1])))
                buildings_pair = buildings_pair - already_proc
        except IOError:
            pass
        self.tot_link = len(buildings_pair)
        print "%d links left to estimate" % len(buildings_pair)
        chunk_size = self.tot_link / n_querier
        chunks = list(chunked(buildings_pair, chunk_size))
        with open(self.link_filename + "_0", 'a') as fl:
            print >> fl, "b1,b2,status,loss,status_downscale,loss_downscale, status_srtm, loss_srtm"
        self.start_time = time.time()
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
        time.sleep(1)
        widgets = [
            'Test: ', progressbar.Percentage(),
            ' ', progressbar.Bar(marker='0', left='[', right=']'),
            ' ', progressbar.ETA(),
            ' ', progressbar.FileTransferSpeed(unit="Link"),
        ]
        bar = progressbar.ProgressBar(
            widgets=widgets,
            max_value=self.tot_link
        ).start()
        while(self.go):
            bar.update(self.processed_link.value, force=True)
            time.sleep(1)
        bar.finish()

    def queryWorker(self, worker_id, buildings_pairs):
        conn = self.tcp.getconn()
        cur = conn.cursor()
        tf = terrain_RF(cur=cur, dataset=self.dataset, working_area=self.working_area)
        tf_srtm = terrain_RF(cur=cur, dataset=self.dataset + "_srtm", working_area=self.working_area)
        for buildings_pair in buildings_pairs:
            id1 = buildings_pair[0]
            id2 = buildings_pair[1]
            try:
                profile = tf.profile_osm(id1, id2)
            except ProfileException:
                profile = None
            try:
                profile_srtm = tf_srtm.profile_osm(id1, id2)
            except ProfileException:
                profile_srtm = None
            result = {"id1": id1,
                      "id2": id2,
                      "profile": profile,
                      "profile_srtm": profile_srtm,
                      "p1": (0.0, self.dict_h[id1]),
                      "p2": (tf.distance(id1, id2), self.dict_h[id2])
                      }
            self.workers_query_result_q.put(result)
        self.tcp.putconn(conn, close=True)

    def calcWorker(self, worker_id):
        while(self.go):
            # Take ORDER
            if self.workers_query_result_q.qsize() > 3:
                print self.workers_query_result_q.qsize()
            order = self.workers_query_result_q.get()
            profile = order["profile"]
            profile_srtm = order["profile_srtm"]
            id1 = order["id1"]
            id2 = order["id2"]
            # Normal profile
            try:
                link = Link(profile)
                loss, status = link.loss_calculator()
            except (ZeroDivisionError, ProfileException), e:
                loss = 0
                status = -1
            # Downscaled profile
            try:
                link_ds = Link(profile)
                loss_ds, status_ds = link_ds.loss_calculator(downscale=3)
            except (ZeroDivisionError, ProfileException), e:
                loss_ds = 0
                status_ds = -1

            # SRTM Profile
            try:
                link_srtm = Link(profile_srtm)
                loss_srtm, status_srtm = link_srtm.loss_calculator()
            except ProfileException, e:
                status_srtm = 1
                loss_srtm = 0
                #TODO: CALC LOSS for these weird links
            except ZeroDivisionError, e:
                status_srtm = -1
                loss_srtm = 0
            with self._counter_lock:
                self.processed_link.value += 1
            with open("%s_%d" % (self.link_filename, worker_id), 'a') as fl:
                print >> fl, "%s,%s,%d,%f,%d,%f,%d,%f" % (id1, id2, status, loss, status_ds, loss_ds, status_srtm, loss_srtm)
                # if status > 0:
                #     print "Worker %d: %s to %s has status %d with loss %f, received pwr %f" % (worker_id, id1, id2, status, loss, 23 + 16 + 16 - loss)

if __name__ == '__main__':
    n_query = int(sys.argv[1])
    n_calc = int(sys.argv[2])
    working_area = (4.8411, 45.7613, 4.8528, 45.7681)
    dataset = 'lyon'
    mt = MT_Terrain(n_query, n_calc, working_area, dataset)
