from __future__ import annotations
import argparse
from pathlib import Path

from tcc.alns.minimal import run_alns_minimal
from tcc.tsplib_loader import load_tsplib_clusteiner
from tcc.verify import verify_solution
from tcc.solution import Solution

# Baseline da Semana 2 (está no exp/runner.py)
from exp.runner import solve_two_level_mst


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True, help="Caminho da instância .txt")
    ap.add_argument("--time", type=float, default=2.0)
    ap.add_argument("--iters", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    instance_path = Path(args.instance)
    instance_id = instance_path.stem

    repo_root = Path(__file__).resolve().parents[3]
    out_dir = repo_root / "experiments" / "results" / "alns_minimal_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"{instance_id}_seed{args.seed}.csv"

    inst = load_tsplib_clusteiner(instance_path)

    # build_initial: usa o baseline factível da Semana 2
    def build_initial(instance):
        cost, edges = solve_two_level_mst(instance)  # (float, List[Tuple[int,int]])
        return Solution(instance_name=instance.name, cost=cost, edges=edges)

    def cost_fn(sol: Solution) -> float:
        return float(sol.cost)

    def feasible_fn(instance, sol: Solution) -> bool:
        return bool(verify_solution(instance, sol).feasible)

    def num_edges_fn(sol: Solution) -> int:
        return len(sol.edges)

    best = run_alns_minimal(
        instance=inst,
        instance_id=instance_id,
        build_initial=build_initial,
        cost_fn=cost_fn,
        feasible_fn=feasible_fn,
        num_edges_fn=num_edges_fn,
        log_path=str(log_path),
        time_limit_s=args.time,
        max_iters=args.iters,
        seed=args.seed,
    )

    ok = verify_solution(inst, best).feasible
    print(f"[OK] log={log_path} best_cost={best.cost:.6f} feasible={ok}")


if __name__ == "__main__":
    main()
