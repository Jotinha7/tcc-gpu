from __future__ import annotations

import argparse
import csv
from pathlib import Path

from tcc.alns import (
    run_alns_sa,
    destroy_remove_k_global_edges,
    destroy_disconnect_cluster,
    repair_r1_dijkstra,
    repair_r1_dijkstra_topL,
    repair_r3_mst_components,
    repair_r4_steiner_hub,
)
from tcc.tsplib_loader import load_tsplib_clusteiner
from tcc.verify import verify_solution
from tcc.solution import Solution

from exp.runner import solve_two_level_mst


def read_bks_for_instance(inst_name: str) -> float | None:
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--time", type=float, default=2.0)
    ap.add_argument("--iters", type=int, default=500)
    ap.add_argument("--seed", type=int, default=0)

    # SA
    ap.add_argument("--t0", type=float, default=None)
    ap.add_argument("--alpha", type=float, default=0.995)

    # D1
    ap.add_argument("--k", type=int, default=2)

    # Top-L
    ap.add_argument("--topL", type=int, default=5, help="Se >0, habilita R1_topL com L=topL")

    args = ap.parse_args()

    instance_path = Path(args.instance)
    instance_id = instance_path.stem

    repo_root = Path(__file__).resolve().parents[3]
    out_dir = repo_root / "experiments" / "results" / "week3_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"{instance_id}_seed{args.seed}.csv"

    inst = load_tsplib_clusteiner(instance_path)

    def build_initial(instance):
        cost, edges = solve_two_level_mst(instance)
        return Solution(instance_name=instance.name, cost=cost, edges=edges)

    def cost_fn(sol: Solution) -> float:
        return float(sol.cost)

    def feasible_fn(instance, sol: Solution) -> bool:
        return bool(verify_solution(instance, sol).feasible)

    def num_edges_fn(sol: Solution) -> int:
        return len(sol.edges)

    bks = read_bks_for_instance(inst.name)

    def D1(instance, sol, rng):
        return destroy_remove_k_global_edges(instance, sol, rng, k=args.k)

    def D2(instance, sol, rng):
        return destroy_disconnect_cluster(instance, sol, rng)

    destroys = [("D1_rm_k", D1), ("D2_disc_cluster", D2)]

    repairs = [("R1_dijkstra", repair_r1_dijkstra), 
               ("R3_comp_mst", repair_r3_mst_components),
               ("R4_steiner_hub", lambda inst, ps, rng: repair_r4_steiner_hub(inst, ps, rng, max_candidates=25)),
    ]
    if args.topL and args.topL > 0:
        def R1T(instance, partial, rng):
            return repair_r1_dijkstra_topL(instance, partial, rng, L=args.topL)
        repairs.insert(0, ("R1_topL", R1T))

    best = run_alns_sa(
        instance=inst,
        instance_id=instance_id,
        build_initial=build_initial,
        cost_fn=cost_fn,
        feasible_fn=feasible_fn,
        num_edges_fn=num_edges_fn,
        destroy_ops=destroys,
        repair_ops=repairs,
        log_path=str(log_path),
        bks_cost=bks,
        time_limit_s=args.time,
        max_iters=args.iters,
        seed=args.seed,
        t0=args.t0,
        alpha=args.alpha,
    )

    ok = verify_solution(inst, best).feasible
    print(f"[OK] log={log_path} best_cost={best.cost:.6f} feasible={ok} bks={bks}", flush=True)


if __name__ == "__main__":
    main()
