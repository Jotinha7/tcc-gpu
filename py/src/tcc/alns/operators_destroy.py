from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import random

from tcc.instance import Instance
from tcc.solution import Solution, TreeEdge

from .partial_state import PartialState


def _norm_edge(u: int, v: int) -> TreeEdge:
    return (u, v) if u < v else (v, u)


def split_local_global_edges(instance: Instance, edges: List[TreeEdge]) -> Tuple[List[TreeEdge], List[TreeEdge]]:
    """
    Definição usada a partir daqui:

    - LOCAL: aresta entre dois terminais do MESMO cluster.
    - GLOBAL: todo o resto (inclui:
        * terminal-terminal de clusters diferentes
        * steiner-terminal
        * steiner-steiner (se existir)
      )

    Isso é necessário porque, se o ALNS começar a usar Steiner para “colar” componentes,
    essas arestas precisam contar como parte da conectividade (global).
    """
    local: List[TreeEdge] = []
    global_: List[TreeEdge] = []

    for (u, v) in edges:
        cu = instance.cluster_of[u]
        cv = instance.cluster_of[v]

        if cu != -1 and cv != -1 and cu == cv:
            local.append(_norm_edge(u, v))
        else:
            global_.append(_norm_edge(u, v))

    return local, global_


class DSU:
    def __init__(self, n: int) -> None:
        self.p = list(range(n))
        self.r = [0] * n

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.r[ra] < self.r[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        if self.r[ra] == self.r[rb]:
            self.r[ra] += 1


def compute_cluster_components(instance: Instance, global_edges: List[TreeEdge]) -> List[List[int]]:
    """
    Componentes no nível de CLUSTERS, mas levando em conta caminhos que passam por Steiner.

    Ideia:
    - DSU em todos os vértices
    - Primeiro “contrai” cada cluster: une todos os terminais do mesmo cluster no DSU
      (assim o cluster vira 1 supernó)
    - Depois une endpoints de todas as arestas globais (incluindo steiner-terminal)
    - No final, clusters com o mesmo root no DSU estão no mesmo componente.
    """
    dsu = DSU(instance.n)

    # contrai cada cluster
    for cid, terminals in enumerate(instance.clusters):
        if not terminals:
            continue
        t0 = terminals[0]
        for t in terminals[1:]:
            dsu.union(t0, t)

    # une arestas globais (inclui Steiner)
    for (u, v) in global_edges:
        dsu.union(u, v)

    root_to_clusters = {}
    for cid, terminals in enumerate(instance.clusters):
        t0 = terminals[0]
        r = dsu.find(t0)
        root_to_clusters.setdefault(r, []).append(cid)

    return list(root_to_clusters.values())

def _build_cluster_to_component(num_clusters: int, components: list[list[int]]) -> list[int]:
    out = [-1] * num_clusters
    for comp_id, comp in enumerate(components):
        for c in comp:
            out[c] = comp_id
    return out


def destroy_d1_remove_k_global_edges(instance, solution, rng: random.Random, k: int = 2) -> PartialState:
    local_edges, global_edges = split_local_global_edges(instance, solution.edges)

    if len(global_edges) == 0:
        components = compute_cluster_components(instance, global_edges)
        cluster_to_component = _build_cluster_to_component(len(instance.clusters), components)
        return PartialState(
            base_solution=solution,
            local_edges=local_edges,
            global_edges_remaining=global_edges,
            global_edges_removed=[],
            components=components,
            cluster_to_component=cluster_to_component,
            destroyed_cluster=None,
            meta={"destroy_op": "D1_remove_k_global_edges", "k": 0},
        )

    kk = min(k, len(global_edges))
    removed = rng.sample(global_edges, kk)
    removed_set = set(removed)
    remaining = [e for e in global_edges if e not in removed_set]

    components = compute_cluster_components(instance, remaining)
    cluster_to_component = _build_cluster_to_component(len(instance.clusters), components)

    return PartialState(
        base_solution=solution,
        local_edges=local_edges,
        global_edges_remaining=remaining,
        global_edges_removed=removed,
        components=components,
        cluster_to_component=cluster_to_component,
        destroyed_cluster=None,
        meta={"destroy_op": "D1_remove_k_global_edges", "k": kk},
    )


def destroy_d2_disconnect_cluster(instance, solution, rng: random.Random) -> PartialState:
    local_edges, global_edges = split_local_global_edges(instance, solution.edges)

    num_clusters = len(instance.clusters)
    c = rng.randrange(num_clusters)
    terminals = set(instance.clusters[c])

    incident = [e for e in global_edges if (e[0] in terminals) or (e[1] in terminals)]

    if not incident:
        components = compute_cluster_components(instance, global_edges)
        cluster_to_component = _build_cluster_to_component(num_clusters, components)
        return PartialState(
            base_solution=solution,
            local_edges=local_edges,
            global_edges_remaining=global_edges,
            global_edges_removed=[],
            components=components,
            cluster_to_component=cluster_to_component,
            destroyed_cluster=c,
            meta={"destroy_op": "D2_disconnect_cluster", "note": "no incident global edge"},
        )

    removed_edge = rng.choice(incident)
    remaining = [e for e in global_edges if e != removed_edge]

    components = compute_cluster_components(instance, remaining)
    cluster_to_component = _build_cluster_to_component(num_clusters, components)

    return PartialState(
        base_solution=solution,
        local_edges=local_edges,
        global_edges_remaining=remaining,
        global_edges_removed=[removed_edge],
        components=components,
        cluster_to_component=cluster_to_component,
        destroyed_cluster=c,
        meta={"destroy_op": "D2_disconnect_cluster"},
    )


destroy_remove_k_global_edges = destroy_d1_remove_k_global_edges
destroy_disconnect_cluster = destroy_d2_disconnect_cluster
