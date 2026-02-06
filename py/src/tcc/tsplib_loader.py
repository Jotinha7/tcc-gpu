from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional
import math

from .instance import Instance


def _tsplib_euc_2d(a: tuple[float, float], b: tuple[float, float]) -> float:
    # TSPLIB EUC_2D costuma usar arredondamento para inteiro:
    # dist = int(sqrt(dx^2+dy^2) + 0.5)
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return float(int(math.sqrt(dx * dx + dy * dy) + 0.5))


def load_tsplib_clusteiner(path: Path) -> Instance:
    """
    Loader mínimo para instâncias estilo TSPLIB + GTSP_SET_SECTION:
      - NAME
      - DIMENSION
      - EDGE_WEIGHT_TYPE: EUC_2D (assumido)
      - NODE_COORD_SECTION
      - GTSP_SET_SECTION (clusters de terminais)
    """
    lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    lines = [ln for ln in lines if ln]

    name = path.stem
    n: Optional[int] = None
    edge_weight_type = None

    # parse header
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("NAME"):
            # "NAME : xxx" ou "NAME: xxx"
            parts = ln.split(":")
            if len(parts) >= 2:
                name = parts[1].strip()
        elif ln.startswith("DIMENSION"):
            parts = ln.split(":")
            n = int(parts[1].strip())
        elif ln.startswith("EDGE_WEIGHT_TYPE"):
            parts = ln.split(":")
            edge_weight_type = parts[1].strip()
        elif ln.startswith("NODE_COORD_SECTION") or ln.startswith("GTSP_SET_SECTION"):
            break
        i += 1

    if n is None:
        raise ValueError(f"{path}: DIMENSION não encontrado")

    # coordenadas (1-based no arquivo)
    coords: List[tuple[float, float]] = [(0.0, 0.0)] * n
    if "NODE_COORD_SECTION" in lines:
        # achar onde começa
        idx = lines.index("NODE_COORD_SECTION") + 1
        for _ in range(n):
            tokens = lines[idx].split()
            idx += 1
            if len(tokens) < 3:
                raise ValueError(f"{path}: linha de coordenada inválida")
            node_id = int(tokens[0]) - 1
            x = float(tokens[1])
            y = float(tokens[2])
            coords[node_id] = (x, y)

    # clusters (GTSP_SET_SECTION)
    clusters: List[List[int]] = []
    terminals_set = set()

    if "GTSP_SET_SECTION" not in lines:
        raise ValueError(f"{path}: GTSP_SET_SECTION não encontrado (loader mínimo só cobre esse caso)")

    idx = lines.index("GTSP_SET_SECTION") + 1
    while idx < len(lines):
        ln = lines[idx]
        idx += 1
        if ln.upper().startswith("EOF"):
            break
        toks = ln.split()
        if len(toks) < 3:
            continue
        # toks[0] = id do cluster (ignora)
        vs: List[int] = []
        for t in toks[1:]:
            if t == "-1":
                break
            v = int(t) - 1  # 0-based
            vs.append(v)
            terminals_set.add(v)
        if vs:
            clusters.append(vs)

    terminals = sorted(terminals_set)

    cluster_of = [-1] * n
    for k, ck in enumerate(clusters):
        for v in ck:
            cluster_of[v] = k

    # criar arestas do grafo completo usando distância euclidiana
    edges: List[Tuple[int, int, float]] = []
    for u in range(n):
        for v in range(u + 1, n):
            w = _tsplib_euc_2d(coords[u], coords[v])
            edges.append((u, v, w))

    inst = Instance(
        name=name,
        n=n,
        m=len(edges),
        edges=edges,
        terminals=terminals,
        clusters=clusters,
        cluster_of=cluster_of,
        is_euclidean=True,
    )
    inst.validate()
    return inst
