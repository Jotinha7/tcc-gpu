from __future__ import annotations

import argparse
import random
import csv
from pathlib import Path

from tcc.tsplib_loader import load_tsplib_clusteiner
from tcc.solution import Solution
from tcc.verify import verify_solution

from tcc.alns.operators_destroy import (
    destroy_remove_k_global_edges,
    destroy_disconnect_cluster,
    split_local_global_edges,
)
from tcc.alns.operators_repair import repair_r1_dijkstra

from exp.runner import solve_two_level_mst
from exp.metrics import avg_cost, best_found, rpd as rpd_metric


def _norm(u: int, v: int):
    return (u, v) if u < v else (v, u)


def read_bks_for_instance(inst_name: str) -> float | None:
    """
    Lê o BKS (best-known solution) da tabela py/src/exp/bks_type1_small.csv.
    Retorna None se não encontrar.
    """
    bks_path = Path(__file__).resolve().parent / "bks_type1_small.csv"
    if not bks_path.exists():
        return None

    with bks_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["instance"].strip() == inst_name.strip():
                val = row["bks"].strip()
                return float(val) if val else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    inst_path = Path(args.instance)
    inst = load_tsplib_clusteiner(inst_path)

    # baseline
    base_cost, base_edges = solve_two_level_mst(inst)
    base_sol = Solution(instance_name=inst.name, cost=base_cost, edges=base_edges)

    # BKS (pra calcular RPD)
    bks = read_bks_for_instance(inst.name)

    # baseline local/global para checar "local não muda"
    local0, global0 = split_local_global_edges(inst, base_sol.edges)
    local0_set = set(_norm(u, v) for (u, v) in local0)

    # sanity baseline
    vr0 = verify_solution(inst, base_sol)
    if not vr0.feasible:
        raise RuntimeError(f"[FAIL] Baseline inviável! Violations: {vr0.violations[:10]}")

    print(f"\n[INSTANCE] {inst.name}")
    print(f"[BASELINE] cost={base_cost:.6f}  local={len(local0)}  global={len(global0)}  clusters={len(inst.clusters)}")

    if bks is not None:
        print(f"[BKS] {bks:.6f}  |  RPD_baseline={rpd_metric(base_cost, bks):.4f}%")
    else:
        print("[BKS] (não encontrado para esta instância)")

    def check_solution(sol: Solution, label: str):
        vr = verify_solution(inst, sol)
        if not vr.feasible:
            raise RuntimeError(f"[FAIL] {label}: solução inviável. Violations: {vr.violations[:5]}")

        # local preservado
        local_now, _ = split_local_global_edges(inst, sol.edges)
        local_now_set = set(_norm(u, v) for (u, v) in local_now)
        if local_now_set != local0_set:
            raise RuntimeError(f"[FAIL] {label}: local_edges mudou (não era pra mudar).")

    costs_d1 = []
    costs_d2 = []
    improved_d1 = 0
    improved_d2 = 0

    for t in range(args.trials):
        rng = random.Random(args.seed + t)

        # D1 -> R1
        ps1 = destroy_remove_k_global_edges(inst, base_sol, rng, k=args.k)
        sol1 = repair_r1_dijkstra(inst, ps1, rng)
        check_solution(sol1, f"D1+R1 trial={t}")
        costs_d1.append(sol1.cost)
        if sol1.cost < base_cost:
            improved_d1 += 1

        # D2 -> R1
        ps2 = destroy_disconnect_cluster(inst, base_sol, rng)
        sol2 = repair_r1_dijkstra(inst, ps2, rng)
        check_solution(sol2, f"D2+R1 trial={t}")
        costs_d2.append(sol2.cost)
        if sol2.cost < base_cost:
            improved_d2 += 1

        if args.verbose and t < 10:
            print(
                f"[{t:03d}] D1 comps={ps1.num_components} cost={sol1.cost:.3f} | "
                f"D2 comps={ps2.num_components} cost={sol2.cost:.3f}"
            )

    # resumo
    avg1 = avg_cost(costs_d1)
    bf1 = best_found(costs_d1)

    avg2 = avg_cost(costs_d2)
    bf2 = best_found(costs_d2)

    def pi(best: float, base: float) -> float:
        # Improvement % do best sobre o baseline
        return (base - best) / base * 100.0 if base > 0 else 0.0

    print("\n[SUMMARY] (quanto melhor, menor custo)")
    print(f"D1+R1: avg={avg1:.6f}  best={bf1:.6f}  PI_best={pi(bf1, base_cost):.3f}%  improved_trials={improved_d1}/{args.trials}")
    if bks is not None:
        print(f"       RPD_avg={rpd_metric(avg1, bks):.4f}%  RPD_best={rpd_metric(bf1, bks):.4f}%")

    print(f"D2+R1: avg={avg2:.6f}  best={bf2:.6f}  PI_best={pi(bf2, base_cost):.3f}%  improved_trials={improved_d2}/{args.trials}")
    if bks is not None:
        print(f"       RPD_avg={rpd_metric(avg2, bks):.4f}%  RPD_best={rpd_metric(bf2, bks):.4f}%")

    print("\n[OK] R1 repair passed + printed improvement stats\n")


if __name__ == "__main__":
    main()
