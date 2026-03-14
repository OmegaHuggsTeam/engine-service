# Matrix Map - Dicionário de Transição de Componentes

## Visão Geral

O Matrix Map é um sistema de navegação dimensional que mapeia o DOM como "zonas" (zones) interconectadas. Cada zona representa um componente ou região da aplicação web, com pontos de entrada e saída bem definidos.

Em vez de navegar cegamente pelo DOM com `driver.get()` ou `driver.find_element()`, o Selum usa o Matrix Map para:
- **Identificar zonas** por seletores únicos
- **Saltar entre zonas** com `leap_to(zone_name)`
- **Rastrear profundidade** (depth) para lidar com iframes e shadow DOM
- **Mapear transições** entre componentes

## Conceitos Fundamentais

### 1. Zonas (Zones)

Uma zona é um componente ou região do DOM com:
- **Nome único**: Identificador da zona (ex: `GMAIL_INBOX`)
- **Selector**: Seletor CSS/XPath que identifica a zona
- **Depth**: Profundidade no DOM (0 = página principal, 1+ = iframe/shadow DOM)
- **Exits**: Lista de zonas acessíveis a partir desta zona
- **Entry Actions**: Ações necessárias para entrar na zona (opcional)
- **Markers**: Elementos âncora para validar que estamos na zona correta

### 2. Leap Actions (Ações de Salto)

Ações que permitem transição entre zonas:
- **leap_to(zone_name)**: Salta para uma zona específica
- **dimensional_shift()**: Muda contexto para iframe/shadow DOM
- **focus_zone()**: Injeta foco visual (debug) na zona atual
- **validate_zone()**: Confirma que estamos na zona esperada

### 3. Dimensional Depth (Profundidade Dimensional)

Níveis de profundidade no DOM:
- **Depth 0**: Página principal (document)
- **Depth 1**: Primeiro nível de iframe
- **Depth 2+**: Iframes aninhados ou shadow DOM

## Estrutura do Matrix Map

```python
MATRIX_MAP = {
    "ZONE_NAME": {
        "selector": "css_or_xpath_selector",
        "depth": 0,  # 0 = main document, 1+ = iframe/shadow
        "exits": ["ZONE_A", "ZONE_B"],  # Zonas acessíveis
        "entry_action": "optional_action",  # Como entrar na zona
        "markers": ["anchor_selector_1", "anchor_selector_2"],  # Validação
        "description": "Descrição da zona"
    }
}
```

## Exemplo: Gmail Navigation

```python
MATRIX_MAP = {
    # Zona Alpha: Login
    "GMAIL_LOGIN": {
        "selector": "form#identifierForm",
        "depth": 0,
        "exits": ["GMAIL_PASSWORD", "GMAIL_2FA"],
        "entry_action": "navigate_to_url",
        "markers": ["input[type='email']", "button#identifierNext"],
        "description": "Página de login do Gmail (email)"
    },

    # Zona Beta: Password
    "GMAIL_PASSWORD": {
        "selector": "form#passwordForm",
        "depth": 0,
        "exits": ["GMAIL_INBOX", "GMAIL_2FA"],
        "entry_action": "submit_email",
        "markers": ["input[type='password']", "button#passwordNext"],
        "description": "Página de senha do Gmail"
    },

    # Zona Gamma: 2FA Challenge
    "GMAIL_2FA": {
        "selector": "div#totpPin",
        "depth": 0,
        "exits": ["GMAIL_INBOX"],
        "entry_action": "submit_password",
        "markers": ["input#totpPin", "button#submit"],
        "description": "Desafio de autenticação de dois fatores"
    },

    # Zona Delta: Inbox
    "GMAIL_INBOX": {
        "selector": "div.inbox-container",
        "depth": 0,
        "exits": ["MESSAGE_VIEW", "SETTINGS_MODAL", "COMPOSE_EMAIL"],
        "entry_action": "complete_login",
        "markers": ["div.aeF", "button[gh='cm']"],
        "description": "Caixa de entrada do Gmail"
    },

    # Zona Epsilon: Message View
    "MESSAGE_VIEW": {
        "selector": "div.message-container",
        "depth": 0,
        "exits": ["GMAIL_INBOX", "REPLY_COMPOSE"],
        "entry_action": "click_message",
        "markers": ["div.message-body", "button.reply"],
        "description": "Visualização de mensagem individual"
    },

    # Zona Zeta: Settings Modal (Iframe)
    "SETTINGS_MODAL": {
        "selector": "iframe#settings-frame",
        "depth": 1,
        "exits": ["GMAIL_INBOX"],
        "entry_action": "click_settings_icon",
        "markers": ["div.settings-content", "button.save-settings"],
        "description": "Modal de configurações (dentro de iframe)"
    }
}
```

## Exemplo: Groq API Dashboard

```python
MATRIX_MAP = {
    # Zona Alpha: Login
    "GROQ_LOGIN": {
        "selector": "form.login-form",
        "depth": 0,
        "exits": ["GROQ_DASHBOARD", "GROQ_OAUTH"],
        "entry_action": "navigate_to_url",
        "markers": ["input#email", "button.login-btn"],
        "description": "Página de login da Groq API"
    },

    # Zona Beta: OAuth Challenge (Iframe)
    "GROQ_OAUTH": {
        "selector": "iframe#oauth-frame",
        "depth": 1,
        "exits": ["GROQ_DASHBOARD"],
        "entry_action": "click_oauth_provider",
        "markers": ["form#identifier-form", "button#submit"],
        "description": "Desafio OAuth em iframe"
    },

    # Zona Gamma: Dashboard
    "GROQ_DASHBOARD": {
        "selector": "div.dashboard-container",
        "depth": 0,
        "exits": ["API_KEYS", "USAGE_STATS", "SETTINGS"],
        "entry_action": "complete_login",
        "markers": ["nav.sidebar", "div.main-content"],
        "description": "Dashboard principal da Groq API"
    },

    # Zona Delta: API Keys
    "API_KEYS": {
        "selector": "div.api-keys-section",
        "depth": 0,
        "exits": ["GROQ_DASHBOARD", "CREATE_KEY_MODAL"],
        "entry_action": "click_api_keys_menu",
        "markers": ["table.keys-table", "button.create-key"],
        "description": "Seção de gerenciamento de API keys"
    },

    # Zona Epsilon: Create Key Modal (Shadow DOM)
    "CREATE_KEY_MODAL": {
        "selector": "modal-component::shadow div.modal",
        "depth": 2,
        "exits": ["API_KEYS"],
        "entry_action": "click_create_key_button",
        "markers": ["input.key-name", "button.generate"],
        "description": "Modal de criação de API key (shadow DOM)"
    }
}
```

## Uso das Leap Actions

### leap_to(zone_name)

Salta para uma zona específica, executando todas as ações necessárias:

```python
# Exemplo: Saltar para inbox do Gmail
selum.leap_to("GMAIL_INBOX")

# Internamente, o Selum:
# 1. Verifica se já está na zona (validate_zone)
# 2. Se não, encontra o caminho mais curto no grafo de zonas
# 3. Executa entry_actions de cada zona intermediária
# 4. Faz dimensional_shift se depth mudar
# 5. Valida chegada com markers
```

### dimensional_shift(target_depth)

Muda contexto para iframe ou shadow DOM:

```python
# Exemplo: Entrar em iframe de settings
selum.dimensional_shift(depth=1, selector="iframe#settings-frame")

# Internamente:
# 1. Localiza iframe/shadow root
# 2. Executa driver.switch_to.frame() ou acessa shadowRoot
# 3. Atualiza mapa mental com novo contexto
# 4. Injeta marcador visual (debug mode)
```

### focus_zone(zone_name, debug=True)

Injeta foco visual na zona atual (útil para debug):

```python
# Exemplo: Destacar zona atual
selum.focus_zone("GMAIL_INBOX", debug=True)

# Internamente:
# 1. Localiza elemento da zona
# 2. Injeta CSS com contorno neon
# 3. Faz scroll suave até o elemento
# 4. Loga coordenadas e dimensões
```

### validate_zone(zone_name)

Confirma que estamos na zona esperada:

```python
# Exemplo: Validar que estamos no inbox
is_valid = selum.validate_zone("GMAIL_INBOX")

# Internamente:
# 1. Verifica presença de markers
# 2. Valida depth atual
# 3. Confirma selector principal
# 4. Retorna True/False
```

## Integração com RAG

O Matrix Map é indexado pelo RAG e pode ser consultado dinamicamente:

```python
# Exemplo: Consultar zonas disponíveis
zones = rag.query("zonas gmail inbox", top_k=5)

# Exemplo: Encontrar caminho entre zonas
path = rag.query("caminho de login para api keys groq", top_k=1)
```

## Regras de Segurança

1. **Validação Obrigatória**: Sempre validar zona antes de executar ações
2. **Depth Tracking**: Sempre rastrear profundidade atual para evitar contexto perdido
3. **Rollback em Falha**: Se leap_to falhar, retornar à zona anterior
4. **Timeout por Zona**: Cada zona tem timeout máximo (padrão: 30s)
5. **Markers Redundantes**: Sempre ter 2+ markers para validação robusta

## Extensibilidade

Para adicionar novas zonas ao Matrix Map:

1. **Identificar componente**: Encontrar selector único
2. **Mapear transições**: Definir exits possíveis
3. **Testar profundidade**: Verificar se está em iframe/shadow DOM
4. **Definir markers**: Escolher 2-3 elementos âncora
5. **Documentar entry_action**: Descrever como entrar na zona
6. **Adicionar ao MATRIX_MAP**: Seguir estrutura padrão
7. **Re-indexar RAG**: Executar `rag.re_index()` para atualizar índice

## Exemplo Completo: Navegação Gmail

```python
# Inicializar Selum com Matrix Map
selum = SelumOfPersistence(driver, matrix_map=MATRIX_MAP)

# Fluxo completo de login
selum.leap_to("GMAIL_LOGIN")
selum.strike("input[type='email']", text="user@example.com")
selum.strike("button#identifierNext")

selum.leap_to("GMAIL_PASSWORD")
selum.strike("input[type='password']", text="password123")
selum.strike("button#passwordNext")

# Se 2FA aparecer
if selum.validate_zone("GMAIL_2FA"):
    selum.strike("input#totpPin", text="123456")
    selum.strike("button#submit")

# Navegar para inbox
selum.leap_to("GMAIL_INBOX")

# Abrir primeira mensagem
messages = selum.scout([{"css": "div.message-item"}])
selum.strike(messages[0])

# Validar que estamos na zona correta
assert selum.validate_zone("MESSAGE_VIEW")
```

## Notas de Implementação

- O Matrix Map deve ser carregado na inicialização do Selum
- Zonas podem ser adicionadas dinamicamente via `selum.register_zone()`
- O grafo de zonas é usado para pathfinding (algoritmo de Dijkstra)
- Dimensional shifts são rastreados em uma pilha (stack) para rollback
- Debug mode injeta contornos coloridos em cada zona visitada
- Logs narrativos descrevem cada salto: "Saltando de GMAIL_LOGIN para GMAIL_PASSWORD..."

## Próximos Passos

1. Implementar `leap_to()` no SelumOfPersistence
2. Criar `MatrixNavigator` para gerenciar transições
3. Adicionar validação de zonas com markers
4. Implementar dimensional_shift para iframes
5. Integrar com RAG para consultas dinâmicas
6. Criar testes de navegação entre zonas
