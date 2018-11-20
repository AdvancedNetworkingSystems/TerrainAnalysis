set terminal eps noenhanced
set datafile separator ','
set output sprintf("%s-bandwidth.eps", filename)

set xlabel "Network Size"
set ylabel "Mb/s"

set key below
set title "Bandwidth per node (percentiles)"
plot filename u 1:(column('perc_10')) w lp title columnhead,\
'' u 1:(column('perc_50')) w lp title columnhead,\
'' u 1:(column('perc_90')) w lp title columnhead, 

set ylabel "Price"
set title "Average price per node"
set output sprintf("%s-price.eps", filename)
plot filename u 1:(column('price_per_user')) w lp title columnhead,\
'' u 1:(column('price_per_mbyte')) w lp title columnhead
