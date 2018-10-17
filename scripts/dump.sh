for i in `seq 250 10 1276`
do
	for j in `seq 53 10 805`
	do
	url="http://www502.regione.toscana.it/wmsraster/com.rt.wms.RTmap/wms?map=wmscartoteca&version=1.3.0&map_resolution=91&map_mnt=cartoteca&SERVICE=WMS&FORMAT=image/png&REQUEST=GetFeatureInfo&LAYERS=rt_cartoteca.lidar2k&QUERY_LAYERS=rt_cartoteca.lidar2k&STYLES=solo_contorno_con_etichette&FEATURE_COUNT=50&HEIGHT=978&WIDTH=1511&SRS=EPSG:25832&VERSION=1.1.1&TRANSPARENT=TRUE&X=$i&Y=$j&BBOX=671564.32488661,4879374.4781002,705757.52000123,4901460.8834158&INFO_FORMAT=text/html";
	curl -s $url | grep dest_dsm | awk 'BEGIN {FS =" "} ; {print $3}';
	#curl -s $url;
	done


done
