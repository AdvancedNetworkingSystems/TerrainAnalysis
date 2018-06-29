import csv
import matplotlib.pyplot as plt
import networkx as nx


from sys import argv
if __name__ == '__main__':
    G = nx.Graph()
    with open(argv[1], mode='rb') as f:
        csv = csv.reader(f)
        for line in list(csv)[1:]:
            if(line[2] is not '0'):
                G.add_edge(line[0], line[1], weight=line[3])
    components = sorted(nx.biconnected_component_subgraphs(G), key=len, reverse=True)
    for i in components:
        print len(i)
    nx.draw(components[0])
    nx.write_graphml(components[0], argv[1][:-4] + ".graphml")
