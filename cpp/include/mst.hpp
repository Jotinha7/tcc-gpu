#pragma once

#include <vector>
#include <tuple>

// Mesmo tipo de grafo que usamos em shortest_paths.hpp
using AdjList = std::vector<std::vector<std::pair<int, double>>>;

// Aresta representada como (peso, u, v)
using Edge = std::tuple<double, int, int>;

// Resultado da MST: lista de arestas (u, v, w)
struct MstResult {
    std::vector<Edge> edges;
    double total_cost;
};

// Calcula uma árvore geradora mínima usando Kruskal.
//
// Parâmetros:
//   - n: número de vértices
//   - edges: lista de arestas (w, u, v)
//
// Retorna:
//   - MstResult com as arestas da MST e o custo total.
//
// Se o grafo não for conexo, a MST resultante ligará apenas a componente
// alcançável a partir das arestas fornecidas.
MstResult kruskal_mst(int n, std::vector<Edge> edges);
