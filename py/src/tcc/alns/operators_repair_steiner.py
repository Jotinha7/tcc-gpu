from __future__ import annotations

import random
from typing import Dict, List, Tuple

from tcc.instance import Instance
from tcc.solution import Solution, TreeEdge

from .partial_state import PartialState
from .operators_repair import repair_r3_mst_components


def _norm_edge(u: int, v: int) -> TreeEdge:
    return (u, v) if u < v else (v, u)


def _weight_map(instance: Instance) -> Dict[Tuple[int, int], float]:
    """
    Cache simples de pesos para lookup O(1).
    """
    wm = getattr(instance, "_wm_cache", None)
    if wm is not None:
        return wm

    wm2: Dict[Tuple[int, int], float] = {}
    for (u, v, w) in instance.edges:
        a, b = (u, v) if u < v else (v, u)
        wm2[(a, b)] = float(w)

    setattr(instance, "_wm_cache", wm2)
    return wm2


def _cost(instance: Instance, edges: List[TreeEdge]) -> float:
    wm = _weight_map(instance)
    total = 0.0
    for (u, v) in edges:
        a, b = (u, v) if u < v else (v, u)
        total += wm[(a, b)]
    return total


def repair_r4_steiner_hub(instance: Instance, ps: PartialState, rng: random.Random, max_candidates: int = 25) -> Solution:
    """
    R4 (Steiner Hub):
    - Se temos C componentes de clusters, escolhemos 1 vértice Steiner s
    - Ligamos s a 1 terminal “mais perto” de cada componente
    - Como s é novo, adicionamos C arestas e 1 vértice => volta a ser árvore (sem ciclo)

    Observação: se já estiver 1 componente, só retorna a solução reconstruída.
    """
    # se já está tudo conectado no nível de clusters, não inventa coisa
    if len(ps.components) <= 1:
        edges = [_norm_edge(*e) for e in (ps.local_edges + ps.global_edges_remaining)]
        return Solution(instance_name=instance.name, cost=_cost(instance, edges), edges=edges)

    used_vertices = set()
    for (u, v) in (ps.local_edges + ps.global_edges_remaining):
        used_vertices.add(u)
        used_vertices.add(v)

    # candidatos Steiner = vertices não-requeridos (-1) e ainda não usados
    steiners = [v for v in range(instance.n) if instance.cluster_of[v] == -1 and v not in used_vertices]
    if not steiners:
        # fallback: reconecta “do jeito antigo”
        return repair_r3_mst_components(instance, ps, rng)

    cand = rng.sample(steiners, min(max_candidates, len(steiners)))
    wm = _weight_map(instance)

    best_s = None
    best_sum = float("inf")
    best_attach: List[int] = []

    # pré-lista: terminais por componente
    comp_terminals: List[List[int]] = []
    for comp in ps.components:
        terminals: List[int] = []
        for cid in comp:
            terminals.extend(instance.clusters[cid])
        comp_terminals.append(terminals)

    for s in cand:
        attach: List[int] = []
        total = 0.0
        for terminals in comp_terminals:
            # escolhe o terminal mais próximo de s
            best_t = None
            best_w = float("inf")
            for t in terminals:
                a, b = (s, t) if s < t else (t, s)
                w = wm[(a, b)]
                if w < best_w:
                    best_w = w
                    best_t = t
            attach.append(best_t)  # type: ignore
            total += best_w

        if total < best_sum:
            best_sum = total
            best_s = s
            best_attach = attach

    assert best_s is not None

    new_edges = [_norm_edge(best_s, t) for t in best_attach]
    edges = [_norm_edge(*e) for e in (ps.local_edges + ps.global_edges_remaining)] + new_edges

    return Solution(instance_name=instance.name, cost=_cost(instance, edges), edges=edges)
