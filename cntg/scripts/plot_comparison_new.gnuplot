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

plot '../data/growing_network/urban.gnuplot' i "comparison" u 2:3:xtic(1) t "Urban",\
'../data/growing_network/suburban.gnuplot' i "comparison" u 2:3:xtic(1) t "Intermediate",\
'../data/growing_network/rural.gnuplot' i "comparison" u 2:3:xtic(1) t "Rural"

set output "../images/pref_attachment/nodes.eps"
set title "Network size: network-aware strategy"


plot '../data/pref_attachment/urban.gnuplot' i "comparison" u 2:3:xtic(1) t "Urban",\
'../data/pref_attachment/suburban.gnuplot' i "comparison" u 2:3:xtic(1) t "Intermediate",\
'../data/pref_attachment/rural.gnuplot' i "comparison" u 2:3:xtic(1) t "Rural"
