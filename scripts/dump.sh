for i in `seq 1 10 549`
do
	for j in `seq 147 10 537`
	do
	url="http://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmscartoteca&version=1.3.0&map_resolution=91&map_mnt=cartoteca&SERVICE=WMS&FORMAT=image%2Fpng&REQUEST=GetFeatureInfo&LAYERS=rt_cartoteca.lidar2k&QUERY_LAYERS=rt_cartoteca.lidar2k&STYLES=solo_contorno_con_etichette&FEATURE_COUNT=50&HEIGHT=789&WIDTH=617&SRS=EPSG:25832&VERSION=1.1.1&TRANSPARENT=TRUE&X="$i"&Y="$j"ff&BBOX=649632.21284028%2C4828766.6838479%2C689649.1868769%2C4879809.4043775";
	curl -s $url | grep dest_dsm | awk 'BEGIN {FS =" "} ; {print $3}';
	#curl -s $url;
	done


done
