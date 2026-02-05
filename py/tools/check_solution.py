from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from tcc import Instance, Solution, verify_solution
from tcc.solution import parse_solution_file

app = typer.Typer(help="Verificador de soluções CluSteiner (.sol)")


def load_toy_instance() -> Instance:
    """
    Cria uma instância pequena artificial só para testar o verificador.

    Grafo:
        0 --1-- 1 --2-- 2
                  \
                   3 --3-- 4

    Terminais R = {0, 2, 4}
    Clusters:
        R0 = {0}
        R1 = {2}
        R2 = {4}

    Ainda não usamos arestas da Instance pro custo,
    apenas a estrutura de n, terminals, clusters, cluster_of.
    """
    n = 5
    m = 4  # número de arestas (mas não vamos usar edges aqui ainda)

    edges = [
        (0, 1, 1.0),
        (1, 2, 2.0),
        (1, 3, 1.0),
        (3, 4, 3.0),
    ]

    terminals = [0, 2, 4]
    clusters = [
        [0],  # cluster 0
        [2],  # cluster 1
        [4],  # cluster 2
    ]

    cluster_of = [-1] * n
    for k, Ck in enumerate(clusters):
        for v in Ck:
            cluster_of[v] = k

    inst = Instance(
        name="toy-instance",
        n=n,
        m=m,
        edges=edges,
        terminals=terminals,
        clusters=clusters,
        cluster_of=cluster_of,
        is_euclidean=False,
    )
    inst.validate()
    return inst


@app.command()
def check(
    solution_path: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        file_okay=True,
        readable=True,
        help="Arquivo .sol com a solução a ser verificada",
    ),
    instance_name: Optional[str] = typer.Option(
        None,
        "--instance_name",
        "-n",
        help="Nome da instância (por enquanto ignorado; usamos instância toy interna)",
    ),
):
    """
    Verifica uma solução .sol usando a lógica de verificação estrutural
    (árvore, terminais, clusters).

    OBS: nesta fase, usamos uma instância 'toy' fixa.
    Depois, este comando será conectado ao loader real das instâncias do dataset.
    """
    typer.echo(f"Lendo solução de: {solution_path}")
    sol = parse_solution_file(solution_path)

    typer.echo(f"INSTANCE no .sol = {sol.instance_name}")
    typer.echo(f"COST declarado  = {sol.cost}")
    typer.echo(f"#arestas        = {len(sol.edges)}")

    # Por enquanto, usamos uma instância pequena artificial.
    inst = load_toy_instance()
    typer.echo(f"Usando instância interna: {inst.name} (n={inst.n}, |R|={len(inst.terminals)})")

    result = verify_solution(inst, sol)

    if result.feasible:
        typer.echo("\n✅ Solução FEASÍVEL de acordo com as regras estruturais.")
    else:
        typer.echo("\n❌ Solução INFEASÍVEL. Violações encontradas:")
        for v in result.violations:
            typer.echo(f"  - {v}")


if __name__ == "__main__":
    app()
