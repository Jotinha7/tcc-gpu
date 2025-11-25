#include "mst.hpp"

#include <algorithm>
#include <numeric>

struct DSU {
    std::vector<int> parent;
    std::vector<int> rank;

    DSU(int n) : parent(n), rank(n, 0) {
        std::iota(parent.begin(), parent.end(), 0);
    }

    int find(int x) {
        if (parent[x] == x) return x;
        return parent[x] = find(parent[x]);
    }

    bool unite(int a, int b) {
        a = find(a);
        b = find(b);
        if (a == b) return false;
        if (rank[a] < rank[b]) std::swap(a, b);
        parent[b] = a;
        if (rank[a] == rank[b]) rank[a]++;
        return true;
    }
};

MstResult kruskal_mst(int n, std::vector<Edge> edges) {
    // Ordena arestas por peso crescente
    std::sort(edges.begin(), edges.end(),
              [](const Edge &a, const Edge &b) {
                  return std::get<0>(a) < std::get<0>(b);
              });

    DSU dsu(n);
    MstResult res;
    res.total_cost = 0.0;

    for (const auto &e : edges) {
        double w;
        int u, v;
        std::tie(w, u, v) = e;

        if (dsu.unite(u, v)) {
            res.edges.push_back(e);
            res.total_cost += w;
        }
    }

    return res;
}
