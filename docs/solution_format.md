# Formato de instâncias e soluções do problema Clustered Steiner Tree (CluSteiner)

Este documento define como as **instâncias** e **soluções** do problema *Clustered Steiner Tree* (CluSteiner) serão representadas no projeto, tanto em memória (Python/C++) quanto em arquivos de texto para experimentos.

O objetivo é ter um formato **simples, consistente e verificável**, que sirva para:

- Implementar e testar o baseline (SPMST / MST + poda / etc.);
- Rodar heurísticas/meta-heurísticas no futuro;
- Verificar factibilidade (árvore + clusters/local trees);
- Medir custo e estatísticas por instância (AVG, BF, RPD, PI).

---

## 1. Convenções gerais

- Os grafos são **não direcionados** e **ponderados** com pesos positivos.
- Os vértices são indexados de $0$ a $n-1$ no código (Python/C++).
  - O dataset original pode vir com índices $1 \dots n$; a conversão para $0 \dots n-1$ é responsabilidade do *loader*.
- O conjunto de vértices requeridos é denotado por $R$.
- $R$ é particionado em $h$ clusters disjuntos:

$$
R = R_1 \cup R_2 \cup \dots \cup R_h, \quad R_i \cap R_j = \emptyset \text{ para } i \neq j.
$$

- Vértices que não pertencem a $R$ são chamados de **vértices de Steiner** (não-requeridos).
- O grafo pode ser:
  - **Euclidiano** (coordenadas, respeito à desigualdade triangular); ou
  - **Não euclidiano** (apenas pesos arbitrários nas arestas).
  
  Essa informação é usada apenas para análise/comparação de heurísticas.

---

## 2. Estrutura da instância (em memória)

As instâncias serão representadas no código Python por uma classe `Instance` (módulo `src/tcc/instance.py`). A estrutura é a seguinte:

```python
from dataclasses import dataclass
from typing import List, Tuple

Edge = Tuple[int, int, float]

@dataclass
class Instance:
    name: str                    # nome da instância (ex.: "EUC_Type1_Small/10berlin52")
    n: int                       # número de vértices
    m: int                       # número de arestas
    edges: List[Edge]            # lista de arestas (u, v, w), 0-based
    terminals: List[int]         # lista de vértices requeridos (conjunto R)
    clusters: List[List[int]]    # clusters R_0, ..., R_{h-1}
    cluster_of: List[int]        # vetor de tamanho n; -1 para não requeridos
    is_euclidean: bool = False   # flag opcional (instância euclidiana ou não)
```

### 2.1. Significado de cada campo

- **`name`**
  Identificador textual da instância, por exemplo:
  - `"EUC_Type1_Small/10berlin52"`
  - `"NON_EUC_Type5_Large/instance_42"`

- **`n`**
  Número total de vértices do grafo.

- **`m`**
  Número total de arestas do grafo.

- **`edges`**
  Lista de arestas do grafo. Cada aresta é uma tupla `(u, v, w)`:
  - $u$ e $v$ são inteiros em $[0, n-1]$;
  - $w$ é o peso (custo) da aresta, um número real positivo.
  
  Como o grafo é não direcionado, a aresta `(u, v, w)` representa conexão tanto de $u$ para $v$ quanto de $v$ para $u$.

- **`terminals`**
  Lista de vértices requeridos, isto é, o conjunto $R$.
  Todos os vértices em `terminals` devem pertencer exatamente a um cluster $R_k$.

- **`clusters`**
  Lista de clusters $R_0, \dots, R_{h-1}$.
  Cada entrada `clusters[k]` é uma lista de vértices pertencentes ao cluster $k$.
  A união de todos os `clusters[k]` deve ser exatamente o conjunto $R$.

- **`cluster_of`**
  Vetor de tamanho $n$ que indica a qual cluster cada vértice pertence:
  - Se $v \in R_k$, então `cluster_of[v] = k`;
  - Se $v$ não é requerido (vértice de Steiner), então `cluster_of[v] = -1`.

- **`is_euclidean`**
  Indica se a instância é derivada de um conjunto de pontos euclidianos (coordenadas) em que os pesos respeitam desigualdade triangular. Essa informação pode ser útil para algumas heurísticas, mas não altera o formato.

### 2.2. Invariantes que devem sempre valer

Uma instância carregada é considerada **bem formada** se:

1. **Número de arestas:**
   `len(edges) == m`

2. **Limites de vértices:**
   Para toda aresta `(u, v, w)` em `edges`:
   - $0 \le u < n$
   - $0 \le v < n$
   - $w > 0$

3. **Tamanho de `cluster_of`:**
   `len(cluster_of) == n`

4. **Cobertura e disjunção dos clusters:**
   - Cada `clusters[k]` é não vazio;
   - Nenhum vértice aparece em mais de um cluster;
   - A união de todos os `clusters[k]` é exatamente o conjunto de vértices em `terminals`.

5. **Coerência com `cluster_of`:**
   - Para qualquer vértice $v$ em `clusters[k]`: `cluster_of[v] == k`;
   - Para qualquer vértice $v$ que **não** está em nenhum cluster: `cluster_of[v] == -1`.

6. **Coerência entre `terminals` e clusters:**
   `set(terminals) == set().union(*clusters)`

Uma função `Instance.validate()` será usada para checar automaticamente essas condições durante leitura/carregamento.

---

## 3. Estrutura da solução (em memória)

Uma solução candidata para o problema CluSteiner será representada em Python por uma estrutura simples:

```python
from typing import NamedTuple, List, Tuple

TreeEdge = Tuple[int, int]

class Solution(NamedTuple):
    cost: float                   # soma dos pesos das arestas da árvore
    edges: List[TreeEdge]         # arestas da árvore (u, v), 0-based
    feasible: bool                # se passou no verificador de factibilidade
    violations: List[str]         # lista de mensagens de violação (se houver)
```

A parte importante aqui são as regras de **factibilidade** a seguir.

### 3.1. O que é uma solução válida?

Seja $G = (V, E)$ o grafo da instância e $R = R_1 \cup \dots \cup R_h$ o conjunto de vértices requeridos.

Uma solução válida é uma árvore $T = (V_T, E_T)$ tal que:

1. **Árvore (estrutura):**
   - $E_T$ é um subconjunto de $E$;
   - O grafo $T$ é conexo no conjunto de vértices que ele usa $V_T$;
   - $T$ é acíclico;
   - Vale a relação clássica de árvore: $|E_T| = |V_T| - 1$

2. **Cobertura de todos os terminais:**
   - Todo vértice requerido deve estar na árvore: $R \subseteq V_T$
   - Na prática: todo vértice $v$ em `terminals` aparece em pelo menos uma aresta da solução (exceto o caso trivial de instâncias com $|R| = 1$).

3. **Local trees por cluster:**
   - Para cada cluster $R_k$, considere o menor subgrafo de $T$ que conecta todos os vértices de $R_k$ (isto é, a união de todos os caminhos em $T$ entre pares de vértices de $R_k$).
   - Esse subgrafo é chamado de **local tree** do cluster $k$ e tem conjunto de vértices $V_k$.

4. **Disjunção de clusters (local trees disjuntos):**
   - Os conjuntos de vértices dos local trees não podem se sobrepor:
     $V_i \cap V_j = \emptyset \quad \text{para } i \neq j$
   - Intuitivamente: a parte da árvore usada para conectar o cluster $R_1$ não pode reutilizar vértices da parte que conecta o cluster $R_2$, e assim por diante.

5. **Custo da solução:**
   - O custo de uma solução é a soma dos pesos das arestas em $E_T$:
     $\text{cost}(T) = \sum_{(u,v) \in E_T} w(u,v)$
   - No código, esse valor é armazenado em `Solution.cost`; o verificador pode recalcular o custo a partir das arestas para garantir consistência.

### 3.2. Interpretação intuitiva (para documentação)

- `edges` descreve **uma árvore** sobre alguns vértices do grafo.
- Todos os vértices obrigatórios $R$ precisam estar presentes na árvore.
- Cada cluster $R_k$ tem sua "subárvore local" dentro da solução.
- Essas subárvores locais **não se misturam**: o conjunto de vértices usado para conectar o cluster 0 não pode ser reaproveitado para conectar o cluster 1, etc.

Essas regras serão implementadas e checadas pelo verificador de factibilidade.

---

## 4. Formato de arquivo de solução (`.sol`)

Para salvar soluções em disco (para experimentos, benchmark e reprodução), usaremos um formato de arquivo texto simples, com extensão `.sol`.

### 4.1. Regras gerais

- Codificação: UTF-8.
- Comentários são permitidos e começam com `#` no início da linha.
- Há uma solução por arquivo.
- Os vértices são sempre indexados de $0$ a $n-1$ (compatível com a `Instance` em memória).

### 4.2. Estrutura do arquivo `.sol`

Formato geral:

```text
# Comentário opcional
INSTANCE <nome_da_instancia>
COST <valor_float>

EDGES
u0 v0
u1 v1
...
u_{k-1} v_{k-1}
```

Significado:

- `INSTANCE <nome_da_instancia>`
  - Nome da instância, deve coincidir com `Instance.name`.

- `COST <valor_float>`
  - Custo declarado da solução (soma dos pesos das arestas).
  - O verificador pode (e deve) recalcular o custo a partir de `EDGES` para conferir consistência.

- Linha `EDGES`
  - Marca o início da lista de arestas da árvore.

- Cada linha após `EDGES` até o fim do arquivo contém:
  - Dois inteiros `u v` ($0 \le u, v < n$), representando uma aresta não direcionada entre $u$ e $v$.

Não há necessidade de declarar explicitamente quais vértices pertencem a $R$ ou aos clusters no arquivo da solução, pois isso já está presente na instância original (`Instance`).

### 4.3. Exemplo de arquivo `.sol`

```text
# Exemplo de solução para uma instância do tipo EUC_Type1_Small
INSTANCE EUC_Type1_Small/10berlin52
COST 1234.000000

EDGES
0 5
5 7
7 3
3 9
9 2
2 8
8 1
4 6
6 0
```

O verificador vai:
1. Ler o nome da instância.
2. Carregar a instância correspondente.
3. Ler a lista de arestas e montar o grafo da solução.
4. Recalcular o custo.
5. Checar todas as regras de factibilidade da Seção 3.

---

## 5. Verificador de factibilidade (resumo da lógica)

O verificador será implementado como um script Python (por exemplo `tools/check_solution.py`), que recebe:

```bash
python tools/check_solution.py instancia.in solucao.sol
```

e executa os seguintes passos:

1. **Carregar a instância** em um objeto `Instance` e chamar `Instance.validate()`.
2. **Ler a solução** em um objeto `Solution` (a partir do arquivo `.sol`).
3. **Checar se todas as arestas da solução existem no grafo** da instância:
   - Se alguma aresta $(u, v)$ não pertence a $E$, a solução é inválida.

4. **Checar se a solução forma uma árvore:**
   - Constrói o grafo $T$ a partir das arestas da solução;
   - Verifica conectividade no conjunto de vértices usados;
   - Verifica ausência de ciclos;
   - Confere se $|E_T| = |V_T| - 1$.

5. **Checar cobertura de todos os terminais:**
   - Verifica se todo $v$ em `terminals` aparece em pelo menos uma aresta da solução (ou é o único vértice em instâncias triviais).

6. **Checar local trees e disjunção dos clusters:**
   - Para cada cluster $R_k$:
     - Extrai, dentro de $T$, o menor subgrafo que conecta todos os vértices de $R_k$;
     - Determina o conjunto de vértices envolvidos $V_k$.
   - Verifica se $V_i \cap V_j = \emptyset$ para todo $i \neq j$.

7. **Recalcular o custo** da solução a partir das arestas e comparar com o valor declarado em `COST`.
   - Se houver discrepância acima de uma tolerância numérica (ex.: `1e-4`), a solução é considerada inconsistente.

8. **Saída:**
   - Em caso de sucesso: imprime algo como `OK` e retorna código de saída `0`;
   - Em caso de erro: imprime uma mensagem explicando a violação (ex.: `TREE ERROR`, `MISSING TERMINAL`, `DISJOINTNESS VIOLATION`, etc.) e retorna código de saída diferente de zero.

Esse verificador será a referência para dizer se uma solução é **factível** ou **infactível** e será usado em todos os experimentos (baseline, meta-heurísticas, versões com CUDA, etc.).

---

Este documento deve ser considerado a especificação oficial de **como modelamos instâncias e soluções** do problema CluSteiner no projeto. Qualquer novo código (baseline, heurísticas, verificadores, scripts de experimento) deve seguir estas definições para garantir compatibilidade e reprodutibilidade dos resultados.