from __future__ import annotations

import argparse
import random
from pathlib import Path

from tcc.solution import Solution
from tcc.tsplib_loader import load_tsplib_clusteiner
from tcc.alns.operators_destroy import (
    split_local_global_edges,
    destroy_remove_k_global_edges,
    destroy_disconnect_cluster,
)

from exp.runner import solve_two_level_mst


def _norm(u: int, v: int):
    return (u, v) if u < v else (v, u)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True, help="Ex: ../data/raw/EUC_Type1_Small/5eil51.txt")
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    inst_path = Path(args.instance)
    inst = load_tsplib_clusteiner(inst_path)

    cost, edges = solve_two_level_mst(inst)
    base_sol = Solution(instance_name=inst.name, cost=cost, edges=edges)

    local0, global0 = split_local_global_edges(inst, base_sol.edges)
    local0_set = set(_norm(u, v) for (u, v) in local0)
    global0_set = set(_norm(u, v) for (u, v) in global0)

    if args.verbose:
        print(f"[BASE] local={len(local0)} global={len(global0)} clusters={len(inst.clusters)}")

    def check_partial(ps, name: str):
        # 1) local não muda
        local_set = set(_norm(u, v) for (u, v) in ps.local_edges)
        if local_set != local0_set:
            raise RuntimeError(f"[FAIL] {name}: local_edges mudou!")

        # 2) global restante + removida == global original
        rem_set = set(_norm(u, v) for (u, v) in ps.global_edges_remaining)
        del_set = set(_norm(u, v) for (u, v) in ps.global_edges_removed)

        if (rem_set | del_set) != global0_set:
            raise RuntimeError(f"[FAIL] {name}: união(remaining,removed) != global original")

        if (rem_set & del_set):
            raise RuntimeError(f"[FAIL] {name}: remaining e removed têm interseção")

        # 3) tem que criar >=2 componentes (quando dá pra destruir)
        if len(inst.clusters) > 1 and len(global0) > 0:
            if ps.num_components < 2:
                raise RuntimeError(f"[FAIL] {name}: num_components={ps.num_components} (esperado >=2)")

    # rodar trials
    comps_d1 = []
    comps_d2 = []

    for t in range(args.trials):
        rng = random.Random(args.seed + t)

        ps1 = destroy_remove_k_global_edges(inst, base_sol, rng, k=args.k)
        check_partial(ps1, "D1")
        comps_d1.append(ps1.num_components)

        ps2 = destroy_disconnect_cluster(inst, base_sol, rng)
        check_partial(ps2, "D2")
        comps_d2.append(ps2.num_components)

        if args.verbose:
            print(f"[{t:03d}] D1 comps={ps1.num_components} (k={ps1.meta.get('k')}) | "
                  f"D2 comps={ps2.num_components} (cluster={ps2.destroyed_cluster})")

    print("[OK] destroy operators passed")
    print(f"D1 avg_components={sum(comps_d1)/len(comps_d1):.2f} (k={args.k})")
    print(f"D2 avg_components={sum(comps_d2)/len(comps_d2):.2f}")


if __name__ == "__main__":
    main()
