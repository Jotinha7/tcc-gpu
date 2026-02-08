from __future__ import annotations
from typing import Any, Callable

from .iterlog import IterationLogger

def rpd_percent(cost: float, best: float) -> float:
    # RPD = 100 * (cost - best) / best
    if best <= 0:
        return 0.0
    return 100.0 * (cost - best) / best

def run_alns_minimal(
    instance: Any,
    instance_id: str,
    build_initial: Callable[[Any], Any],             # retorna Solution do teu projeto
    cost_fn: Callable[[Any], float],                 # custo da Solution
    feasible_fn: Callable[[Any, Any], bool],         # (instance, solution) -> bool
    num_edges_fn: Callable[[Any], int],              # número de arestas (só pra log)
    log_path: str,
    time_limit_s: float = 2.0,
    max_iters: int = 200,
    seed: int = 0,
) -> Any:
    """
    Dia 01: ALNS esqueleto.
    - S0 = build_spmst_solution(instance)
    - candidate = current (ainda sem destroy/repair)
    - aceita sempre
    - loga tudo por iteração
    """
    logger = IterationLogger(log_path)
    logger.open()

    S = build_initial(instance)
    best = S

    best_cost = cost_fn(best)
    prev_rpd = 0.0

    feasible0 = feasible_fn(instance, S)
    c0 = cost_fn(S)
    rpd0 = rpd_percent(c0, best_cost)

    logger.log({
        "iter": 0,
        "time_s": logger.elapsed_s(),
        "cost": c0,
        "best_cost": best_cost,
        "rpd": rpd0,
        "delta_rpd": 0.0,
        "accepted": 1,
        "temp": 0.0,              # SA ainda não existe no Dia 01
        "destroy_op": "none",
        "repair_op": "none",
        "feasible": int(feasible0),
        "num_edges": num_edges_fn(S),
    })
    prev_rpd = rpd0

    it = 0
    while it < max_iters and logger.elapsed_s() < time_limit_s:
        it += 1

        # placeholder: não altera a solução
        S_candidate = S

        # aceita sempre
        S = S_candidate

        c = cost_fn(S)
        if c < best_cost:
            best = S
            best_cost = c

        feasible = feasible_fn(instance, S)
        rpd = rpd_percent(c, best_cost)
        delta_rpd = rpd - prev_rpd
        prev_rpd = rpd

        logger.log({
            "iter": it,
            "time_s": logger.elapsed_s(),
            "cost": c,
            "best_cost": best_cost,
            "rpd": rpd,
            "delta_rpd": delta_rpd,
            "accepted": 1,
            "temp": 0.0,
            "destroy_op": "none",
            "repair_op": "none",
            "feasible": int(feasible),
            "num_edges": num_edges_fn(S),
        })

    logger.close()
    return best
