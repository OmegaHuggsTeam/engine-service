# 🛡️ Selum of Persistence - Guia do Paladino

## Visão Geral

**Selum of Persistence** (também conhecido como **Moltor, o Paladino**) é uma camada de abstração sobre Selenium que transforma operações técnicas em "manobras de combate" narrativas e resilientes.

Cada interação com o DOM é tratada como um turno de combate, com logs narrativos que contam a história do que aconteceu. Quando uma manobra falha, o Paladino invoca a "sabedoria dos Anciões" (AgentFactory) para aprender e evoluir.

## 🎯 Características Principais

- ⚔️ **Cliques Resilientes**: Fallback automático para JS click quando necessário
- 🔍 **Reconhecimento Multi-Seletor**: Busca múltiplos seletores/idiomas
- 👁️ **Espera Inteligente**: Logs de progresso durante waits
- ✨ **Limpeza Automática**: Remove overlays e modais
- 🎯 **Scroll Inteligente**: Garante visibilidade antes de interagir
- 🧙 **Aprendizado Contínuo**: Integração com AgentFactory
- 📖 **Logs Narrativos**: Cada ação conta uma história

## 🚀 Instalação

O Selum já está incluído no projeto. Certifique-se de ter o Selenium instalado:

```bash
pip install selenium>=4.0.0
```

## 📚 Uso Básico

### Inicialização

```python
from selenium import webdriver
from src.utils.selum_of_persistence import SelumOfPersistence

# Criar WebDriver
driver = webdriver.Chrome()

# Inicializar o Paladino
selum = SelumOfPersistence(driver)
```

### Strike (Clique Resiliente)

```python
# Clique com fallback automático (estratégia 'smart')
selum.strike(".settings-button")

# Forçar JS click direto
selum.strike(".settings-button", strategy='force')

# Apenas clique normal (sem fallback)
selum.strike(".settings-button", strategy='gentle')
```

**Output:**
```
[Turno 1 - Selum of Persistence]: Empunhando 'strike' contra '.settings-button'...
[Resultado]: ✓ Golpe certeiro! O caminho está livre.
```

### Scout (Reconhecimento Multi-Seletor)

```python
# Buscar elemento com múltiplas possibilidades
element = selum.scout([
    {"text": "Definições"},
    {"text": "Settings"},
    {"text": "Configuración"},
    {"css": ".settings-btn"},
    {"xpath": "//button[@id='settings']"}
])

if element:
    selum.strike(element)
```

**Output:**
```
[Turno 2 - Selum of Persistence]: Farejando trilhas em busca de 5 caminhos...
[Resultado]: ✓ Caminho seguro encontrado: text='Settings'
```

### Vigilance (Espera Inteligente)

```python
# Aguardar elemento aparecer (com logs de progresso)
element = selum.vigilance(".api-key-field", timeout=30)
```

**Output:**
```
[Turno 3 - Selum of Persistence]: Em vigília constante aguardando '.api-key-field'...
[Progresso]: Ainda em vigília... (5s de 30s)
[Progresso]: Ainda em vigília... (10s de 30s)
[Resultado]: ✓ Brecha na armadura do DOM detectada!
```

### Cleansing Aura (Limpeza de Obstáculos)

```python
# Remover overlays, modais e pop-ups
removed = selum.cleansing_aura()
print(f"Removidos: {removed} obstáculos")
```

**Output:**
```
[Turno 4 - Selum of Persistence]: Invocando Aura de Limpeza...
[Resultado]: ✓ 2 névoas dissipadas!
```

### Steady Gaze (Scroll Inteligente)

```python
# Scroll até elemento para garantir visibilidade
element = selum.steady_gaze(".hidden-button")
```

**Output:**
```
[Turno 5 - Selum of Persistence]: Fixando o olhar em '.hidden-button'...
[Resultado]: ✓ Alvo em foco!
```

## 🎮 Exemplo Completo

```python
from selenium import webdriver
from src.utils.selum_of_persistence import SelumOfPersistence

# Inicializar
driver = webdriver.Chrome()
selum = SelumOfPersistence(driver)

try:
    # Navegar
    driver.get("https://example.com")
    
    # Limpar obstáculos
    selum.cleansing_aura()
    
    # Buscar botão de configurações (multi-idioma)
    settings_btn = selum.scout([
        {"text": "Definições"},
        {"text": "Settings"},
        {"text": "Configuración"}
    ])
    
    if settings_btn:
        # Focar no botão
        selum.steady_gaze(settings_btn)
        
        # Clicar com resiliência
        selum.strike(settings_btn, strategy='smart')
    
    # Aguardar campo de API key aparecer
    api_field = selum.vigilance("#api-key", timeout=20)
    
    # Obter relatório de batalha
    report = selum.get_battle_report()
    print(f"\nTotal de turnos: {len(report)}")
    
finally:
    driver.quit()
```

## 📊 Relatório de Batalha

O Paladino mantém um histórico de todas as ações:

```python
# Obter relatório
report = selum.get_battle_report()

# Cada entrada contém:
for action in report:
    print(f"Turno {action['turn']}: {action['action']}")
    print(f"  Alvo: {action['target']}")
    print(f"  Resultado: {action['result']}")
    print(f"  Sucesso: {action['success']}")
    print(f"  Timestamp: {action['timestamp']}")
```

## 🧙 Integração com AgentFactory

Quando uma manobra falha, o Paladino automaticamente invoca o AgentFactory para análise:

```python
try:
    selum.strike(".non-existent-element")
except Exception as e:
    # O Paladino já invocou invoke_wisdom() automaticamente
    # O grimório (selenium.md) será atualizado com nova estratégia
    pass
```

**Output:**
```
[Turno 6 - Selum of Persistence]: Invocando a sabedoria dos Anciões...
[Sabedoria Ancestral]: Use scout() para múltiplos seletores
```

## 📖 Grimório (selenium.md)

O Paladino mantém um grimório de conhecimento em `src/agents/specs/selenium.md` com:

- Padrões de erro comuns
- Manobras de combate aprendidas
- Histórico de evolução
- Estratégias de prevenção

O grimório é atualizado automaticamente quando novas estratégias são aprendidas.

## 🎯 Estratégias de Clique

### Smart (Padrão)
Tenta clique normal primeiro, usa JS click se falhar.

```python
selum.strike(".button", strategy='smart')
```

### Force
Usa JS click direto (mais rápido, mas menos "natural").

```python
selum.strike(".button", strategy='force')
```

### Gentle
Apenas clique normal, sem fallback (falha se interceptado).

```python
selum.strike(".button", strategy='gentle')
```

## 🔍 Formatos de Scout

O scout aceita vários formatos de seletor:

```python
possibilities = [
    # Por texto (link)
    {"text": "Settings", "type": "link"},
    
    # Por texto (qualquer elemento)
    {"text": "Settings"},
    
    # Por texto parcial
    {"text": "Sett", "type": "partial"},
    
    # Por CSS
    {"css": ".settings-btn"},
    
    # Por XPath
    {"xpath": "//button[@id='settings']"},
    
    # Por ID
    {"id": "settings-button"},
    
    # Por Name
    {"name": "settings"}
]

element = selum.scout(possibilities)
```

## ⚠️ Boas Práticas

1. **Use scout() para elementos multi-idioma**
   ```python
   element = selum.scout([
       {"text": "Definições"},
       {"text": "Settings"}
   ])
   ```

2. **Limpe obstáculos antes de interações críticas**
   ```python
   selum.cleansing_aura()
   selum.strike(".important-button")
   ```

3. **Use steady_gaze() para elementos fora do viewport**
   ```python
   element = selum.steady_gaze(".footer-button")
   selum.strike(element)
   ```

4. **Use vigilance() para conteúdo dinâmico**
   ```python
   element = selum.vigilance(".dynamic-content", timeout=30)
   ```

5. **Revise o relatório de batalha para debugging**
   ```python
   report = selum.get_battle_report()
   for action in report:
       if not action['success']:
           print(f"Falha: {action}")
   ```

## 🐛 Debugging

### Logs Detalhados

Todos os logs são automáticos e narrativos:

```
[Turno 1 - Selum of Persistence]: Empunhando 'strike' contra '.button'...
[Aviso]: Bloqueado! Usando Injeção de Força...
[Resultado]: ✓ Injeção de Força bem-sucedida! O caminho está livre.
```

### Relatório de Batalha

```python
# Ver todas as ações
report = selum.get_battle_report()

# Filtrar apenas falhas
failures = [a for a in report if not a['success']]
print(f"Falhas: {len(failures)}")
```

### Grimório

Consulte `src/agents/specs/selenium.md` para ver:
- Padrões de erro conhecidos
- Manobras aprendidas
- Histórico de evolução

## 🔮 Funcionalidades Futuras

- **Combos**: Sequências pré-definidas (ex: `combo_login()`)
- **Estatísticas**: Métricas de sucesso por manobra
- **Estratégias Adaptativas**: Ajuste automático de timeouts
- **Multi-Paladino**: Múltiplos Paladinos coordenados

## 📝 Contribuindo

Para adicionar novas manobras ao Paladino:

1. Adicione o método em `src/utils/selum_of_persistence.py`
2. Use `_increment_turn()` e `CombatLogger`
3. Adicione a manobra ao grimório (`selenium.md`)
4. Crie testes em `tests/unit/`

## 🏆 Filosofia

> "Que Selum of Persistence guie nossos cliques através das trevas do DOM!" ⚔️🛡️

O Paladino transforma Selenium de uma ferramenta técnica em uma narrativa épica, onde cada interação é um turno de combate e cada falha é uma oportunidade de aprendizado.

---

**Criado por:** Hugo (Planejamento) + Kiro (Implementação)  
**Versão:** 1.0.0  
**Data:** 2024-01-01
