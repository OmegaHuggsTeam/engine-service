# [Nome da Skill] - Especificação Técnica

## 📋 Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | [Nome da Skill] |
| **Categoria** | [Data / Communication / Automation / Analysis / Infrastructure] |
| **Versão** | 1.0.0 |
| **Status** | [Active / Development / Deprecated] |
| **Prioridade** | [Alta / Média / Baixa] |
| **Módulo** | `src.skills.[nome_modulo]` ou `superpowers.[nome]` |
| **Criado em** | YYYY-MM-DD |
| **Última Atualização** | YYYY-MM-DD |

---

## 🎯 Objetivo

[Descrição concisa do que a skill faz em 2-3 frases]

### Problema que Resolve
[Qual problema específico esta skill resolve?]

### Valor Agregado
[Qual valor esta skill traz para o sistema?]

---

## 🤖 Agentes que Utilizam

| Agente | Uso | Frequência |
|--------|-----|------------|
| **[Nome do Agente]** | [Como usa] | [Alta/Média/Baixa] |
| **[Nome do Agente]** | [Como usa] | [Alta/Média/Baixa] |

---

## 📥 Interface

### Input

```python
# Tipo de input esperado
{
    "param1": "tipo - descrição",
    "param2": "tipo - descrição",
    "options": {
        "option1": "valor padrão",
        "option2": "valor padrão"
    }
}
```

### Output

```python
# Tipo de output retornado
{
    "status": "success | error",
    "data": {
        "result1": "tipo - descrição",
        "result2": "tipo - descrição"
    },
    "metadata": {
        "execution_time_ms": 1234,
        "items_processed": 10
    },
    "errors": []  # Lista de erros se status == "error"
}
```

### Exceções

| Exceção | Quando Ocorre | Como Tratar |
|---------|---------------|-------------|
| `[NomeExcecao]` | [Condição] | [Ação recomendada] |

---

## 🔧 Implementação

### Tecnologias Utilizadas
- **[Tecnologia 1]**: [Para que serve]
- **[Tecnologia 2]**: [Para que serve]

### Dependências
```txt
biblioteca1>=1.0.0
biblioteca2>=2.0.0
```

### Variáveis de Ambiente
```bash
SKILL_CONFIG_VAR1=valor
SKILL_CONFIG_VAR2=valor
```

### Estrutura de Código

```python
# Exemplo de implementação
class [NomeDaSkill]:
    def __init__(self, config: dict):
        self.config = config

    def execute(self, input_data: dict) -> dict:
        """
        Executa a skill.

        Args:
            input_data: Dados de entrada

        Returns:
            Resultado da execução
        """
        # Implementação
        pass
```

---

## 📊 Métricas

### KPIs
- **Success Rate**: > X%
- **Execution Time**: < Xs (p95)
- **Throughput**: > X items/segundo
- **Error Rate**: < X%

### Monitoramento
```python
{
  "skill": "[nome_skill]",
  "timestamp": "2026-03-03T10:00:00Z",
  "metrics": {
    "success_rate": 0.95,
    "avg_execution_time_ms": 1234,
    "items_processed": 100,
    "error_rate": 0.05
  }
}
```

---

## 🧪 Testes

### Casos de Teste

1. **Teste de Sucesso**
   - Input: [exemplo]
   - Output esperado: [exemplo]
   - Validação: [critério]

2. **Teste de Erro**
   - Input: [exemplo inválido]
   - Output esperado: [erro específico]
   - Validação: [critério]

3. **Teste de Performance**
   - Input: [volume grande]
   - Output esperado: [resultado em tempo aceitável]
   - Validação: [tempo < threshold]

### Comandos de Teste
```bash
# Testes unitários
pytest tests/skills/test_[nome_skill].py -v

# Teste manual
python -c "
from src.skills.[nome_modulo] import [NomeDaSkill]
skill = [NomeDaSkill](config={})
result = skill.execute({'param1': 'valor'})
print(result)
"
```

---

## 🔄 Integração

### Como Usar em Agentes

```python
# Exemplo de uso em um agente
from src.skills.[nome_modulo] import [NomeDaSkill]

class MeuAgente:
    def __init__(self):
        self.skill = [NomeDaSkill](config={})

    def processar(self, dados):
        resultado = self.skill.execute(dados)
        return resultado
```

### Como Usar em Workflows n8n

```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.function",
      "name": "[Nome da Skill]",
      "parameters": {
        "functionCode": "// Código que invoca a skill via API"
      }
    }
  ]
}
```

---

## 🐛 Troubleshooting

### Problema Comum 1
- **Sintoma**: [Descrição]
- **Causa**: [Explicação]
- **Solução**: [Passos]

### Problema Comum 2
- **Sintoma**: [Descrição]
- **Causa**: [Explicação]
- **Solução**: [Passos]

---

## 🗺️ Roadmap

### Versão Atual (1.0.0)
- ✅ Feature 1
- ✅ Feature 2

### Próxima Versão (1.1.0)
- ⏳ Feature 3
- ⏳ Feature 4

### Futuro (2.0.0)
- 💡 Feature 5
- 💡 Feature 6

---

## 📚 Referências

- [Link para documentação relacionada]
- [Link para código fonte]
- [Link para exemplos]

---

**Mantido por**: [Nome do time/pessoa]
**Última Revisão**: YYYY-MM-DD
