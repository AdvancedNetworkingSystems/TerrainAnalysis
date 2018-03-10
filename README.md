# TerrainAnalysis
Steps to reproduce the work:

* Install the latest version of postgresql with postgis extension for your system}

```bash
apt install postgresql-9.3-postgis-2.1 postgis postgresql-server-9.3-dev
```
  * Create the tables and the extensions in the postgis db:
```SQL
CREATE EXTENSION postgis;
CREATE EXTENSION pointcloud;
CREATE EXTENSION pointcloud_postgis;
CREATE TABLE lidar_toscana (
    id SERIAL PRIMARY KEY,
    pa PCPATCH(1)
);
CREATE INDEX lidar_toscana_index ON lidar_toscana USING GIST(PC_EnvelopeGeometry(pa));
CREATE TABLE lidar_lyon (
    id SERIAL PRIMARY KEY,
    pa PCPATCH(1)
);

```
* Install pdal and it's dependencies (laszip support mandatory for certain dataset. eg: lyon)
* Download the lidar files for your zone (for tuscany and lyon you can use the list of url provided in this repository)
```bash
for i in `cat tiles_piana_url.txt`
do 
  wget $i -P ~/lidar/centro_italy/zip
done
```
```bash
for i in `cat tiles_lyon_url.txt`
do 
  wget $i -P ~/lidar/lyon/zip
done
```
* Download the osm building files from an osm mirror
* Insert the osm building using the `shp2pgsql` command
```bash
shp2pgsql -Gs 4326 -I ~/osm/lyon/gis.osm_buildings_a_free_1.shp  lyon_buildings | sudo -u postgres psql
shp2pgsql -Gs 4326 -I ~/osm/centro_italy/gis.osm_buildings_a_free_1.shp  centro_buildings | sudo -u postgres psql
```
* Use the provided pipeline to insert the .asc or .laz lidar files into the postgis db
If you are using different lidar files rembember to fix the SRID in the pipeline json definition
```bash
for i in `ls ~/lidar/centro_italy/*.asc`
do 
  pdal pipeline toscana.json --readers.gdal.filename=$i
done
#laz
for i in `ls ~/lidar/rhone/*.laz`
do 
  pdal pipeline lyon.json --readers.las.filename=$i
done
```
