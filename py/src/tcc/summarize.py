from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd
import typer

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


def parse_instance(file_path: Path) -> Dict[str, object]:
    """
    Lê UMA instância (um arquivo .txt) e extrai:
    - nome
    - número de vértices (DIMENSION)
    - número de clusters (GTSP_SETS ou NUMBER_OF_CLUSTERS)
    - número total de terminais (|R|)
    - número de vértices Steiner (DIMENSION - |R|)
    - quantidade de vértices por cluster
    Suporta dois formatos:
    - Euclidiano (GTSP_SET_SECTION)
    - Não-Euclidiano (CLUSTER_SECTION)
    """
    name = file_path.stem
    dimension = None
    num_clusters_header = None

    terminals: set[int] = set()
    cluster_sizes: List[int] = []

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

            # tokens[0] = id do cluster
            vertices = []
            for tok in tokens[1:]:
                if tok == "-1":
                    break
                vertices.append(int(tok))

            terminals.update(vertices)
            cluster_sizes.append(len(vertices))

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

            # tokens[0] = id do cluster
            vertices = []
            for tok in tokens[1:]:
                if tok == "-1":
                    break
                vertices.append(int(tok))

            terminals.update(vertices)
            cluster_sizes.append(len(vertices))

    # ---------- Estatísticas finais ----------
    num_terminals = len(terminals)
    num_steiner = dimension - num_terminals
    num_clusters = (
        num_clusters_header if num_clusters_header is not None else len(cluster_sizes)
    )

    return {
        "instance": name,
        "num_vertices": dimension,
        "num_clusters": num_clusters,
        "num_terminals": num_terminals,
        "num_steiner": num_steiner,
        "cluster_sizes": cluster_sizes,
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
    Varre todas as instâncias em data_dir e gera um CSV de resumo.
    """
    typer.echo(f"Lendo instâncias em: {data_dir}")

    rows: List[Dict[str, object]] = []

    # percorre recursivamente todos os .txt
    for file_path in sorted(data_dir.rglob("*.txt")):
        if not file_path.is_file():
            continue

        meta = infer_metadata(file_path)
        stats = parse_instance(file_path)

        row = {
            **meta,
            **stats,
            "rel_path": str(file_path.relative_to(data_dir)),
        }
        rows.append(row)

    if not rows:
        typer.echo("Nenhuma instância encontrada!")
        raise typer.Exit(code=1)

    df = pd.DataFrame(rows)

    # Expande cluster_sizes em colunas opcionais (máx. 20 clusters, por exemplo)
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

    typer.echo(f"Salvo resumo em: {out_csv}")
    typer.echo()
    typer.echo("Primeiras linhas:")
    typer.echo(df.head().to_string(index=False))


if __name__ == "__main__":
    app()
