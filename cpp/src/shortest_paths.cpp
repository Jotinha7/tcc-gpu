#include "shortest_paths.hpp"

#include <queue>
#include <limits>

// Implementação clássica de Dijkstra usando priority_queue.

// No fim, dist[v] é a melhor distância encontrada de source até v.
std::vector<double> dijkstra(const AdjList &graph, int source) {
    const int n = static_cast<int>(graph.size());
    const double INF = std::numeric_limits<double>::infinity();

    std::vector<double> dist(n, INF);
    dist[source] = 0.0;

    using State = std::pair<double, int>;
    std::priority_queue<State, std::vector<State>, std::greater<State>> pq;

    pq.push({0.0, source});

    while (!pq.empty()) {
        auto [d, u] = pq.top();
        pq.pop();

        if (d > dist[u]) {
            continue;
        }

        for (const auto &edge : graph[u]) {
            int v = edge.first;
            double w = edge.second;

            if (dist[v] > dist[u] + w) {
                dist[v] = dist[u] + w;
                pq.push({dist[v], v});
            }
        }
    }

    return dist;
}
