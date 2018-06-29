import csv

measures = {}
with open("../data/lyon_links_1x1.csv") as f1:
    lidar_csv = csv.reader(f1)
    for line in lidar_csv:
        measures[line[0] + "-" + line[1]] = {
            "status_lidar": line[2],
            "status_lidar_ds": line[4],
            "loss_lidar": line[3],
            "loss_lidar_ds": line[5]
        }

with open("../data/lyon_srtm_links_1x1.csv") as f2:
    srtm_csv = csv.reader(f2)
    try:
        for line in srtm_csv:
            measures[line[0] + "-" + line[1]]["status_srtm"] = line[2]
            measures[line[0] + "-" + line[1]]["loss_srtm"] = line[3]
    except KeyError:
        print "missing key"


with open("../data/lyon_all_links_1x1.csv", "w") as fw:
    print >> fw, "link,status_lidar,loss_lidar,status_lidar_ds,loss_lidar_ds,status_srtm,loss_srtm"
    for key in measures.keys():
        measure = measures[key]
        status_lidar = measure["status_lidar"]
        status_lidar_ds = measure["status_lidar_ds"]
        loss_lidar = measure["loss_lidar"]
        try:
            status_srtm = measure["status_srtm"]
            loss_srtm = measure["loss_srtm"]
        except KeyError:
            loss_srtm = 0
            status_srtm = -2
        loss_lidar_ds = measure["loss_lidar_ds"]
        print >> fw, "%s,%s,%s,%s,%s,%s,%s" % ((key, status_lidar, loss_lidar, status_lidar_ds, loss_lidar_ds, status_srtm, loss_srtm))
