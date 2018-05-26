class terrain_RF:
    def __init__(self, cur, dataset, frequency=5):

        self.srid = '4326'
        self.cur = cur
        self.dataset = dataset
        if self.dataset == 'toscana':
            self.osm_table = 'centro_buildings'
            self.lidar_table = 'lidar_toscana'
            self.buff = 0.5  # 1 point per meter
        elif self.dataset == 'lyon':
            self.osm_table = 'lyon_buildings'
            self.lidar_table = 'lidar_lyon'
            self.buff = 0.15  # 3-5 point per meter
        else:
            raise Exception("Dataset not found")

    def set_workingarea(self, xmin, ymin, xmax, ymax):
        self.working_area = (xmin, ymin, xmax, ymax)

    def profile_osm(self, p1, p2, downscale=False):
        self.cur.execute("""WITH p1 AS(
                            SELECT ST_Centroid(geom) as pt FROM {0}
                            WHERE  gid={2}
                            ),
                            p2 as(
                                SELECT ST_Centroid(geom) as pt FROM {0}
                                WHERE  gid={3}
                            ),
                            buffer AS(
                                SELECT ST_Buffer_Meters(ST_MakeLine(p1.pt, p2.pt), {4}) AS line FROM p1,p2
                            ),
                            lidar AS(
                                WITH
                                patches AS (
                                SELECT pa FROM {1}
                                JOIN buffer ON PC_Intersects(pa, line)
                                ),
                                pa_pts AS (
                                SELECT PC_Explode(pa) AS pts FROM patches
                                ),
                                building_pts AS (
                                SELECT pts, line FROM pa_pts JOIN buffer
                                ON ST_Intersects(line, pts::geometry)
                                )
                                SELECT
                                PC_Get(pts, 'z') AS z, ST_Distance(pts::geometry, p1.pt, true) as distance
                                FROM building_pts, p1
                                )
                            SELECT lidar.z, lidar.distance  FROM lidar ORDER BY distance;""".format(self.osm_table, self.lidar_table, p1, p2, self.buff))
        q_result = self.cur.fetchall()
        if self.cur.rowcount == 0:
            raise Exception("No profile")
        # remove invalid points
        profile = filter(lambda a: a[0] != -9999, q_result)
        # cast everything to float
        y, d = zip(*profile)
        y = [float(i) for i in y]
        d = [float(i) for i in d]
        return zip(d, y)

    def get_buildings(self):
        self.cur.execute("""SELECT gid, z FROM {0}
                            WHERE geom && ST_MakeEnvelope({1}, {2}, {3}, {4}, {5})
                        """.format(self.osm_table,
                                   self.working_area[0], self.working_area[1], self.working_area[2], self.working_area[3],
                                   self.srid))
        buildings = list(self.cur)
        return buildings

    def update_building_heigth(self):
        query = """UPDATE {0} SET z = elevs.z
                    FROM (
                      -- For every building, all intersecting patches
                      WITH patches AS (
                        SELECT
                          {0}.gid AS buildings_gid,
                          {1}.id AS medford_id,
                          {1}.pa AS pa
                        FROM {1}
                        JOIN {0}
                        ON PC_Intersects(pa, geom)
                        WHERE lyon_buildings.geom && ST_MakeEnvelope({2},{3},{4},{5},{6})
                      ),
                      -- Explode those patches into points, remembering
                      -- which building they were associated with
                      pa_pts AS (
                        SELECT buildings_gid, PC_Explode(pa) AS pts FROM patches
                      )
                      -- Use the building associations to efficiently
                      -- spatially test the points against the building footprints
                      -- Summarize per building
                      SELECT
                        buildings_gid,
                        Avg(PC_Get(pts, 'z')) AS z
                      FROM pa_pts
                      JOIN {0}
                      ON {0}.gid = buildings_gid
                      WHERE ST_Intersects({0}.geom, pts::geometry)
                      GROUP BY buildings_gid
                    ) AS elevs
                    -- Join calculated elevations to original buildings table
                    WHERE elevs.buildings_gid = gid;
                """.format(self.osm_table, self.lidar_table,
                           self.working_area[0], self.working_area[1], self.working_area[2], self.working_area[3],
                           self.srid)
        self.cur.execute(query)
        return self.cur.fetchall()

    def distance(self, b1, b2):
        self.cur.execute('''WITH
                            building1 AS(
                            SELECT gid, geom FROM {0}
                            WHERE gid = {1}
                            ),
                            building2 AS(
                            SELECT gid, geom FROM {0}
                            WHERE gid = {2}
                            )
                            SELECT ST_Distance_Sphere(ST_Centroid(building1.geom), ST_Centroid(building2.geom))
                            FROM building1, building2
                        '''.format(self.osm_table, b1, b2))
        distance = float(self.cur.fetchall()[0][0])
        return distance
