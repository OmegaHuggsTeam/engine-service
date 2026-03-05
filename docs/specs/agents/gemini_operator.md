# Gemini Operator - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | GeminiOperator |
| **Tipo** | Operator |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `automation_hub.agents.gemini_operator` |

---

## Funcao Core

O GeminiOperator e o provedor de inferencia multimodal do sistema, utilizando a API Google Gemini para processamento de texto, imagens e contextos longos. Serve como alternativa ao Groq para tarefas que requerem capacidades multimodais.

### Responsabilidades
- Executar inferencia multimodal (texto + imagem) via Gemini API
- Processar documentos longos com janela de contexto estendida
- Analisar screenshots e imagens para computer use tasks
- Servir como fallback quando Groq esta indisponivel
- Processar tarefas que excedem o contexto maximo do Groq

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| llm_inference | Inferencia LLM via Google Gemini |
| multimodal | Processamento combinado de texto e imagens |
| long_context | Suporte a contextos extensos (1M+ tokens) |

---

## Inicializacao

- **Pattern**: No-arg
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: N/A (operator, nao baseado em conhecimento)

## Integracao

- **UseCase Coverage**: Transversal (fallback multimodal)
- **Depends On**: Google Gemini API, GEMINI_API_KEY
- **Used By**: ComputerUseAgent (screenshots), llm_client.py (fallback)

## Testes

- **Test File**: `tests/test_gemini_operator.py`
- **Coverage**: Unit tests para inference e multimodal processing
