from __future__ import annotations

import argparse
import random
from pathlib import Path

from tcc.tsplib_loader import load_tsplib_clusteiner
from tcc.solution import Solution
from tcc.verify import verify_solution

from tcc.alns.operators_destroy import (
    destroy_remove_k_global_edges,
    destroy_disconnect_cluster,
    split_local_global_edges,
)
from tcc.alns.operators_repair import repair_r3_mst_components

from exp.runner import solve_two_level_mst


def _norm(u: int, v: int):
    return (u, v) if u < v else (v, u)


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

    # sanity baseline
    vr0 = verify_solution(inst, base_sol)
    if not vr0.feasible:
        raise RuntimeError(f"[FAIL] Baseline inviável! Violations: {vr0.violations[:10]}")

    local0, global0 = split_local_global_edges(inst, base_sol.edges)
    local0_set = set(_norm(u, v) for (u, v) in local0)

    print(f"\n[INSTANCE] {inst.name}")
    print(f"[BASELINE] cost={base_cost:.6f} local={len(local0)} global={len(global0)} clusters={len(inst.clusters)}")

    def check_solution(sol: Solution, label: str):
        vr = verify_solution(inst, sol)
        if not vr.feasible:
            raise RuntimeError(f"[FAIL] {label}: inviável. Violations: {vr.violations[:5]}")

        # local preservado
        local_now, _ = split_local_global_edges(inst, sol.edges)
        local_now_set = set(_norm(u, v) for (u, v) in local_now)
        if local_now_set != local0_set:
            raise RuntimeError(f"[FAIL] {label}: local_edges mudou (não era pra mudar).")

    best1 = base_cost
    best2 = base_cost

    for t in range(args.trials):
        rng = random.Random(args.seed + t)

        ps1 = destroy_remove_k_global_edges(inst, base_sol, rng, k=args.k)
        sol1 = repair_r3_mst_components(inst, ps1, rng)
        check_solution(sol1, f"D1+R3 trial={t}")
        best1 = min(best1, sol1.cost)

        ps2 = destroy_disconnect_cluster(inst, base_sol, rng)
        sol2 = repair_r3_mst_components(inst, ps2, rng)
        check_solution(sol2, f"D2+R3 trial={t}")
        best2 = min(best2, sol2.cost)

        if args.verbose and t < 10:
            print(f"[{t:03d}] D1 comps={ps1.num_components} -> cost={sol1.cost:.3f} | "
                  f"D2 comps={ps2.num_components} -> cost={sol2.cost:.3f}")

    print("\n[SUMMARY]")
    print(f"D1+R3 best_cost={best1:.6f}  (delta={base_cost - best1:.6f})")
    print(f"D2+R3 best_cost={best2:.6f}  (delta={base_cost - best2:.6f})")
    print("[OK] R3 repair passed (feasible + local unchanged)\n")


if __name__ == "__main__":
    main()
