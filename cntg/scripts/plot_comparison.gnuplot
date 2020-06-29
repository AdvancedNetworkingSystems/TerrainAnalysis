set terminal eps
set style fill solid 1.00 border 0
set style histogram errorbars gap 2 lw 1
set style data histogram
#set xtics rotate by -45
set grid ytics
set yrange [0:*]
set datafile separator ","
set xlabel "Minimum Guaranteed Bandwidth"

## comparison of SCENARIOS

set output "../images/growing_network/nodes.eps"
set title "Network size: local strategy"

plot '../data/growing_network/firenze.gnuplot' i "comparison" u 2:3:xtic(1) t "Urban",\
'../data/growing_network/quarrata.gnuplot' i "comparison" u 2:3:xtic(1) t "Suburban",\
'../data/growing_network/vaiano.gnuplot' i "comparison" u 2:3:xtic(1) t "Intermediate",\
'../data/growing_network/pontremoli.gnuplot' i "comparison" u 2:3:xtic(1) t "Rural"


set xtics 1,1,5
set output "../images/growing_network/cost.eps"
set ylabel "Euro"
set title "Average Cost per Node: local strategy"
set style histogram gap 2 
set style data histogram
set yrange [200:300]

plot '../data/growing_network/quarrata.gnuplot' i "comparison" u 1:($4-200) w lp t "Suburban",\
'../data/growing_network/firenze.gnuplot' i "comparison" u 1:($4-200) w lp t "Urban",\
'../data/growing_network/vaiano.gnuplot' i "comparison" u 1:($4-200) w lp t "Intermediate",\
'../data/growing_network/pontremoli.gnuplot' i "comparison" u 1:($4-200) w lp t "Rural"

set output "../images/growing_network/devices-per-node.eps"
set xlabel "Minimum Guaranteed Bandwidth"
set ylabel ""
set title "Average Devices per Node: local strategy"
set yrange [2.7:4]
set ytics 1,0.5,4

plot '../data/growing_network/firenze.gnuplot' i "comparison" u 1:6 w lp t "Urban",\
'../data/growing_network/quarrata.gnuplot' i "comparison" u 1:6 w lp t "Suburban",\
'../data/growing_network/vaiano.gnuplot' i "comparison" u 1:6 w lp t "Intermediate",\
'../data/growing_network/pontremoli.gnuplot' i "comparison" u 1:6 w lp t "Rural"
#
## comparison of strategies: RURAL

set output "../images/comparison-nodes-rural-disadvantaged.eps"
set style fill solid 1.00 border 0
set style histogram errorbars gap 2 lw 1
set style data histogram
set grid ytics
set yrange [0:*]
set title "Network size (rural)"

plot '../data/growing_network/pontremoli.gnuplot' i "comparison" u 2:3:xtic(1) t "Local heuristic",\
'../data/pref_attachment/pontremoli.gnuplot' i "comparison" u 2:3:xtic(1) t "Network-aware heuristic"


set output "../images/comparison-cost-rural-disadvantaged.eps"
set ylabel "Euro"
set title "Average Cost per Node (rural)"
set yrange [300:500]

plot '../data/growing_network/pontremoli.gnuplot' i "comparison" u 1:4 w lp t "Local heuristic",\
'../data/pref_attachment/pontremoli.gnuplot' i "comparison" u 1:4 w lp t "Network-aware heuristic"

set output "../images/comparison-devices-per-node-rural-disadvantaged.eps"
set ylabel ""
set title "Average Devices per Node (rural)"
set yrange [2:4]


plot '../data/growing_network/pontremoli.gnuplot' i "comparison" u 1:6 w lp t "Local heuristic",\
'../data/pref_attachment/pontremoli.gnuplot' i "comparison" u 1:6 w lp t "Network-aware heuristic"


## comparison of strategies: INTERMEDIATE

set output "../images/comparison-nodes-rural.eps"
set style fill solid 1.00 border 0
set style histogram errorbars gap 2 lw 1
set style data histogram
set grid ytics
set yrange [0:*]
set title "Network size (intermediate)"

plot '../data/growing_network/vaiano.gnuplot' i "comparison" u 2:3:xtic(1) t "Local heuristic",\
'../data/pref_attachment/vaiano.gnuplot' i "comparison" u 2:3:xtic(1) t "Network-aware heuristic"


set output "../images/comparison-cost-rural.eps"
set ylabel "Euro"
set title "Average Cost per Node (intermediate)"
set yrange [300:500]

plot '../data/growing_network/vaiano.gnuplot' i "comparison" u 1:4 w lp t "Local heuristic",\
'../data/pref_attachment/vaiano.gnuplot' i "comparison" u 1:4 w lp t "Network-aware heuristic"

set output "../images/comparison-devices-per-node-rural.eps"
set ylabel ""
set title "Average Devices per Node (intermediate)"
set yrange [2:4]


plot '../data/growing_network/vaiano.gnuplot' i "comparison" u 1:6 w lp t "Local heuristic",\
'../data/pref_attachment/vaiano.gnuplot' i "comparison" u 1:6 w lp t "Network-aware heuristic"


## comparison of strategies: URBAN

set output "../images/comparison-nodes-urban.eps"
set style fill solid 1.00 border 0
set style histogram errorbars gap 2 lw 1
set style data histogram
set grid ytics
set yrange [0:*]
set title "Network size (urban)"

plot '../data/growing_network/firenze.gnuplot' i "comparison" u 2:3:xtic(1) t "Local heuristic",\
'../data/pref_attachment/firenze.gnuplot' i "comparison" u 2:3:xtic(1) t "Network-aware heuristic"


set output "../images/comparison-cost-urban.eps"
set ylabel "Euro"
set title "Average Cost per Node (urban)"
set yrange [300:500]

plot '../data/growing_network/firenze.gnuplot' i "comparison" u 1:4 w lp t "Local heuristic",\
'../data/pref_attachment/firenze.gnuplot' i "comparison" u 1:4 w lp t "Network-aware heuristic"

set output "../images/comparison-devices-per-node-urban.eps"
set ylabel ""
set title "Average Devices per Node (urban)"
set yrange [2:4]


plot '../data/growing_network/firenze.gnuplot' i "comparison" u 1:6 w lp t "Local heuristic",\
'../data/pref_attachment/firenze.gnuplot' i "comparison" u 1:6 w lp t "Network-aware heuristic"


## comparison of strategies: ALL

set xtics 1,1,5
set output "../images/comparison-nodes-all.eps"
set style fill solid 1.00 border 0
set style histogram errorbars gap 2 lw 1
set style data histogram
set grid ytics
set yrange [0:*]
set title "Network size: network-aware strategy"
set ytics auto

plot '../data/pref_attachment/firenze.gnuplot' i "comparison" u 2:3:xtic(1) t "Urban",\
'../data/pref_attachment/quarrata.gnuplot' i "comparison" u 2:3:xtic(1) t "Suburban",\
'../data/pref_attachment/vaiano.gnuplot' i "comparison" u 2:3:xtic(1) t "Intermediate",\
'../data/pref_attachment/pontremoli.gnuplot' i "comparison" u 2:3:xtic(1) t "Rural"



set output "../images/comparison-cost-all.eps"
set ylabel "Euro"
set title "Average Cost per Node: network-aware strategy"
set yrange [140:210]
set ytics 100,25,300
set xtics 1,1,5

plot '../data/pref_attachment/firenze.gnuplot' i "comparison" u 1:($4-200) w lp t "Urban",\
'../data/pref_attachment/quarrata.gnuplot' i "comparison" u 1:($4-200) w lp t "Suburban",\
'../data/pref_attachment/vaiano.gnuplot' i "comparison" u 1:($4-200) w lp t "Intermediate",\
'../data/pref_attachment/pontremoli.gnuplot' i "comparison" u 1:($4-200) w lp t "Rural"

set ytics 1,1,5
set output "../images/comparison-devices-per-node-all.eps"
set ylabel ""
set title "Average Devices per Node: network-aware strategy"
set yrange [2:3]
set xtics 1,1,5
set ytics 1,0.5,4
plot '../data/pref_attachment/firenze.gnuplot' i "comparison" u 1:6 w lp t "Urban",\
'../data/pref_attachment/quarrata.gnuplot' i "comparison" u 1:6 w lp t "Suburban",\
'../data/pref_attachment/vaiano.gnuplot' i "comparison" u 1:6 w lp t "Intermediate",\
'../data/pref_attachment/pontremoli.gnuplot' i "comparison" u 1:6 w lp t "Rural"


## comparison of strategies: bandwidth distrbution

inputfile="../data/growing_network/vaiano.gnuplot"
x = system("grep '#B_' ".inputfile." | sed 's/\#//' | sort -n")
labels = system("grep '#B_' ".inputfile." | sed 's/\#B_//' |  sort -n ")

set autoscale x
set yrange [0.5:100]
set ytics auto
set xtics auto
set output '../images/growing_network/bw-distribution.eps'
set logscale y
set ylabel "Mb/s"
set xlabel "Nodes" 
set title "Guaranteed bandwidth per node (all runs): local strategy "
set xrange [0:4000]
set key below
f(x) = 1

plot for [l=1:words(x)] inputfile i word(x, l) with p pt l ps 0.5 t "Min. BW: ".word(labels, l)." Mb/s" 


inputfile="../data/pref_attachment/vaiano.gnuplot"
x = system("grep '#B_' ".inputfile." | sed 's/\#//' | sort -n")
labels = system("grep '#B_' ".inputfile." | sed 's/\#B_//' |  sort -n ")

set title "Guaranteed bandwidth per node (all runs): network-aware strategy "
set output '../images/pref_attachment/bw-distribution.eps'
plot for [l=1:words(x)] inputfile i word(x, l) with p pt l ps 0.5 t "Min. BW: ".word(labels, l)." Mb/s" 

