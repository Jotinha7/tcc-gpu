#pragma once

#include <vector>
#include <utility>

// Representamos o grafo como uma lista de adjacência:
//
// graph[u] = lista de (v, w), ou seja,
//   uma aresta de u -> v com peso w.
using AdjList = std::vector<std::vector<std::pair<int, double>>>;

// Executa Dijkstra a partir do vértice 'source'.
// Retorna um vetor dist, em que dist[v] é a menor
// distância encontrada de source até v.
//
// Se um vértice não for alcançável, dist[v] será "infinito".
std::vector<double> dijkstra(const AdjList &graph, int source);
