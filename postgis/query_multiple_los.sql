SELECT b1,b2
FROM(
	SELECT array_agg(array[distance, z]) as profile, b1, b2
	FROM(
		SELECT distance, z, b1, b2
		FROM (
			SELECT distinct on (distance) PC_Get(pts, 'z') as z, ST_Distance(pts::geometry, p1, true) as distance, b1, b2
			FROM ( 
				WITH buffer AS(
					SELECT ST_Buffer_Meters(ST_MakeLine(ST_Centroid(osm1.geom), ST_Centroid(osm2.geom)), 1) as line, ST_Centroid(osm1.geom) as p1, osm1.gid as b1, osm2.gid as b2
					FROM ctr_firenze osm1, ctr_firenze osm2
					WHERE osm1.gid  IN (70261)
					AND osm2.gid IN (70261, 70653, 70122, 71806, 70246, 70910, 71218, 69563, 69563, 70877, 70940, 70236)
					AND osm1.gid != osm2.gid
				)
				SELECT PC_Explode(lidar_toscana.pa) as pts, b1, b2, p1, line FROM lidar_toscana
				JOIN buffer  ON PC_Intersects(pa, buffer.line)
			)_
			WHERE ST_Intersects(pts::geometry, line)
		)_
		ORDER BY b1, b2, distance
	)_
	GROUP BY b1, b2
	)_
WHERE line_of_sight(profile)	