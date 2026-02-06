from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import time
import csv

import typer

from tcc.solution import Solution
from tcc.verify import verify_solution
from tcc.tsplib_loader import load_tsplib_clusteiner
from exp.metrics import avg_cost, best_found, rpd, pi


app = typer.Typer(help="Runner de experimentos (Type1 Small)")

Edge = Tuple[int, int]


def _weight_lookup(inst) -> Dict[Tuple[int, int], float]:
    # cria map (u,v)->w para acesso rápido
    w = {}
    for u, v, c in inst.edges:
        w[(u, v)] = c
        w[(v, u)] = c
    return w


def _mst_prim(nodes: List[int], w) -> List[Edge]:
    """
    MST simples (Prim) no conjunto 'nodes', usando w(u,v).
    Retorna lista de arestas (u,v).
    """
    if len(nodes) <= 1:
        return []

    in_tree = set([nodes[0]])
    remaining = set(nodes[1:])
    edges: List[Edge] = []

    while remaining:
        best = None
        best_u = best_v = None
        for u in in_tree:
            for v in remaining:
                cost = w[(u, v)]
                if best is None or cost < best:
                    best = cost
                    best_u, best_v = u, v
        edges.append((best_u, best_v))
        in_tree.add(best_v)
        remaining.remove(best_v)

    return edges


def solve_two_level_mst(inst) -> Tuple[float, List[Edge]]:
    """
    Baseline factível (bem simples):
      1) MST dentro de cada cluster (somente nos terminais daquele cluster)
      2) Conecta clusters com MST entre clusters usando a menor aresta entre clusters

    Resultado: árvore sobre os terminais (cobre R e mantém clusters disjuntos).
    """
    w = _weight_lookup(inst)

    # 1) local trees: MST em cada cluster
    all_edges: List[Edge] = []
    for ck in inst.clusters:
        all_edges.extend(_mst_prim(ck, w))

    # 2) MST entre clusters (nós = clusters)
    h = len(inst.clusters)
    if h <= 1:
        cost = sum(w[(u, v)] for (u, v) in all_edges)
        return cost, all_edges

    # peso entre clusters i,j = min_{u in Ci, v in Cj} w(u,v)
    best_pair: Dict[Tuple[int, int], Tuple[float, int, int]] = {}
    for i in range(h):
        for j in range(i + 1, h):
            best = None
            bu = bv = None
            for u in inst.clusters[i]:
                for v in inst.clusters[j]:
                    c = w[(u, v)]
                    if best is None or c < best:
                        best = c
                        bu, bv = u, v
            best_pair[(i, j)] = (best, bu, bv)

    # Prim em clusters
    in_tree = {0}
    remaining = set(range(1, h))
    while remaining:
        best = None
        best_i = best_j = None
        best_u = best_v = None
        for i in in_tree:
            for j in remaining:
                a, b = (i, j) if i < j else (j, i)
                c, u, v = best_pair[(a, b)]
                if best is None or c < best:
                    best = c
                    best_i, best_j = i, j
                    best_u, best_v = u, v

        # adiciona aresta real entre vértices terminais que liga os clusters
        all_edges.append((best_u, best_v))
        in_tree.add(best_j)
        remaining.remove(best_j)

    cost = sum(w[(u, v)] for (u, v) in all_edges)
    return cost, all_edges


def read_bks_csv(path: Path) -> Dict[str, Optional[float]]:
    if not path.exists():
        return {}
    out: Dict[str, Optional[float]] = {}
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            inst = row["instance"].strip()
            val = row["bks"].strip()
            out[inst] = float(val) if val else None
    return out


def write_bks_csv(path: Path, data: Dict[str, Optional[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["instance", "bks"])
        writer.writeheader()
        for inst in sorted(data.keys()):
            bks = data[inst]
            writer.writerow({"instance": inst, "bks": "" if bks is None else f"{bks:.6f}"})


@app.command()
def run(
    data_dir: Path = typer.Option(..., help="Ex: data/raw/EUC_Type1_Small"),
    out_csv: Path = typer.Option(..., help="Ex: data/processed/type1_small_results.csv"),
    bks_csv: Path = typer.Option(Path("exp/bks_type1_small.csv"), help="CSV com best-known solutions"),
    runs: int = typer.Option(1, help="Número de execuções por instância"),
    limit: int = typer.Option(1, help="Quantas instâncias rodar (1 pra testar hoje)"),
):
    """
    Roda o baseline em algumas instâncias e gera CSV com AVG/BF/RPD/PI.
    """
    paths = sorted(data_dir.rglob("*.txt"))[:limit]
    if not paths:
        raise typer.BadParameter(f"Nenhuma instância .txt em {data_dir}")

    bks = read_bks_csv(bks_csv)

    rows = []
    for p in paths:
        inst = load_tsplib_clusteiner(p)

        costs: List[float] = []
        times: List[float] = []

        for _ in range(runs):
            t0 = time.perf_counter()
            cost, edges = solve_two_level_mst(inst)
            t1 = time.perf_counter()

            # verificação estrutural
            sol = Solution(instance_name=inst.name, cost=cost, edges=edges)
            res = verify_solution(inst, sol)
            if not res.feasible:
                raise RuntimeError(f"Solução infeasível em {inst.name}: {res.violations}")

            costs.append(cost)
            times.append(t1 - t0)

        avg = avg_cost(costs)
        bf = best_found(costs)

        # BKS: se não existe, usa o melhor que achamos hoje; se existe, atualiza se melhorou
        cur_bks = bks.get(inst.name, None)
        if cur_bks is None or bf < cur_bks:
            cur_bks = bf
        bks[inst.name] = cur_bks

        rpd_val = rpd(avg, cur_bks)

        # PI precisa de um algoritmo B de referência; hoje temos só 1 -> PI = 0.0
        pi_val = 0.0

        rows.append({
            "instance": inst.name,
            "AVG": avg,
            "BF": bf,
            "BKS": cur_bks,
            "RPD": rpd_val,
            "PI": pi_val,
            "runs": runs,
            "time_avg_s": sum(times)/len(times),
        })

        typer.echo(f"{inst.name}: AVG={avg:.2f} BF={bf:.2f} RPD={rpd_val:.3f}%")

    # salva BKS atualizado
    write_bks_csv(bks_csv, bks)

    # salva resultados
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        cols = ["instance", "AVG", "BF", "BKS", "RPD", "PI", "runs", "time_avg_s"]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    typer.echo(f"\nOK! Resultados em: {out_csv}")
    typer.echo(f"BKS atualizado em: {bks_csv}")

if __name__ == "__main__":
    app()
