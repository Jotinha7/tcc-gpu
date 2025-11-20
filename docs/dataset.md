# Dataset – Clustered Steiner Tree (CluSteiner)

Este documento descreve o dataset usado neste TCC, extraído do repositório
**CluSteiner-Dataset**, publicado pelos autores do artigo:

> *An online transfer learning based multifactorial evolutionary algorithm  
> for solving the clustered Steiner tree problem (2024)*.

---

## 1. Fonte do Dataset

O dataset original é baseado no conjunto **MOM-LIB**, que contém instâncias
do problema **Clustered Traveling Salesman Problem (CluTSP)**.

Os autores do artigo adaptam essas instâncias para o problema  
**Clustered Steiner Tree (CluSteiner)** com o seguinte processo:

- cada instância possui um conjunto de **vértices terminais obrigatórios** R;  
- R é dividido em **clusters** (R₁, R₂, ..., Rₕ);  
- todos os vértices em R **devem aparecer na solução**;  
- vértices fora de R são **Steiner opcionais**.

O repositório original contém instâncias:

- **Euclidianas** (distância EUC_2D)
- **Não-Euclidianas** (distâncias arbitrárias)

---

## 2. Organização no Projeto

A estrutura do dataset dentro do repositório é:

data/
raw/
EUC_Type1_Small/
EUC_Type1_Large/
EUC_Type5_Small/
EUC_Type5_Large/
EUC_Type6_Small/
EUC_Type6_Large/
NON_EUC_Type1_Small/
NON_EUC_Type1_Large/
NON_EUC_Type5_Small/
NON_EUC_Type5_Large/
NON_EUC_Type6_Small/
NON_EUC_Type6_Large/


Cada pasta contém dezenas de arquivos `.txt`, onde **cada arquivo representa uma instância**.

---

## 3. Estrutura de uma instância

Cada arquivo segue o formato inspirado na TSPLIB/GTSP.

Exemplo (retirado da instância `10berlin52.txt`):

Name : 10berlin52
DIMENSION : 52
GTSP_SETS : 10
NODE_COORD_SECTION
1 565 575
2 25 185
...
52 1740 245
GTSP_SET_SECTION
1 1 -1
2 13 28 52 -1
3 2 -1
4 16 20 -1
5 4 40 46 -1
6 9 -1
7 33 -1
8 8 45 -1
9 11 12 -1
10 3 -1


A estrutura significa:

### 3.1. Cabeçalho

- **Name**: nome da instância  
- **DIMENSION**: número total de vértices (|V|)  
- **GTSP_SETS**: número de clusters (h)

### 3.2. NODE_COORD_SECTION

Lista (id, x, y) de **todos** os vértices do grafo.

Ex.:  
`1 565 575` → vértice 1 tem coordenadas (565, 575)

### 3.3. GTSP_SET_SECTION

Esta seção lista **os vértices terminais**, agrupados em clusters.

Exemplo interpretado:

Cluster 1: {1}
Cluster 2: {13, 28, 52}
Cluster 3: {2}
Cluster 4: {16, 20}
Cluster 5: {4, 40, 46}
Cluster 6: {9}
Cluster 7: {33}
Cluster 8: {8, 45}
Cluster 9: {11, 12}
Cluster 10: {3}

---

## 4. Terminais e Vértices Steiner

> → A árvore precisa conter **todos os terminais**.

Portanto:

- todos os vértices listados no `GTSP_SET_SECTION` são **terminais obrigatórios**;  
- qualquer vértice **não listado** é um vértice **Steiner opcional**.

No exemplo `10berlin52`:

- DIMENSION = 52  
- Terminais = 17 vértices  
- Steiner = 35 vértices

---

## 5. Tipos de instâncias

O dataset contém seis tipos (1 a 6).  
Neste TCC utilizamos os tipos 1, 5 e 6 (versões Small e Large).

### Type 1
Clusters criados com base em regiões estruturadas.

### Type 5
Clusters definidos por agrupamento geométrico.

### Type 6
Clusters com estrutura mais irregular.

Cada tipo possui duas variantes:

- **Small** → instâncias pequenas (típico: 50–100 vértices)  
- **Large** → instâncias grandes (típico: 250–450 vértices)

---

## 6. Resumo para implementação

Para cada arquivo `.txt`:

- Ler `DIMENSION`  
- Ler lista de vértices (todos são candidatos a Steiner)  
- Ler `GTSP_SET_SECTION` e anotar:
  - clusters R₁, R₂, ..., Rₕ  
  - conjunto total R  
- Identificar:
  - |V| = número de vértices  
  - |R| = número de terminais  
  - |Steiner| = |V| − |R|  
  - clusters e seus tamanhos  
- Salvar em um `.csv` para análise posterior

