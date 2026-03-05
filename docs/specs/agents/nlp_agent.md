# NLP Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | NlpAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O NlpAgent e especialista em processamento de linguagem natural, realizando classificacao de texto, analise de sentimento e extracao de entidades. Fornece capacidades NLP para outros agentes que necessitam de compreensao textual avancada.

### Responsabilidades
- Classificar textos por intencao, topico e categoria
- Analisar sentimento em mensagens de leads e interacoes
- Extrair entidades nomeadas (pessoas, empresas, produtos)
- Processar e normalizar texto para pipelines downstream
- Detectar idioma e traduzir conteudo quando necessario

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| nlp | Processamento de linguagem natural geral |
| text_classification | Classificacao de texto por intencao e topico |
| sentiment_analysis | Analise de sentimento (positivo, neutro, negativo) |
| entity_extraction | Extracao de entidades nomeadas (NER) |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="nlp", **kwargs)`
- **Knowledge Categories**: nlp, text_classification, sentiment, ner

## Integracao

- **UseCase Coverage**: Transversal (compreensao textual)
- **Depends On**: GroqOperator (LLM inference), sentence-transformers (embeddings)
- **Used By**: CrmBackendAgent (lead classification), SocialMediaAgent (sentiment)

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
