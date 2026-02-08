from __future__ import annotations

import random
from typing import Dict, List, Tuple

from tcc.instance import Instance
from tcc.solution import Solution, TreeEdge

from .partial_state import PartialState


def _norm_edge(e: TreeEdge) -> TreeEdge:
    u, v = e
    return (u, v) if u < v else (v, u)


def split_local_global_edges(inst: Instance, edges: List[TreeEdge]) -> Tuple[List[TreeEdge], List[TreeEdge]]:
    """
    Separa arestas em:
      - local: endpoints no MESMO cluster, ou envolvendo Steiner (-1)
      - global: endpoints em clusters DIFERENTES (ambos >= 0)

    Só vamos remover arestas globais.
    """
    local_edges: List[TreeEdge] = []
    global_edges: List[TreeEdge] = []

    for (u, v) in edges:
        u, v = _norm_edge((u, v))
        cu = inst.cluster_of[u]
        cv = inst.cluster_of[v]

        # global só se ambos são terminais (cluster >=0) e clusters diferentes
        if cu != -1 and cv != -1 and cu != cv:
            global_edges.append((u, v))
        else:
            local_edges.append((u, v))

    return local_edges, global_edges


class _DSU:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.sz = [1] * n

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.sz[ra] < self.sz[rb]:
            ra, rb = rb, ra
        self.p[rb] = ra
        self.sz[ra] += self.sz[rb]


def compute_cluster_components(inst: Instance, global_edges_remaining: List[TreeEdge]) -> Tuple[List[List[int]], List[int]]:
    """
    Calcula componentes conectados no nível de clusters, usando SOMENTE arestas globais restantes.

    Retorna:
      components: List[List[cluster_id]]
      cluster_to_component: List[int] com tamanho h
    """
    h = len(inst.clusters)
    if h == 0:
        return [], []

    dsu = _DSU(h)

    for (u, v) in global_edges_remaining:
        cu = inst.cluster_of[u]
        cv = inst.cluster_of[v]
        if cu == -1 or cv == -1 or cu == cv:
            continue
        dsu.union(cu, cv)

    groups: Dict[int, List[int]] = {}
    for k in range(h):
        r = dsu.find(k)
        groups.setdefault(r, []).append(k)

    # ordenação estável
    components = []
    for comp in groups.values():
        comp.sort()
        components.append(comp)
    components.sort(key=lambda comp: comp[0])

    cluster_to_component = [-1] * h
    for cid, comp in enumerate(components):
        for k in comp:
            cluster_to_component[k] = cid

    return components, cluster_to_component


# -------------------------
# DESTROY OPERATORS (Dia 2)
# -------------------------

def destroy_remove_k_global_edges(
    inst: Instance,
    solution: Solution,
    rng: random.Random,
    k: int = 2,
) -> PartialState:
    """
    D1: remove k arestas GLOBAIS aleatórias.
    """
    local_edges, global_edges = split_local_global_edges(inst, solution.edges)

    if not global_edges:
        comps, c2c = compute_cluster_components(inst, [])
        return PartialState(
            base_solution=solution,
            local_edges=local_edges,
            global_edges_remaining=[],
            global_edges_removed=[],
            components=comps,
            cluster_to_component=c2c,
            meta={"op": "D1_remove_k_global_edges", "k": 0},
        )

    k_eff = min(k, len(global_edges))
    removed = rng.sample(global_edges, k_eff)
    removed_set = set(removed)

    remaining = [e for e in global_edges if e not in removed_set]

    comps, c2c = compute_cluster_components(inst, remaining)
    return PartialState(
        base_solution=solution,
        local_edges=local_edges,
        global_edges_remaining=remaining,
        global_edges_removed=removed,
        components=comps,
        cluster_to_component=c2c,
        meta={"op": "D1_remove_k_global_edges", "k": k_eff},
    )


def destroy_disconnect_cluster(
    inst: Instance,
    solution: Solution,
    rng: random.Random,
) -> PartialState:
    """
    D2: escolhe um cluster c e remove 1 aresta global incidente a ele.
    """
    local_edges, global_edges = split_local_global_edges(inst, solution.edges)
    h = len(inst.clusters)

    if h <= 1 or not global_edges:
        comps, c2c = compute_cluster_components(inst, global_edges)
        return PartialState(
            base_solution=solution,
            local_edges=local_edges,
            global_edges_remaining=global_edges,
            global_edges_removed=[],
            components=comps,
            cluster_to_component=c2c,
            destroyed_cluster=None,
            meta={"op": "D2_disconnect_cluster", "removed": 0},
        )

    # tenta achar um cluster com pelo menos 1 aresta incidente
    clusters = list(range(h))
    rng.shuffle(clusters)

    chosen_cluster = None
    incident: List[TreeEdge] = []
    for c in clusters:
        incident = []
        for (u, v) in global_edges:
            cu = inst.cluster_of[u]
            cv = inst.cluster_of[v]
            if cu == c or cv == c:
                incident.append((u, v))
        if incident:
            chosen_cluster = c
            break

    if chosen_cluster is None:
        # não achou nada (bem improvável se global_edges existe)
        comps, c2c = compute_cluster_components(inst, global_edges)
        return PartialState(
            base_solution=solution,
            local_edges=local_edges,
            global_edges_remaining=global_edges,
            global_edges_removed=[],
            components=comps,
            cluster_to_component=c2c,
            destroyed_cluster=None,
            meta={"op": "D2_disconnect_cluster", "removed": 0},
        )

    removed_edge = rng.choice(incident)
    removed_set = {removed_edge}
    remaining = [e for e in global_edges if e not in removed_set]

    comps, c2c = compute_cluster_components(inst, remaining)
    return PartialState(
        base_solution=solution,
        local_edges=local_edges,
        global_edges_remaining=remaining,
        global_edges_removed=[removed_edge],
        components=comps,
        cluster_to_component=c2c,
        destroyed_cluster=chosen_cluster,
        meta={"op": "D2_disconnect_cluster", "removed": 1},
    )
