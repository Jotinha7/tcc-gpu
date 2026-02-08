from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from tcc.solution import Solution, TreeEdge


@dataclass
class PartialState:
    """
    Estado parcial após uma destruição (destroy).

    A ideia é:
      - NÃO mexer em local_edges (arestas dentro do cluster).
      - Remover algumas global_edges para "quebrar" o grafo global.
      - Guardar os componentes no nível de clusters (grafo contraído).
    """

    # solução original (antes de destruir)
    base_solution: Solution

    # arestas que NÃO mudam hoje
    local_edges: List[TreeEdge]

    # arestas globais após remoções
    global_edges_remaining: List[TreeEdge]

    # arestas globais removidas pelo destroy
    global_edges_removed: List[TreeEdge]

    # componentes no nível dos clusters: cada componente é uma lista de ids de cluster
    components: List[List[int]]

    # para cada cluster k, qual componente ele pertence (id = índice em components)
    cluster_to_component: List[int]

    # se o destroy escolheu um cluster específico (D2), guardamos aqui
    destroyed_cluster: Optional[int] = None

    # metadados livres (nome do operador, k, seed, etc.)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_components(self) -> int:
        return len(self.components)

    def current_edges(self) -> List[TreeEdge]:
        """Arestas atuais (local intacto + global restante)."""
        return list(self.local_edges) + list(self.global_edges_remaining)
