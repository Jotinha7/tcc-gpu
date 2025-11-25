#include <iostream>
#include <vector>
#include <tuple>
#include <set>

#include "mst.hpp"
#include "shortest_paths.hpp"  // ainda não vamos usar Dijkstra aqui, mas já fica pronto

// Função para podar folhas Steiner:
// Recebe:
//  - n: número de vértices
//  - mst_edges: arestas da MST (w, u, v)
//  - terminals: conjunto de vértices obrigatórios R
//
// Retorna:
//  - lista de arestas (w, u, v) da árvore podada
std::vector<Edge> prune_steiner_leaves(
    int n,
    const std::vector<Edge> &mst_edges,
    const std::set<int> &terminals
) {
    // Construir lista de adjacência da MST
    std::vector<std::vector<int>> adj(n);
    for (const auto &e : mst_edges) {
        double w;
        int u, v;
        std::tie(w, u, v) = e;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Grau atual de cada vértice na árvore
    std::vector<int> degree(n, 0);
    for (int u = 0; u < n; ++u) {
        degree[u] = (int)adj[u].size();
    }

    // Ativo = vértice ainda na árvore
    std::vector<bool> active(n, false);
    for (int u = 0; u < n; ++u) {
        if (degree[u] > 0) {
            active[u] = true;
        }
    }

    bool removed = true;
    while (removed) {
        removed = false;
        for (int u = 0; u < n; ++u) {
            // Se já não está mais na árvore ou não é folha, ignora
            if (!active[u]) continue;
            if (degree[u] != 1) continue;

            // Se for terminal, não pode remover
            if (terminals.count(u)) continue;

            // Remover a folha u
            active[u] = false;
            removed = true;

            // Encontrar seu vizinho único e atualizar grau
            for (int v : adj[u]) {
                if (active[v]) {
                    degree[v]--;
                }
            }
            degree[u] = 0;
        }
    }

    // Reconstroi a lista de arestas apenas com vértices ativos
    std::vector<Edge> pruned_edges;
    for (const auto &e : mst_edges) {
        double w;
        int u, v;
        std::tie(w, u, v) = e;
        if (active[u] && active[v]) {
            pruned_edges.push_back(e);
        }
    }

    return pruned_edges;
}

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int n, m;
    if (!(std::cin >> n >> m)) {
        std::cerr << "Erro ao ler n e m.\n";
        return 1;
    }

    std::vector<Edge> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        double w;
        std::cin >> u >> v >> w;
        edges.push_back({w, u, v});
    }

    int t;
    std::cin >> t;
    std::set<int> terminals;
    for (int i = 0; i < t; ++i) {
        int r;
        std::cin >> r;
        terminals.insert(r);
    }

    // Calcula MST do grafo inteiro
    MstResult mst = kruskal_mst(n, edges);

    // Poda folhas Steiner
    std::vector<Edge> pruned = prune_steiner_leaves(n, mst.edges, terminals);

    // Calcula custo total da árvore podada
    double total_cost = 0.0;
    for (const auto &e : pruned) {
        total_cost += std::get<0>(e);
    }

    // Saída simples:
    //
    // Primeiro linha: custo total
    // Depois: lista de arestas u v w
    std::cout << "COST " << total_cost << "\n";
    std::cout << "EDGES\n";
    for (const auto &e : pruned) {
        double w;
        int u, v;
        std::tie(w, u, v) = e;
        std::cout << u << " " << v << " " << w << "\n";
    }

    return 0;
}
