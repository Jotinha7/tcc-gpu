from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional


def avg_cost(costs: Iterable[float]) -> float:
    costs = list(costs)
    if not costs:
        raise ValueError("avg_cost: lista vazia")
    return sum(costs) / len(costs)


def best_found(costs: Iterable[float]) -> float:
    costs = list(costs)
    if not costs:
        raise ValueError("best_found: lista vazia")
    return min(costs)


def rpd(avg: float, bks: float) -> float:
    """
    Relative Percentage Difference (minimização):
        RPD = (Avg - BKS) / BKS * 100
    (no paper: gap entre Avg e best-known)
    """
    if bks <= 0:
        raise ValueError(f"rpd: BKS inválido ({bks})")
    return (avg - bks) / bks * 100.0


def pi(avg_a: float, avg_b: float) -> float:
    """
    Improvement Percentage de A sobre B:
        PI_AB = (Avg_B - Avg_A) / Avg_B * 100
    (no paper)
    """
    if avg_b <= 0:
        raise ValueError(f"pi: Avg_B inválido ({avg_b})")
    return (avg_b - avg_a) / avg_b * 100.0


@dataclass
class MetricsRow:
    instance: str
    avg: float
    bf: float
    bks: float
    rpd: float
    pi: Optional[float]  # pode ficar None se não houver algoritmo B de referência
