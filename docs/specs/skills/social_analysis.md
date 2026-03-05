# Social Analysis - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | SocialAnalysis |
| **Categoria** | Analysis |
| **Versao** | 1.0.0 |
| **Status** | Development |
| **Prioridade** | Media |
| **Modulo** | `src.skills.social_analysis` (planejado) |
| **Criado em** | 2026-03-03 |
| **Ultima Atualizacao** | 2026-03-03 |

---

## Objetivo

Analisa a rede social de um lead dentro do grafo CRM: conexoes, influencia, comunidades e padroes de interacao. Transforma o grafo de relacionamentos em insights acionaveis para priorizacao e segmentacao.

### Problema que Resolve
Leads nao existem isoladamente — um lead pode ser influenciador de 10 outros, ou estar em 3 flows diferentes. Sem analise de rede, essas relacoes ficam invisiveis e o CRM trata cada lead como entidade independente.

### Valor Agregado
- Identificacao de leads influenciadores (alto degree centrality)
- Deteccao de comunidades (leads que interagem entre si)
- Network-based scoring: leads bem conectados tem mais valor
- Visualizacao de clusters no LeadGraph
- Propagacao de trust: leads conectados a leads de alto trust herdam confianca

---

## Agentes que Utilizam

| Agente | Uso | Frequencia |
|--------|-----|------------|
| **CrmAgent** | Enriquece LeadGraph com metricas de rede | Media |
| **analytics_agent** | Reports de segmentacao por comunidade | Baixa |
| **marketing_agent** | Identifica influenciadores para campanhas | Media |
| **social_media_agent** | Mapeia presenca social de leads | Baixa |

---

## Interface

### Input

```python
{
    "lead_id": "lead_abc123",      # Opcional: analise centrada em um lead
    "analysis_type": "full",        # full | centrality | community | influence
    "depth": 3,                     # profundidade de traversal no grafo
    "options": {
        "include_agents": true,     # incluir nodes Agent na analise
        "include_flows": true,      # incluir nodes Flow na analise
        "min_trust": 0.0           # filtrar leads abaixo deste trust
    }
}
```

### Output

```python
{
    "status": "success",
    "data": {
        # Metricas de centralidade do lead
        "centrality": {
            "degree": 12,                   # total de conexoes diretas
            "betweenness": 0.35,            # intermediacao na rede
            "closeness": 0.72,              # proximidade media
            "pagerank": 0.08                # influencia iterativa
        },
        # Comunidade detectada
        "community": {
            "id": "comm_3",
            "size": 8,
            "members": ["lead_abc", "lead_def", "lead_ghi", ...],
            "dominant_source": "telegram",
            "avg_trust": 0.68
        },
        # Influencia
        "influence": {
            "score": 0.75,                  # 0-1
            "direct_connections": 12,
            "indirect_reach": 34,           # leads a 2-3 hops
            "shared_flows": 3
        },
        # Leads proximos recomendados
        "recommendations": [
            {"lead_id": "lead_xyz", "reason": "same community, high trust", "score": 0.9},
            {"lead_id": "lead_uvw", "reason": "shared 2 flows", "score": 0.7}
        ]
    },
    "metadata": {
        "execution_time_ms": 250,
        "nodes_analyzed": 42,
        "edges_analyzed": 78,
        "algorithm": "louvain_community + pagerank"
    }
}
```

### Exceções

| Excecao | Quando Ocorre | Como Tratar |
|---------|---------------|-------------|
| Lead isolado | Lead sem conexoes | Retornar metricas zeradas, sem erro |
| Grafo vazio | Nenhum lead no Neo4j | Retornar resultado vazio |
| Timeout | Grafo muito grande (>10k nodes) | Limitar depth e retornar parcial |

---

## Implementacao

### Algoritmos

| Algoritmo | Uso | Complexidade |
|-----------|-----|-------------|
| **Degree Centrality** | Contagem de conexoes diretas | O(V) |
| **PageRank** | Influencia iterativa na rede | O(V + E) * iterations |
| **Louvain Community Detection** | Agrupamento de leads | O(V * log V) |
| **Betweenness Centrality** | Identificar brokers/pontes | O(V * E) |
| **Closeness Centrality** | Acessibilidade na rede | O(V * (V + E)) |

### Cypher Queries

```cypher
-- Degree centrality de um lead
MATCH (l:Lead {id: $lead_id})-[r]-(connected)
RETURN count(r) AS degree, labels(connected) AS types

-- Network do lead (3 hops)
MATCH (l:Lead {id: $lead_id})-[*1..3]-(connected)
WHERE connected:Lead OR connected:Flow OR connected:Agent
RETURN DISTINCT connected, labels(connected) AS types

-- Leads compartilhando flows
MATCH (l1:Lead {id: $lead_id})-[:PART_OF_FLOW]->(f:Flow)<-[:PART_OF_FLOW]-(l2:Lead)
WHERE l1 <> l2
RETURN l2.id AS lead_id, l2.name AS name, l2.trust AS trust,
       count(f) AS shared_flows
ORDER BY shared_flows DESC

-- Community detection via GDS (quando disponivel)
CALL gds.louvain.stream('lead-graph', {relationshipTypes: ['INTERACTED_WITH', 'PART_OF_FLOW']})
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).id AS lead_id, communityId
ORDER BY communityId

-- Subgrafo para analise (exportar para NetworkX)
MATCH (l:Lead)-[r:INTERACTED_WITH|PART_OF_FLOW]-(connected)
WHERE connected:Lead OR connected:Flow
RETURN l.id AS source, type(r) AS rel_type,
       connected.id AS target, connected.trust AS target_trust
```

### Tecnologias Utilizadas
- **Neo4j**: Traversal e queries de grafo
- **Neo4j GDS** (futuro): Graph algorithms (PageRank, Louvain)
- **NetworkX** (fallback): Algoritmos em Python quando GDS indisponivel
- **NumPy**: Calculo de metricas de centralidade

### Dependencias
```txt
neo4j>=5.0.0
networkx>=3.0.0       # fallback para algoritmos de grafo
numpy>=1.24.0         # calculo de metricas
```

### Variaveis de Ambiente
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
# Opcional: Neo4j GDS
NEO4J_GDS_ENABLED=false
```

### Estrutura de Codigo

```python
class SocialAnalyzer:
    def __init__(self, graph_manager):
        self.graph = graph_manager

    def analyze(self, lead_id: str = None, analysis_type: str = "full",
                depth: int = 3) -> dict:
        """Executa analise social completa ou focada."""
        subgraph = self._extract_subgraph(lead_id, depth)

        result = {}
        if analysis_type in ("full", "centrality"):
            result["centrality"] = self._compute_centrality(subgraph, lead_id)
        if analysis_type in ("full", "community"):
            result["community"] = self._detect_communities(subgraph, lead_id)
        if analysis_type in ("full", "influence"):
            result["influence"] = self._compute_influence(subgraph, lead_id)

        result["recommendations"] = self._recommend(subgraph, lead_id)
        return result

    def _extract_subgraph(self, lead_id, depth):
        """Extrai subgrafo do Neo4j para analise local."""
        ...

    def _compute_centrality(self, subgraph, lead_id):
        """Degree, betweenness, closeness, pagerank."""
        ...

    def _detect_communities(self, subgraph, lead_id):
        """Louvain community detection."""
        ...

    def _compute_influence(self, subgraph, lead_id):
        """Score de influencia baseado em PageRank + reach."""
        ...

    def _recommend(self, subgraph, lead_id):
        """Recomenda leads proximos baseado em similaridade de rede."""
        ...
```

---

## Metricas

### KPIs
- **Execution Time**: < 500ms (p95) para analise de um lead
- **Full Graph Analysis**: < 10s para 1000 leads
- **Community Detection Quality**: Modularity > 0.3
- **Recommendation Relevance**: > 70% dos leads recomendados sao confirmados como relevantes

### Monitoramento
```python
{
  "skill": "SocialAnalysis",
  "timestamp": "2026-03-03T10:00:00Z",
  "metrics": {
    "analyses_performed": 15,
    "avg_execution_time_ms": 250,
    "communities_detected": 4,
    "avg_community_size": 8,
    "avg_degree_centrality": 5.3,
    "isolated_leads": 3
  }
}
```

---

## Testes

### Casos de Teste

1. **Teste de Lead Isolado**
   - Input: Lead sem conexoes
   - Output esperado: degree=0, community=solo, influence=0

2. **Teste de Hub Lead**
   - Input: Lead conectado a 10+ leads
   - Output esperado: alto degree, alto pagerank

3. **Teste de Community Detection**
   - Input: Grafo com 2 clusters distintos
   - Output esperado: 2 comunidades detectadas

4. **Teste de Recommendation**
   - Input: Lead em community com 5 membros
   - Output esperado: 4 recomendacoes com scores

5. **Teste de Depth Limiting**
   - Input: depth=1
   - Output esperado: somente conexoes diretas

6. **Teste de Performance**
   - Input: 500 leads, 1000 edges
   - Output esperado: analise completa < 5s

### Comandos de Teste
```bash
# Quando implementado
pytest tests/skills/test_social_analysis.py -v

# Teste manual via Cypher
python -c "
from src.neural_link.graph.manager import GraphManager
gm = GraphManager.from_env()
rows = gm.execute_read('''
  MATCH (l:Lead {id: \"lead_abc123\"})-[*1..3]-(c)
  RETURN count(DISTINCT c) AS reach
''')
print(f'Network reach: {rows[0][\"reach\"]}')"
```

---

## Integracao

### Como Usar em Agentes

```python
from src.skills.social_analysis import SocialAnalyzer

analyzer = SocialAnalyzer(graph_manager=graph)

# Analise completa de um lead
result = analyzer.analyze(lead_id="lead_abc123")
print(f"Influence: {result['influence']['score']}")
print(f"Community: {result['community']['id']} ({result['community']['size']} members)")

# Analise de comunidade apenas
community = analyzer.analyze(lead_id="lead_abc123", analysis_type="community")
```

### Como Usar no Frontend (LeadGraph)

O resultado de Social Analysis enriquece o LeadGraph.tsx:
- **Degree centrality** -> tamanho do node
- **Community** -> cor do cluster
- **PageRank** -> opacidade do node
- **Recommendations** -> edges pontilhadas sugeridas

---

## Roadmap

### Versao Atual (1.0.0)
- OK Spec tecnica completa
- OK Cypher queries de subgrafo e network
- OK GET_LEAD_NETWORK query no queries.py

### Proxima Versao (1.1.0)
- Implementar SocialAnalyzer class
- Degree + closeness centrality via NetworkX
- Basic community detection (connected components)
- Endpoint GET /crm/leads/{id}/network

### Futuro (2.0.0)
- Neo4j GDS integration (PageRank, Louvain nativo)
- Influence propagation (trust cascade)
- Temporal network analysis (evolucao da rede)
- Social graph export para ferramentas externas

---

## Referencias

- [CRM Agent Spec](../agents/crm_agent.md)
- [Lead Scoring Skill](lead_scoring.md)
- [CRM Product Docs](../../product/crm/README.md)
- [Neo4j Queries - GET_LEAD_NETWORK](../../../src/neural_link/graph/queries.py)
- [LeadGraph Component](../../../frontend/src/modules/crm/LeadGraph.tsx)
- [Skills Template](TEMPLATE.md)

---

**Mantido por**: Neural Link Team
**Ultima Revisao**: 2026-03-03
