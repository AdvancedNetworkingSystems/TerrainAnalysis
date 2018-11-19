import networkx as nx

class EdgeEffect():
    def __init__(self, G, sG):
        self.G = G
        self.sG = sG  # Biggest Connected component

    def restructure_edgeeffect(self, l):
        # for each link that we found is feasible, but we havent added compute
        # the edge effect
        # we do it only for the link between nodes of the main connected
        # component
        edge = {}
        edge[0] = l['src'].gid
        edge[1] = l['dst'].gid
        edge['weight'] = 1  # For now do not use costs
        if not (l['src'].gid in self.sG and l['dst'].gid in self.sG):
            l['effect'] = 0
        else:
            edge['effect'] = self.edgeffect(self.G, edge)
        return edge

    @staticmethod
    def edgeffect(G, edge):
        # First of all convert the graph to undirected graph
        G = G.to_undirected()
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
