# 🎨 Workflow Diagrams - Bunker Intelligence

Diagramas visuais dos principais fluxos do sistema.

## 📥 Fluxo de Ingestão em Massa

```mermaid
graph TB
    A[Repositório GitHub<br/>zie619/zie619.github.io] -->|GitHub API| B[GitHub Ingestor]
    B -->|Lista arquivos .json| C{É workflow n8n?}
    C -->|Sim| D[n8n Extractor]
    C -->|Não| E[Ignora]
    D -->|Extrai módulos| F[Operation Modules]
    F -->|Adiciona metadados| G[Chunks com category:<br/>external_template]
    G -->|Embeddings| H[(ChromaDB)]
    H -->|Carrega chunks| I[n8n Knowledge Processor]
    I -->|Gera| J[n8n_capabilities.md]
    I -->|Gera| K[n8n_recipes.md]
    I -->|Gera| L[n8n_master_context.json]
    
    style A fill:#e1f5ff
    style H fill:#ffe1e1
    style J fill:#e1ffe1
    style K fill:#e1ffe1
    style L fill:#e1ffe1
```

## 🤖 Fluxo do ComposerAgent

```mermaid
graph TB
    A[Usuário: /create_n8n<br/>objetivo] -->|Telegram| B[Telegram Handler]
    B -->|Invoca| C[ComposerAgent]
    C -->|1. Busca templates| D[(ChromaDB)]
    D -->|Retorna templates<br/>relevantes| C
    C -->|2. Identifica componentes| E[Component Analyzer]
    E -->|Trigger, Processors,<br/>Output| C
    C -->|3. Compõe workflow| F[Workflow Builder]
    F -->|Combina templates| G[JSON n8n]
    G -->|4. Valida e enriquece| H[Validator]
    H -->|Workflow válido| I[Salva em<br/>data/generated_workflows/]
    I -->|Retorna resultado| B
    B -->|Envia resposta| J[Usuário recebe:<br/>- Arquivo JSON<br/>- Templates usados<br/>- Instruções]
    
    style A fill:#e1f5ff
    style D fill:#ffe1e1
    style G fill:#fff4e1
    style J fill:#e1ffe1
```

## 🔍 Fluxo de Busca Híbrida (HybridRAG)

```mermaid
graph TB
    A[Query do usuário] -->|Roteamento| B[QueryRouter]
    B -->|Define pesos| C{Tipo de query?}
    C -->|Semântica| D[ChromaDB<br/>Vector Search]
    C -->|Conceitual| E[Neo4j<br/>Graph Search]
    C -->|Exata| F[TF-IDF<br/>Keyword Search]
    D -->|Resultados| G[ResultMerger]
    E -->|Resultados| G
    F -->|Resultados| G
    G -->|Combina com pesos| H[Resultados Ranqueados]
    H -->|Top K| I[Retorna ao usuário]
    
    style A fill:#e1f5ff
    style D fill:#ffe1e1
    style E fill:#ffe1e1
    style F fill:#ffe1e1
    style I fill:#e1ffe1
```

## 📊 Fluxo de Geração de Conhecimento

```mermaid
graph TB
    A[(ChromaDB<br/>15.000+ chunks)] -->|Filtra| B[external_template<br/>chunks]
    B -->|Agrupa por workflow| C[Workflow Classifier]
    C -->|Classifica| D{Categoria?}
    D -->|AI/LLM| E1[AI Category]
    D -->|Marketing| E2[Marketing Category]
    D -->|DevOps| E3[DevOps Category]
    D -->|Outros| E4[Other Categories]
    E1 --> F[Synthesize Capabilities]
    E2 --> F
    E3 --> F
    E4 --> F
    F -->|Gera| G[n8n_capabilities.md<br/>- Integrações<br/>- Serviços<br/>- Node types]
    F -->|Gera| H[n8n_recipes.md<br/>- Receitas por categoria<br/>- Fluxos detalhados]
    F -->|Gera| I[n8n_master_context.json<br/>- Best practices<br/>- Padrões globais]
    
    style A fill:#ffe1e1
    style G fill:#e1ffe1
    style H fill:#e1ffe1
    style I fill:#e1ffe1
```

## 🔄 Fluxo Completo: Do GitHub ao Workflow

```mermaid
graph TB
    subgraph "Fase 1: Ingestão"
        A[GitHub Repository] -->|API| B[GitHub Ingestor]
        B -->|Extrai| C[n8n Workflows]
        C -->|Chunks| D[(ChromaDB)]
    end
    
    subgraph "Fase 2: Conhecimento"
        D -->|Processa| E[n8n Knowledge]
        E -->|Gera| F[Knowledge Files]
        E -->|Gera| G[Master Context]
    end
    
    subgraph "Fase 3: Composição"
        H[Usuário: objetivo] -->|Telegram| I[ComposerAgent]
        I -->|Busca| D
        I -->|Usa| G
        I -->|Cria| J[Workflow JSON]
    end
    
    subgraph "Fase 4: Uso"
        J -->|Importa| K[n8n Platform]
        K -->|Executa| L[Automação Ativa]
    end
    
    style A fill:#e1f5ff
    style D fill:#ffe1e1
    style F fill:#e1ffe1
    style G fill:#e1ffe1
    style J fill:#fff4e1
    style L fill:#e1ffe1
```

## 🎯 Fluxo de Decisão: Identificação de Componentes

```mermaid
graph TB
    A[Objetivo do usuário] -->|Analisa| B{Contém trigger<br/>keywords?}
    B -->|webhook, api| C1[Trigger: Webhook]
    B -->|schedule, cron| C2[Trigger: Schedule]
    B -->|telegram| C3[Trigger: Telegram]
    B -->|email| C4[Trigger: Email]
    B -->|Nenhum| C5[Trigger: Default<br/>mais comum dos templates]
    
    C1 --> D[Busca templates<br/>no ChromaDB]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    
    D -->|Filtra| E[Templates relevantes]
    E -->|Extrai| F[Processadores]
    
    A -->|Analisa output| G{Contém output<br/>keywords?}
    G -->|telegram| H1[Output: Telegram]
    G -->|email| H2[Output: Email]
    G -->|sheets| H3[Output: GoogleSheets]
    G -->|database| H4[Output: Database]
    G -->|Nenhum| H5[Output: HTTP<br/>default]
    
    F --> I[Componentes<br/>Identificados]
    H1 --> I
    H2 --> I
    H3 --> I
    H4 --> I
    H5 --> I
    
    I -->|Compõe| J[Workflow Final]
    
    style A fill:#e1f5ff
    style D fill:#ffe1e1
    style I fill:#fff4e1
    style J fill:#e1ffe1
```

## 🔐 Fluxo de Verificação do Sistema

```mermaid
graph TB
    A[verify_intelligence.py] -->|1. Verifica| B{Environment<br/>Variables?}
    B -->|OK| C[✅ GROQ_API_KEY]
    B -->|Falta| D[❌ Variáveis faltando]
    
    A -->|2. Verifica| E{ChromaDB<br/>Acessível?}
    E -->|OK| F[✅ ChromaDB OK]
    E -->|Erro| G[❌ ChromaDB inacessível]
    
    A -->|3. Verifica| H{Knowledge<br/>Files?}
    H -->|OK| I[✅ Arquivos OK]
    H -->|Falta| J[❌ Arquivos faltando]
    
    A -->|4. Verifica| K{ComposerAgent<br/>Funcional?}
    K -->|OK| L[✅ Agent OK]
    K -->|Erro| M[❌ Agent com erro]
    
    A -->|5. Verifica| N{Telegram<br/>Config?}
    N -->|OK| O[✅ Bot OK]
    N -->|Erro| P[❌ Bot não configurado]
    
    C --> Q[Resumo Final]
    D --> Q
    F --> Q
    G --> Q
    I --> Q
    J --> Q
    L --> Q
    M --> Q
    O --> Q
    P --> Q
    
    Q -->|Todos OK| R[🎯 Sistema Funcional]
    Q -->|Algum erro| S[⚠️ Ações Recomendadas]
    
    style A fill:#e1f5ff
    style R fill:#e1ffe1
    style S fill:#ffe1e1
```

## 🚀 Fluxo de Setup Automatizado

```mermaid
graph TB
    A[setup_intelligence.py] -->|1| B[Check Environment]
    B -->|2| C[Verify ChromaDB]
    C -->|3| D{Skip Ingestion?}
    D -->|Não| E[Run Ingestion<br/>zie619 repo]
    D -->|Sim| F[Use existing data]
    E --> G[Generate Knowledge]
    F --> G
    G -->|4| H[n8n_capabilities.md]
    G -->|5| I[n8n_recipes.md]
    G -->|6| J[n8n_master_context.json]
    H --> K{Test Composer?}
    I --> K
    J --> K
    K -->|Sim| L[Test ComposerAgent]
    K -->|Não| M[Skip test]
    L --> N[Final Summary]
    M --> N
    N -->|Sucesso| O[🎯 Setup Complete!<br/>Next steps:<br/>1. Start bot<br/>2. Use /create_n8n]
    N -->|Erro| P[❌ Setup Failed<br/>Check logs]
    
    style A fill:#e1f5ff
    style O fill:#e1ffe1
    style P fill:#ffe1e1
```

## 📱 Fluxo de Interação via Telegram

```mermaid
sequenceDiagram
    participant U as Usuário
    participant T as Telegram Bot
    participant H as Handler
    participant C as ComposerAgent
    participant D as ChromaDB
    participant F as FileSystem
    
    U->>T: /create_n8n Webhook para Telegram
    T->>H: Recebe comando
    H->>H: Parse comando e args
    H->>T: Envia "Digitando..."
    H->>C: compose_workflow(objetivo)
    C->>D: Busca templates relevantes
    D-->>C: Retorna templates
    C->>C: Identifica componentes
    C->>C: Compõe workflow
    C->>C: Valida JSON
    C->>F: Salva workflow.json
    F-->>C: Caminho do arquivo
    C-->>H: Resultado completo
    H->>T: Formata resposta
    T->>U: ✅ Workflow criado!<br/>📁 Arquivo: ...<br/>🔧 Templates: ...
```

## 🔄 Ciclo de Vida de um Workflow

```mermaid
stateDiagram-v2
    [*] --> Objetivo: Usuário define objetivo
    Objetivo --> Busca: ComposerAgent busca templates
    Busca --> Análise: Analisa templates relevantes
    Análise --> Composição: Identifica componentes
    Composição --> Validação: Compõe JSON n8n
    Validação --> Salvo: Valida estrutura
    Salvo --> Importado: Salva em filesystem
    Importado --> Configurado: Usuário importa no n8n
    Configurado --> Ativo: Configura credenciais
    Ativo --> Executando: Ativa workflow
    Executando --> [*]: Automação rodando
    
    Validação --> Erro: JSON inválido
    Erro --> Composição: Tenta novamente
```

---

## 📚 Legenda de Cores

- 🔵 **Azul claro** (#e1f5ff): Entrada do usuário / Início
- 🔴 **Vermelho claro** (#ffe1e1): Armazenamento / Banco de dados
- 🟢 **Verde claro** (#e1ffe1): Saída / Resultado final
- 🟡 **Amarelo claro** (#fff4e1): Processamento / Transformação

---

**Última atualização:** 2026-03-03
**Autor:** Hugo (Bunker Intelligence Team)
