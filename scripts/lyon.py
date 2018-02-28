import json, os

with open("lyon.json", 'r') as f:
	j = json.load(f)
	for elem in  j['values']:
		print 'https://download.data.grandlyon.com/files/grandlyon/imagerie/mnt2015/lidar/'+elem['nom'].replace(' ', '')+'.zip'
	
