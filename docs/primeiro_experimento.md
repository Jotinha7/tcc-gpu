# Baseline + Verificação + Métricas + Runner

## Objetivos completados:
Construir uma **pipeline experimental mínima, reproduzível e “à prova de erro”** para o CluSteiner:

1. **Carregar instâncias do dataset** (ao menos *EUC Type1 Small*).
2. Gerar uma **solução baseline** (algo simples, mas válido).
3. **Verificar factibilidade** (árvore + cobre todos terminais + disjunção entre clusters).
4. Calcular métricas (**AVG/BF/RPD/PI**) e salvar em **CSV** por instância.
5. Critério de aceitação (CA): rodar **Type1 Small (todas)** sem erro.

---

## O que foi implementado (entregáveis)

### 1) Formato de solução
- **Arquivo:** `docs/solution_format.md`
- Define como salvar uma solução em texto (ex.: `INSTANCE`, `COST`, `EDGES`).
- Motivação: padronizar saída para verificador + experimentos + futuro artigo.

### 2) Estrutura de instância (Python)
- **Arquivos principais:** `py/src/tcc/instance.py`, `py/src/tcc/__init__.py`
- `Instance` concentra:
  - `n` (nº de vértices)
  - `edges` (arestas/pesos; no EUC geramos grafo completo por distância)
  - `clusters` (lista de listas; cada cluster é um conjunto de terminais)
  - `terminals` (união de todos clusters)
  - `cluster_of` (vetor que diz a qual cluster cada vértice terminal pertence)
- `Instance.validate()` garante invariantes (ex.: todo terminal está em algum cluster).

### 3) Verificador de solução (factibilidade)
- **Arquivos:**  
  - `py/src/tcc/solution.py` (parser do `.sol`)  
  - `py/src/tcc/verify.py` (validações)  
  - `py/tools/check_solution.py` (CLI para checar solução)
- O verificador checa, de forma estruturada:
  1. **Formato básico** (arestas dentro do range, etc.)
  2. **Árvore** (conectividade + propriedade `|E| = |V|-1`)
  3. **Cobertura** (todos vértices de `R` aparecem)
  4. **Disjunção entre clusters** via “local tree” de cada cluster:
     - Para cada cluster, pega os caminhos na árvore entre seus terminais
     - União dos vértices nesses caminhos = `V_k` (local tree do cluster k)
     - Exige `V_i ∩ V_j = ∅` para `i ≠ j`

> Observação: esse verificador é o “juiz” dos seus experimentos. Se passar aqui, você tem confiança que está respeitando as restrições do problema.

### 4) Loader mínimo (instâncias reais do paper)
- **Arquivo:** `py/src/tcc/tsplib_loader.py`
- Implementa um **loader mínimo para EUC** que lê:
  - `DIMENSION`
  - `NODE_COORD_SECTION`
  - `GTSP_SET_SECTION`
- Constrói o grafo completo com distância EUC_2D (com arredondamento padrão TSPLIB).
- Isso permite rodar experimentos em `data/raw/EUC_Type1_Small/*.txt`.

> Por que “mínimo”?  
> Porque cobre o caso EUC+coords+GTSP_SET_SECTION. NON_EUC e variações podem exigir outro parser.

### 5) Métricas e runner (experimentos automatizados)
- **Arquivos:**  
  - `py/src/exp/metrics.py`  
  - `py/src/exp/runner.py`  
  - `py/src/exp/bks_type1_small.csv`  
- `metrics.py` implementa:
  - **AVG**: média dos custos de múltiplas execuções
  - **BF**: melhor custo encontrado (min)
  - **RPD**: gap relativo (%) entre `AVG` e `BKS`
  - **PI**: melhoria percentual entre dois métodos (no começo ficou 0.0 por termos só 1 método)
- `runner.py`:
  - varre instâncias
  - roda baseline
  - chama verificador (para garantir factibilidade)
  - salva CSV com métricas e tempo

---

## Baseline atual (intuitivo)
**Baseline usado no runner:** “2-level MST nos terminais”

1. Para cada cluster `R_k`, calcula uma MST **apenas** nos terminais daquele cluster.
2. Conecta clusters entre si por uma MST no “grafo de clusters”, onde o peso entre cluster i e j é a **menor aresta** entre qualquer terminal de `R_i` e qualquer terminal de `R_j`.
3. Junta todas as arestas. Isso gera uma árvore só com terminais, normalmente preservando disjunção.

---

## Como rodar (comandos práticos)

### Ativar o ambiente
```bash
cd ~/dev/tcc-gpu
source py/.venv/bin/activate
```

### Rodar 1 instância (teste rápido)
```bash
python -m exp.runner   --data-dir data/raw/EUC_Type1_Small   --out-csv experiments/results/type1_small_baseline.csv   --bks-csv py/src/exp/bks_type1_small.csv   --runs 1   --limit 1
```

### Rodar TODAS as instâncias do Type1 Small (CA)
Descubra quantas existem:
```bash
ls data/raw/EUC_Type1_Small/*.txt | wc -l
```

Use o número retornado em `--limit`.

> Dica: salve resultados em `experiments/results/` para manter fora de `data/` (dataset/raw/processed) e facilitar versionamento do CSV final.

---

## O que significa o `bks_type1_small.csv`
- BKS = **best known solution** (melhor solução conhecida para a instância).
- No começo, como você ainda não tem a tabela do paper pronta, o runner usa:
  - **melhor encontrado nas suas execuções até agora**
- Com o tempo, você pode substituir/preencher o BKS com valores do paper, se tiver.

---