import csv
from collections import defaultdict

mcs_AC_file = '80211/tables/mcs-AC.csv'
mcs_N_file = '80211/tables/mcs-N.csv'


def rec_dd():
    return defaultdict(rec_dd)


mcs_N = rec_dd()
mcs_AC = rec_dd()

tx_power_regulation_eu = {
        '2.4': 20,
        '5': 30}

default_channel_width = 40

# EU allows channel 100-144 (5470-5725 MHz) for outdoor
indipendent_channels_EU = {20: [100, 104, 108, 112, 116, 120, 124, 128, 132,
                                136, 140, 144],
                           40: [102, 110, 118, 126, 134, 142],
                           80: [106, 122, 138],
                           160: [114]}
channels = indipendent_channels_EU[default_channel_width]


def load_mcs_tables(gi="400 ns GI"):
    with open(mcs_N_file) as f:
        for row in csv.DictReader(f):
            try:
                b = float(row[gi])
            except ValueError:
                b = 0
            mcs_N['MCS'+row['MCS']][int(row['channel'])] = b
    with open(mcs_AC_file) as f:
        for row in csv.DictReader(f):
            try:
                b = float(row[gi])
            except ValueError:
                b = 0
            mcs_AC['MCS'+row['MCS']][int(row['streams'])]\
                                    [int(row['channel'])] = b
