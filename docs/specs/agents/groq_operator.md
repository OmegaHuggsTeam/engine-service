# Groq Operator - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | GroqOperator |
| **Tipo** | Operator |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `automation_hub.agents.groq_operator` |

---

## Funcao Core

O GroqOperator e o provedor principal de inferencia LLM do sistema, utilizando a API Groq para execucao rapida de modelos Llama. Suporta function calling para automacao e e o backend padrao de todos os agentes via llm_client.

### Responsabilidades
- Executar inferencia LLM via Groq API (llama-3.3-70b-versatile, llama-3.1-8b-instant)
- Processar function calling para automacao de tarefas
- Gerenciar rate limiting e cooldown de API keys (429 handling)
- Rotear entre modelos por tier (8b para triage, 70b para geracao)
- Fornecer fallback para outros operadores em caso de indisponibilidade

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| llm_inference | Inferencia LLM com baixa latencia via Groq |
| function_calling | Chamada de funcoes estruturadas via LLM |
| automation | Automacao de tarefas via function calling |

---

## Inicializacao

- **Pattern**: No-arg
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: N/A (operator, nao baseado em conhecimento)

## Integracao

- **UseCase Coverage**: Transversal (usado por todos os agentes)
- **Depends On**: Groq API, KeyManager (SecretVault)
- **Used By**: Todos os agentes via llm_client.py, GroqRouter middleware

## Testes

- **Test File**: `tests/test_groq_operator.py`
- **Coverage**: Unit tests para inference, function calling, rate limiting
