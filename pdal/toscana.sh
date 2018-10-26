#!/bin/bash

for file in `ls  ~/data/Toscana/Pontremoli/Lidar/*.asc`; do
	pdal pipeline toscana.json --readers.gdal.filename=$file && mv $file $file.loaded
	echo $file loaded
done 

