set terminal eps noenhanced
set datafile separator ','
set macro
system "mkdir -p ../images"

inputfile="../data/growing_network/all.gnuplot"
x = system("grep '#B_' ".inputfile." | sed 's/\#//' | sort -n")
labels = system("grep '#B_' ".inputfile." | sed 's/\#B_//' |  sort -n ")
print x
set output '../images/growing_network/bw-distribution.eps'
set logscale y
set ylabel "Mb/s"
set xlabel "Nodes" 
set title "Guaranteed bandwidth per user (all runs)"
set key below
f(x) = 1

plot for [l=1:words(x)] inputfile i word(x, l) with p pt l ps 0.5 t "Min. BW: ".word(labels, l)." Mb/s" 


inputfile="../data/pref_attachment/all.gnuplot"
x = system("grep '#B_' ".inputfile." | sed 's/\#//' | sort -n")
labels = system("grep '#B_' ".inputfile." | sed 's/\#B_//' |  sort -n ")

set output '../images/pref_attachment/bw-distribution.eps'
plot for [l=1:words(x)] inputfile i word(x, l) with p pt l ps 0.5 t "Min. BW: ".word(labels, l)." Mb/s" 

