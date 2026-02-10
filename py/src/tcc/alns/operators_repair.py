from __future__ import annotations

import heapq
import random
from typing import Dict, List, Tuple, Optional

from tcc.instance import Instance
from tcc.solution import Solution, TreeEdge

from .partial_state import PartialState
from .operators_destroy import compute_cluster_components  # DSU do Dia 02


def _norm_edge(e: TreeEdge) -> TreeEdge:
    u, v = e
    return (u, v) if u < v else (v, u)


def build_weight_lookup(inst: Instance) -> Dict[Tuple[int, int], float]:
    """Mapa rápido w(u,v). Coloca as duas direções pra facilitar."""
    w: Dict[Tuple[int, int], float] = {}
    for u, v, c in inst.edges:
        cc = float(c)
        w[(u, v)] = cc
        w[(v, u)] = cc
    return w


def build_adj(inst: Instance) -> List[List[Tuple[int, float]]]:
    """Adjacência (lista) para Dijkstra."""
    adj: List[List[Tuple[int, float]]] = [[] for _ in range(inst.n)]
    for u, v, c in inst.edges:
        cc = float(c)
        adj[u].append((v, cc))
        adj[v].append((u, cc))
    return adj

# Dijkstra multi-source

def dijkstra_all(
    inst: Instance,
    adj: List[List[Tuple[int, float]]],
    sources: List[int],
) -> Tuple[List[float], List[int]]:
    """
    Dijkstra multi-source completo:
      - retorna dist[] e parent[] pra reconstruir caminho até alguma fonte
    """
    INF = 10**30
    n = inst.n
    dist = [INF] * n
    parent = [-1] * n
    pq: List[Tuple[float, int]] = []

    for s in sources:
        dist[s] = 0.0
        parent[s] = -1
        heapq.heappush(pq, (0.0, s))

    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue
        for v, w_uv in adj[u]:
            nd = d + w_uv
            if nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(pq, (nd, v))

    return dist, parent


def reconstruct_path_edges(parent: List[int], target: int) -> List[TreeEdge]:
    """
    Reconstrói o caminho (lista de arestas) voltando do target até alguma fonte (parent=-1).
    """
    edges: List[TreeEdge] = []
    cur = target
    while parent[cur] != -1:
        p = parent[cur]
        edges.append(_norm_edge((p, cur)))
        cur = p
    edges.reverse()
    return edges


# Repair R1 — reconecta ganancioso com Dijkstra

def repair_r1_dijkstra(inst: Instance, ps: PartialState, rng: random.Random) -> Solution:
    """
    R1: reconectar componentes usando Dijkstra multi-source repetidamente.

    Entrada:
      ps.local_edges: NÃO muda
      ps.global_edges_remaining: floresta global
      ps.components: componentes no nível de clusters

    Saída:
      Solution com local_edges intactas + global_edges reparadas.
    """
    adj = build_adj(inst)
    w = build_weight_lookup(inst)

    local_edges = [_norm_edge(e) for e in ps.local_edges]
    global_edges = [_norm_edge(e) for e in ps.global_edges_remaining]
    global_set = set(global_edges)

    while True:
        components, cluster_to_component = compute_cluster_components(inst, global_edges)
        if len(components) <= 1:
            break

        # componente base: se D2 marcou um cluster, usa o componente dele
        if ps.destroyed_cluster is not None:
            base_component_id = cluster_to_component[ps.destroyed_cluster]
        else:
            base_component_id = rng.randrange(len(components))

        base_clusters = components[base_component_id]

        # fontes = todos os terminais desses clusters
        sources: List[int] = []
        for ck in base_clusters:
            sources.extend(inst.clusters[ck])

        dist, parent = dijkstra_all(inst, adj, sources)

        # alvo = terminal mais barato que esteja fora da componente base
        best_target = None
        best_cost = 10**30

        for k in range(len(inst.clusters)):
            if cluster_to_component[k] == base_component_id:
                continue
            for v in inst.clusters[k]:
                if dist[v] < best_cost:
                    best_cost = dist[v]
                    best_target = v

        if best_target is None:
            raise RuntimeError("R1: não encontrou conexão para outra componente (inesperado).")

        path_edges = reconstruct_path_edges(parent, best_target)
        if not path_edges:
            raise RuntimeError("R1: caminho reconstruído vazio (inesperado).")

        for e in path_edges:
            if e not in global_set:
                global_set.add(e)
                global_edges.append(e)

    final_edges = list(local_edges) + list(global_edges)

    cost = 0.0
    for (u, v) in final_edges:
        cost += w[(u, v)]

    return Solution(instance_name=inst.name, cost=cost, edges=final_edges)


# Repair R3  — MST entre componentes + expandir caminhos

def prim_mst_components(weights: List[List[float]]) -> List[Tuple[int, int]]:
    """
    MST por Prim em um grafo completo com pesos weights[i][j].
    Retorna lista de arestas (u,v) da MST no nível de componentes.
    """
    n = len(weights)
    if n <= 1:
        return []

    INF = 10**30
    in_mst = [False] * n
    key = [INF] * n
    parent = [-1] * n

    key[0] = 0.0

    for _ in range(n):
        u = -1
        best = INF
        for i in range(n):
            if not in_mst[i] and key[i] < best:
                best = key[i]
                u = i

        if u == -1:
            break

        in_mst[u] = True

        for v in range(n):
            if in_mst[v] or v == u:
                continue
            w = weights[u][v]
            if w < key[v]:
                key[v] = w
                parent[v] = u

    edges = []
    for v in range(1, n):
        if parent[v] == -1:
            raise RuntimeError("Prim falhou: MST desconectada (inesperado em grafo completo).")
        edges.append((parent[v], v))
    return edges


def repair_r3_mst_components(inst: Instance, ps: PartialState, rng: random.Random) -> Solution:
    """
    R3:
      1) calcula os componentes (no nível de clusters) depois do destroy
      2) para cada componente i, roda Dijkstra multi-source a partir dela
         - distâncias até todas as outras componentes
         - guarda um target para reconstruir caminho
      3) constrói matriz weights entre componentes
      4) faz MST entre componentes (Prim)
      5) expande cada aresta da MST em caminho real e adiciona ao global
    """
    adj = build_adj(inst)
    wlookup = build_weight_lookup(inst)

    local_edges = [_norm_edge(e) for e in ps.local_edges]
    global_edges = [_norm_edge(e) for e in ps.global_edges_remaining]
    global_set = set(global_edges)

    components, cluster_to_component = compute_cluster_components(inst, global_edges)
    c = len(components)

    if c <= 1:
        final_edges = list(local_edges) + list(global_edges)
        cost = sum(wlookup[(u, v)] for (u, v) in final_edges)
        return Solution(instance_name=inst.name, cost=cost, edges=final_edges)

    # comp_vertices[i] = todos os terminais que pertencem aos clusters daquela componente
    comp_vertices: List[List[int]] = []
    for comp in components:
        verts = []
        for ck in comp:
            verts.extend(inst.clusters[ck])
        comp_vertices.append(verts)

    # Para cada componente i:
    # - roda Dijkstra de todas fontes em comp_vertices[i]
    # - escolhe melhor terminal em cada componente j como alvo
    parents: List[List[int]] = []
    dist_lists: List[List[float]] = []
    best_target: List[List[Optional[int]]] = [[None] * c for _ in range(c)]
    best_dist: List[List[float]] = [[10**30] * c for _ in range(c)]

    for i in range(c):
        dist, parent = dijkstra_all(inst, adj, comp_vertices[i])
        parents.append(parent)
        dist_lists.append(dist)

        for j in range(c):
            if i == j:
                best_dist[i][j] = 0.0
                best_target[i][j] = None
                continue

            # melhor terminal dentro da componente j
            t_best = None
            d_best = 10**30
            for v in comp_vertices[j]:
                if dist[v] < d_best:
                    d_best = dist[v]
                    t_best = v

            best_dist[i][j] = d_best
            best_target[i][j] = t_best

    # matriz simétrica de pesos entre componentes
    weights = [[0.0] * c for _ in range(c)]
    for i in range(c):
        for j in range(c):
            if i == j:
                weights[i][j] = 0.0
            else:
                weights[i][j] = min(best_dist[i][j], best_dist[j][i])

    # MST no nível de componentes
    mst_edges = prim_mst_components(weights)

    # expandir cada aresta da MST em caminho real
    for a, b in mst_edges:
        # escolhe direção que tem target válido (sempre deve ter)
        ta = best_target[a][b]
        tb = best_target[b][a]

        if ta is not None and best_dist[a][b] <= best_dist[b][a]:
            path_edges = reconstruct_path_edges(parents[a], ta)
        elif tb is not None:
            path_edges = reconstruct_path_edges(parents[b], tb)
        else:
            raise RuntimeError("R3: não encontrou target para reconstruir (inesperado).")

        if not path_edges:
            raise RuntimeError("R3: caminho reconstruído vazio (inesperado).")

        for e in path_edges:
            if e not in global_set:
                global_set.add(e)
                global_edges.append(e)

    final_edges = list(local_edges) + list(global_edges)
    cost = sum(wlookup[(u, v)] for (u, v) in final_edges)
    return Solution(instance_name=inst.name, cost=cost, edges=final_edges)
