import networkx as nx


def edgeffect(G, edge):
    Tx = nx.bfs_tree(G, edge[0])
    Ax = {n for n in Tx.nodes() if nx.shortest_path_length(G, n, edge[1]) + edge['weight'] <
                                   nx.shortest_path_length(G, n, edge[0])}
    r = 0
    for u in Ax:
        Tu = nx.bfs_tree(G, u)
        for v in Tu:
            dold = nx.shortest_path_length(G, u, v)
            dnew = nx.shortest_path_length(G, v, edge[0]) + nx.shortest_path_length(G, u, edge[1]) + edge['weight']
            if dnew < dold:
                r += dold - dnew
    return r

if __name__ == '__main__':
    g = nx.Graph()
    g.add_edge(0, 1, weight=0.2)
    g.add_edge(1, 2, weight=0.6)
    g.add_edge(2, 3, weight=1)
    g.add_edge(3, 4, weight=0.2)
    g.add_edge(4, 5, weight=0.6)
    
    edge = {}
    edge[0] = 1
    edge[1] = 4
    edge['weight'] = 0.6
    print(edgeffect(g, edge))
