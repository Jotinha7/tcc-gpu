from __future__ import annotations

import math
import random
from typing import Any, Callable, List, Tuple, Optional

from .iterlog import IterationLogger


def rpd_percent(cost: float, bks: float) -> float:
    # RPD = 100 * (cost - bks) / bks
    if bks is None or bks <= 0:
        return 0.0
    return 100.0 * (cost - bks) / bks


def sa_accept(rng: random.Random, curr_cost: float, cand_cost: float, temp: float) -> bool:
    """
    Regra SA:
      - se melhorou: aceita
      - se piorou: aceita com probabilidade exp(-(cand-curr)/T)
    """
    if cand_cost <= curr_cost:
        return True
    if temp <= 1e-12:
        return False

    delta = cand_cost - curr_cost
    p = math.exp(-delta / temp)
    return rng.random() < p


def run_alns_sa(
    instance: Any,
    instance_id: str,
    build_initial: Callable[[Any], Any],  # retorna Solution
    cost_fn: Callable[[Any], float],
    feasible_fn: Callable[[Any, Any], bool],
    num_edges_fn: Callable[[Any], int],
    destroy_ops: List[Tuple[str, Callable[[Any, Any, random.Random], Any]]],  # (name, fn(inst, sol, rng)->PartialState)
    repair_ops: List[Tuple[str, Callable[[Any, Any, random.Random], Any]]],   # (name, fn(inst, partial, rng)->Solution)
    log_path: str,
    bks_cost: Optional[float] = None,
    time_limit_s: float = 2.0,
    max_iters: int = 200,
    seed: int = 0,
    t0: Optional[float] = None,    # temperatura inicial
    alpha: float = 0.995,          # resfriamento (0.99~0.999)
) -> Any:
    """
    ALNS com SA:
      - começa com S0 (baseline factível)
      - a cada iteração:
        1) escolhe destroy e repair aleatoriamente
        2) gera candidato
        3) aceita por SA
        4) atualiza best
        5) loga tudo (cost, best_cost, rpd, delta_rpd, accepted, temp, ops...)
    """
    rng = random.Random(seed)

    logger = IterationLogger(log_path)
    logger.open()

    # solução inicial
    S = build_initial(instance)
    best = S

    curr_cost = cost_fn(S)
    best_cost = curr_cost

    # se não passar bks, usamos o best_cost inicial como referência (pra ao menos ter um rpd "interno")
    if bks_cost is None:
        bks_cost = best_cost

    # se não passar T0, escolhemos algo proporcional ao custo (regra prática)
    # ideia: aceitar pioras pequenas no começo
    if t0 is None:
        t0 = 0.05 * curr_cost  # ajuste depois se quiser

    temp = float(t0)

    feasible0 = feasible_fn(instance, S)
    rpd0 = rpd_percent(curr_cost, bks_cost)

    logger.log({
        "iter": 0,
        "time_s": logger.elapsed_s(),
        "cost": curr_cost,
        "best_cost": best_cost,
        "rpd": rpd0,
        "delta_rpd": 0.0,
        "accepted": 1,
        "temp": temp,
        "destroy_op": "none",
        "repair_op": "none",
        "feasible": int(feasible0),
        "num_edges": num_edges_fn(S),
    })

    prev_rpd = rpd0

    it = 0
    while it < max_iters and logger.elapsed_s() < time_limit_s:
        it += 1

        # 1) escolhe operadores (simples: uniforme)
        dname, destroy = rng.choice(destroy_ops)
        rname, repair = rng.choice(repair_ops)

        # 2) gera candidato
        partial = destroy(instance, S, rng)
        S_cand = repair(instance, partial, rng)

        cand_cost = cost_fn(S_cand)
        cand_feasible = feasible_fn(instance, S_cand)

        # 3) aceitação SA
        accepted = 0
        if cand_feasible and sa_accept(rng, curr_cost, cand_cost, temp):
            S = S_cand
            curr_cost = cand_cost
            accepted = 1

        # 4) atualiza best
        if curr_cost < best_cost:
            best = S
            best_cost = curr_cost

        # 5) métricas e log
        rpd = rpd_percent(curr_cost, bks_cost)
        delta_rpd = rpd - prev_rpd
        prev_rpd = rpd

        logger.log({
            "iter": it,
            "time_s": logger.elapsed_s(),
            "cost": curr_cost,
            "best_cost": best_cost,
            "rpd": rpd,
            "delta_rpd": delta_rpd,
            "accepted": accepted,
            "temp": temp,
            "destroy_op": dname,
            "repair_op": rname,
            "feasible": int(feasible_fn(instance, S)),
            "num_edges": num_edges_fn(S),
        })

        # resfriamento
        temp *= alpha

    logger.close()
    return best
