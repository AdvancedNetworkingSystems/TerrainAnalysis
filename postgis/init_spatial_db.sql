CREATE USER terrain_analysis;
CREATE DATABASE terrain_analysis;
GRANT ALL ON DATABASE terrain_analysis to terrain_analysis;
\connect terrain_analysis terrain_analysis;
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
CREATE INDEX lidar_lyon_index ON lidar_lyon USING GIST(PC_EnvelopeGeometry(pa));
