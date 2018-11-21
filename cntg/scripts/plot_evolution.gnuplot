set terminal eps noenhanced
set datafile separator ','

system "mkdir -p ../images"

set output sprintf("../images/%s-bandwidth.eps", filename)
inputfile = sprintf("../data/%s", filename)

set xlabel "Network Size"
set ylabel "Mb/s"


set yrange [0:]
set key below
set title "Bandwidth per node (percentiles)"
plot inputfile u 1:(column('perc_10')) w lp title columnhead ls 1 ps 0.5,\
'' u 1:(column('perc_50')) w lp title columnhead ls 2 ps 0.5,\
'' u 1:(column('perc_90')) w lp title columnhead ls 7 ps 0.5 

set ylabel "Price"
set title "Average price per node"
set output sprintf("../images/%s-price.eps", filename)
plot inputfile u 1:(column('price_per_user')) w lp title columnhead,\
'' u 1:(column('price_per_mbyte')) w lp title columnhead

set ylabel ""
set title "Nodes with less than threshold bandwidth"
set output sprintf("../images/%s-th.eps", filename)
plot inputfile u 1:(column('nodes_below_bw')) w lp title columnhead
