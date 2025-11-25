from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
import typer

from tcc import Instance  # nossa classe de instância

app = typer.Typer(help="Resumo das instâncias CluSteiner em data/raw/")


# ---------- Funções auxiliares ----------


def infer_metadata(file_path: Path) -> Dict[str, object]:
    """
    Descobre se é Euclidean/Non-Euclidean, tipo (1/5/6) e tamanho (Small/Large)
    com base no nome da pasta, por exemplo:
    data/raw/EUC_Type1_Small/10berlin52.txt
    """
    dataset_dir = file_path.parent.name  # ex.: EUC_Type1_Small

    is_euclidean = dataset_dir.startswith("EUC_")
    metric = "euclidean" if is_euclidean else "non_euclidean"

    # Tipo (1, 5 ou 6)
    tipo = None
    if "Type1" in dataset_dir:
        tipo = 1
    elif "Type5" in dataset_dir:
        tipo = 5
    elif "Type6" in dataset_dir:
        tipo = 6

    # Tamanho (Small / Large)
    size = "Small" if "Small" in dataset_dir else "Large"

    return {
        "folder": dataset_dir,
        "metric": metric,
        "type": tipo,
        "size_class": size,
    }


def make_cluster_of(n: int, clusters: List[List[int]]) -> List[int]:
    """
    Constrói o vetor cluster_of a partir da lista de clusters.

    - cluster_of[v] = k se v está no cluster k
    - cluster_of[v] = -1 se v não é terminal (Steiner)
    """
    cluster_of = [-1] * n
    for k, Ck in enumerate(clusters):
        for v in Ck:
            cluster_of[v] = k
    return cluster_of


def parse_instance(file_path: Path, is_euclidean: bool) -> Dict[str, object]:
    """
    Lê UMA instância (um arquivo .txt) e extrai:

    - nome
    - número de vértices (DIMENSION)
    - número de clusters (GTSP_SETS ou NUMBER_OF_CLUSTERS)
    - número total de terminais (|R|)
    - número de vértices Steiner (DIMENSION - |R|)
    - quantidade de vértices por cluster
    - constrói um objeto Instance (ainda SEM arestas reais, por enquanto)

    Suporta dois formatos:
    - Euclidiano (GTSP_SET_SECTION)
    - Não-Euclidiano (CLUSTER_SECTION)

    OBS: neste momento, ainda não lemos as arestas / coordenadas do grafo.
    Vamos apenas montar corretamente:
      - terminals
      - clusters
      - cluster_of
    e usar isso para validar a estrutura via Instance.validate().
    """
    name = file_path.stem
    dimension = None
    num_clusters_header = None

    # Aqui vamos guardar clusters explicitamente (1-based no arquivo).
    clusters_1based: List[List[int]] = []

    # Lê todas as linhas não vazias
    with file_path.open("r") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    # ---------- 1ª passada: cabeçalho ----------
    for line in lines:
        if line.startswith("Name"):
            parts = line.split(":")
            if len(parts) >= 2:
                name = parts[1].strip()

        elif line.startswith("DIMENSION"):
            parts = line.split(":")
            dimension = int(parts[1].strip())

        elif line.startswith("GTSP_SETS"):
            parts = line.split(":")
            num_clusters_header = int(parts[1].strip())

        elif line.startswith("NUMBER_OF_CLUSTERS"):
            parts = line.split(":")
            num_clusters_header = int(parts[1].strip())

    if dimension is None:
        raise ValueError(f"Arquivo {file_path} não possui DIMENSION")

    # Descobre qual formato é: GTSP_SET_SECTION ou CLUSTER_SECTION
    has_gtsp = any(line.startswith("GTSP_SET_SECTION") for line in lines)
    has_cluster_sec = any(line.startswith("CLUSTER_SECTION") for line in lines)

    mode = None
    if has_gtsp:
        mode = "gtsp"
    elif has_cluster_sec:
        mode = "cluster"

    # ---------- 2ª passada: leitura dos clusters ----------
    if mode == "gtsp":
        in_sets_section = False
        for line in lines:
            if line.startswith("GTSP_SET_SECTION"):
                in_sets_section = True
                continue
            if not in_sets_section:
                continue
            if line.upper().startswith("EOF"):
                break

            tokens = line.split()
            if len(tokens) < 3:
                continue

            # tokens[0] = id do cluster (ignoramos aqui)
            vertices_1based: List[int] = []
            for tok in tokens[1:]:
                if tok == "-1":
                    break
                vertices_1based.append(int(tok))

            if vertices_1based:
                clusters_1based.append(vertices_1based)

    elif mode == "cluster":
        in_cluster = False
        for line in lines:
            if line.startswith("CLUSTER_SECTION"):
                in_cluster = True
                continue
            if not in_cluster:
                continue

            tokens = line.split()
            if len(tokens) < 3:
                continue

            # tokens[0] = id do cluster (ignoramos aqui)
            vertices_1based: List[int] = []
            for tok in tokens[1:]:
                if tok == "-1":
                    break
                vertices_1based.append(int(tok))

            if vertices_1based:
                clusters_1based.append(vertices_1based)

    # ---------- Construção de terminals, clusters 0-based e cluster_sizes ----------

    # Converte clusters de 1-based -> 0-based
    clusters: List[List[int]] = []
    for C1 in clusters_1based:
        C0 = [v - 1 for v in C1]  # 1..DIMENSION -> 0..DIMENSION-1
        clusters.append(C0)

    # Conjunto de terminais R
    terminals_set = set(v for C in clusters for v in C)
    num_terminals = len(terminals_set)

    # Tamanho dos clusters (para estatística / CSV)
    cluster_sizes: List[int] = [len(C) for C in clusters]

    num_steiner = dimension - num_terminals
    num_clusters = (
        num_clusters_header if num_clusters_header is not None else len(clusters)
    )

    # cluster_of: n posições, -1 para não requeridos
    cluster_of = make_cluster_of(dimension, clusters)

    # ---------- Construção do objeto Instance ----------

    # Ainda não estamos lendo as arestas reais, então usamos lista vazia.
    edges: List[tuple[int, int, float]] = []

    inst = Instance(
        name=name,
        n=dimension,
        m=len(edges),
        edges=edges,
        terminals=sorted(terminals_set),
        clusters=clusters,
        cluster_of=cluster_of,
        is_euclidean=is_euclidean,
    )

    # Se algo estiver inconsistente (clusters, cluster_of, terminals), isso explode aqui.
    inst.validate()

    # Retornamos estatísticas + o próprio objeto de instância (para debug/uso futuro)
    return {
        "instance": name,
        "num_vertices": dimension,
        "num_clusters": num_clusters,
        "num_terminals": num_terminals,
        "num_steiner": num_steiner,
        "cluster_sizes": cluster_sizes,
        "_inst": inst,  # campo interno, não vai pro CSV
    }


# ---------- Comando de linha de comando ----------


@app.command()
def summarize(
    data_dir: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=False,
        dir_okay=True,
        help="Diretório raiz com as instâncias (ex.: ../data/raw)",
    ),
    out_csv: Path = typer.Option(
        ...,
        "--out_csv",
        "-o",
        help="Caminho do CSV de saída (ex.: ../data/processed/instances.csv)",
    ),
):
    """
    Varre todas as instâncias em data_dir, valida a estrutura de clusters/terminals
    com Instance.validate() e gera um CSV de resumo.
    """
    typer.echo(f"Lendo instâncias em: {data_dir}")

    rows: List[Dict[str, object]] = []

    # percorre recursivamente todos os .txt
    for file_path in sorted(data_dir.rglob("*.txt")):
        if not file_path.is_file():
            continue

        meta = infer_metadata(file_path)
        is_euclidean = meta["metric"] == "euclidean"

        stats = parse_instance(file_path, is_euclidean=is_euclidean)
        inst = stats["_inst"]

        # Log simples pra garantir que o Instance passou no validate
        typer.echo(
            f"OK: {inst.name} "
            f"(n={inst.n}, |R|={len(inst.terminals)}, h={len(inst.clusters)})"
        )

        # Monta linha para o CSV (sem o campo interno _inst)
        row = {
            **meta,
            "instance": stats["instance"],
            "num_vertices": stats["num_vertices"],
            "num_clusters": stats["num_clusters"],
            "num_terminals": stats["num_terminals"],
            "num_steiner": stats["num_steiner"],
            "rel_path": str(file_path.relative_to(data_dir)),
        }
        # cluster_sizes vai virar colunas depois
        row["cluster_sizes"] = stats["cluster_sizes"]

        rows.append(row)

    if not rows:
        typer.echo("Nenhuma instância encontrada!")
        raise typer.Exit(code=1)

    df = pd.DataFrame(rows)

    # Expande cluster_sizes em colunas opcionais (máx. N clusters reais)
    max_clusters = max(len(cs) for cs in df["cluster_sizes"])
    for i in range(max_clusters):
        col_name = f"cluster_size_{i+1}"
        df[col_name] = df["cluster_sizes"].apply(
            lambda cs, i=i: cs[i] if i < len(cs) else None
        )

    # não precisamos guardar a lista inteira no CSV
    df = df.drop(columns=["cluster_sizes"])

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_csv, index=False)

    typer.echo(f"\nSalvo resumo em: {out_csv}")
    typer.echo()
    typer.echo("Primeiras linhas:")
    typer.echo(df.head().to_string(index=False))


if __name__ == "__main__":
    app()
