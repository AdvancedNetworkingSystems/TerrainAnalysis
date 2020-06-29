set terminal eps noenhanced
set datafile separator ','

### plot degree and bw distribution

set output "../images/onerun/degreemassfunction.eps"
set xlabel "Degree"
set title "Degree ECDF"
#set log 
plot '../data/degree.txt' u 1:2 w p pt 7 ps 0.7 t ""

set xrange [0:227]
set title "Guaranteed bandwidth per node: local strategy"
set output '../images/onerun/bw-distribution.eps'
set ylabel "Guaranteed bandwidth (Mb/s)"
set xlabel "Node"
set logscale y
plot '../data/onerun/data-vaiano.csv' u 0:2 with lp t ""
set nologscale y

# plot bw, price and devices


inputfile="../data/onerun/stats-vaiano.csv"
set ylabel "Mb/s"
set xlabel "Network size"


set yrange [0:]
set xrange [10:]
set key below
set output "../images/onerun/bw.eps"

set title "Guaranteed Bandwidth per Node (percentiles)"

#NOTE: the data parser has a bug and returns swapped labels, do not remove the title definition

plot inputfile u 1:(column('perc_10')) w lp ls 1 ps 0.5 t "90th perc.",\
'' u 1:(column('perc_50')) w lp ls 2 ps 0.5 t "50th perc.",\
'' u 1:(column('perc_90')) w lp ls 7 ps 0.5 t "10th perc"

set ylabel "Price"
set output "../images/onerun/price.eps"
set title "Average Cost and Devices per Node"
set key below
set yrange [300:500]
set y2range [2:5]
set y2label "Devices per node"
set ylabel "Euro per node"
set y2tics 1  nomirror
set ytics nomirror
plot inputfile u 1:(column('price_per_user')) w lp pt 7 ps 0.5 t "Node Cost",\
'' u 1:(column('antennas_per_node')) w lp t "Devices per node" axes x1y2

#set output "../images/onerun/price_per_mbit.eps"
#set ylabel "Price"
#set title "Average price per node per mb/s"
#plot inputfile u 1:(column('price_per_mbit')) w lp title columnhead

#set output "../images/onerun/antennas_per_node.eps"
#set ylabel ""
#set title "Average number of Devices per Node"
#plot inputfile u 1:(column('antennas_per_node')) w lp title columnhead


