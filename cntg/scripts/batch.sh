python parse_datafiles.py -f ../results/*firenze-growing_network*.csv ../results/*trento-growing_network*.csv ../results/*napoli-growing_network*.csv -o ../data/growing_network/urban.gnuplot
python parse_datafiles.py -f ../results/*sorrento-growing_network*.csv ../results/*mezzolombardo-growing_network*.csv ../results/*barberino-growing_network*.csv -o ../data/growing_network/suburban.gnuplot
python parse_datafiles.py -f ../results/*visciano-growing_network*.csv ../results/*predaia-growing_network*.csv ../results/*pontremoli-growing_network*.csv -o ../data/growing_network/rural.gnuplot

python parse_datafiles.py -f ../results/*firenze-pref_attachment*.csv ../results/*trento-pref_attachment*.csv ../results/*napoli-pref_attachment*.csv -o ../data/pref_attachment/urban.gnuplot
python parse_datafiles.py -f ../results/*sorrento-pref_attachment*.csv ../results/*mezzolombardo-pref_attachment*.csv ../results/*barberino-pref_attachment*.csv -o ../data/pref_attachment/suburban.gnuplot
python parse_datafiles.py -f ../results/*visciano-pref_attachment*.csv ../results/*predaia-pref_attachment*.csv ../results/*pontremoli-pref_attachment*.csv -o ../data/pref_attachment/rural.gnuplot

gnuplot plot_comparison_new.gnuplot1
