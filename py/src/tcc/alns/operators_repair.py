from __future__ import annotations

import heapq
import random
from typing import Dict, List, Tuple, Optional

from tcc.instance import Instance
from tcc.solution import Solution, TreeEdge

from .partial_state import PartialState
from .operators_destroy import compute_cluster_components  # reaproveita DSU


def _norm_edge(e: TreeEdge) -> TreeEdge:
    u, v = e
    return (u, v) if u < v else (v, u)


def build_weight_lookup(inst: Instance) -> Dict[Tuple[int, int], float]:
    """Mapa rápido w(u,v). Colocamos as duas direções pra facilitar."""
    w: Dict[Tuple[int, int], float] = {}
    for u, v, c in inst.edges:
        w[(u, v)] = float(c)
        w[(v, u)] = float(c)
    return w


def build_adj(inst: Instance) -> List[List[Tuple[int, float]]]:
    """Adjacência (lista) para Dijkstra."""
    adj: List[List[Tuple[int, float]]] = [[] for _ in range(inst.n)]
    for u, v, c in inst.edges:
        cc = float(c)
        adj[u].append((v, cc))
        adj[v].append((u, cc))
    return adj


def multi_source_dijkstra_to_other_component(
    inst: Instance,
    adj: List[List[Tuple[int, float]]],
    sources: List[int],
    cluster_to_component: List[int],
    base_component_id: int,
) -> Tuple[Optional[int], List[int]]:
    """
    Dijkstra multi-source:
      - queremos chegar no primeiro TERMINAL que esteja em outra componente (cluster diferente da base)
    Retorna:
      (target_vertex, parent_array)
    Se não achar, retorna (None, parent).
    """
    INF = 10**30
    n = inst.n
    dist = [INF] * n
    parent = [-1] * n

    pq: List[Tuple[float, int]] = []

    # inicializa fontes
    for s in sources:
        dist[s] = 0.0
        parent[s] = -1
        heapq.heappush(pq, (0.0, s))

    while pq:
        d, u = heapq.heappop(pq)
        if d != dist[u]:
            continue

        cu = inst.cluster_of[u]
        # só aceitamos como alvo um TERMINAL (cu != -1) que esteja em outra componente
        if cu != -1 and cluster_to_component[cu] != base_component_id:
            return u, parent

        for v, w_uv in adj[u]:
            nd = d + w_uv
            if nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(pq, (nd, v))

    return None, parent


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
    # estruturas auxiliares
    adj = build_adj(inst)
    w = build_weight_lookup(inst)

    local_edges = [_norm_edge(e) for e in ps.local_edges]
    global_edges = [_norm_edge(e) for e in ps.global_edges_remaining]

    # set pra evitar duplicar arestas
    global_set = set(global_edges)

    # loop até ficar 1 componente
    while True:
        components, cluster_to_component = compute_cluster_components(inst, global_edges)
        if len(components) <= 1:
            break

        # escolher componente base:
        # se o destroy foi D2 e marcou destroyed_cluster, usamos a componente dele (intuitivo)
        base_component_id = 0
        if ps.destroyed_cluster is not None:
            base_component_id = cluster_to_component[ps.destroyed_cluster]
        else:
            # opcional: aleatorizar um pouco
            base_component_id = rng.randrange(len(components))

        base_clusters = components[base_component_id]

        # fontes = todos os terminais desses clusters
        sources: List[int] = []
        for ck in base_clusters:
            sources.extend(inst.clusters[ck])

        # roda dijkstra até achar um terminal em outra componente
        target, parent = multi_source_dijkstra_to_other_component(
            inst=inst,
            adj=adj,
            sources=sources,
            cluster_to_component=cluster_to_component,
            base_component_id=base_component_id,
        )

        if target is None:
            # não deveria acontecer no grafo completo, mas fica como proteção
            raise RuntimeError("Dijkstra não encontrou conexão para outra componente (inesperado).")

        path_edges = reconstruct_path_edges(parent, target)
        if not path_edges:
            # também não deveria, mas proteção
            raise RuntimeError("Caminho reconstruído vazio (inesperado).")

        # adiciona arestas do caminho ao global (evita duplicar)
        for e in path_edges:
            if e not in global_set:
                global_set.add(e)
                global_edges.append(e)

        # continua loop (recomputa componentes de novo no topo)

    # monta solução final
    final_edges = list(local_edges) + list(global_edges)

    # custo = soma w(u,v) em todas as arestas
    cost = 0.0
    for (u, v) in final_edges:
        cost += w[(u, v)]

    return Solution(instance_name=inst.name, cost=cost, edges=final_edges)
