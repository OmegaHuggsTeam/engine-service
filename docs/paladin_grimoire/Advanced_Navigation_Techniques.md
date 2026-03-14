# Advanced Navigation Techniques - Técnicas Avançadas de Navegação

## Visão Geral

Este documento descreve técnicas avançadas para navegar em aplicações web modernas que usam Shadow DOM, iframes aninhados, e componentes encapsulados. Estas técnicas vão além do Selenium tradicional e permitem ao Selum acessar elementos "invisíveis" para seletores comuns.

## 1. Shadow DOM Navigation (O Mapa das Sombras)

### Problema

Componentes modernos (Web Components) são encapsulados em `shadow-root`. O Selenium não consegue "ver" dentro deles com seletores CSS/XPath comuns:

```python
# ❌ Isso NÃO funciona com Shadow DOM
element = driver.find_element(By.CSS_SELECTOR, "custom-button::shadow .inner-button")
```

### Solução: Shadow Root Injection

Use JavaScript para acessar `element.shadowRoot` e navegar dentro dele:

```python
def pierce_shadow_dom(driver, host_selector, inner_selector):
    """
    Penetra Shadow DOM e retorna elemento interno.

    Args:
        driver: WebDriver instance
        host_selector: Seletor do elemento host (que contém shadowRoot)
        inner_selector: Seletor do elemento dentro do shadowRoot

    Returns:
        WebElement dentro do Shadow DOM
    """
    script = """
    const host = document.querySelector(arguments[0]);
    if (!host || !host.shadowRoot) {
        return null;
    }
    return host.shadowRoot.querySelector(arguments[1]);
    """
    return driver.execute_script(script, host_selector, inner_selector)
```

### Exemplo: Acessar Botão em Shadow DOM

```python
# Estrutura HTML:
# <custom-component>
#   #shadow-root
#     <button class="confirm-btn">Confirm</button>
# </custom-component>

# Acessar botão dentro do shadow root
button = pierce_shadow_dom(
    driver,
    host_selector="custom-component",
    inner_selector="button.confirm-btn"
)
button.click()
```

### Shadow DOM Aninhado (Nested Shadow Roots)

Para Shadow DOM aninhado, use navegação recursiva:

```python
def pierce_nested_shadow_dom(driver, path):
    """
    Navega por múltiplos níveis de Shadow DOM.

    Args:
        driver: WebDriver instance
        path: Lista de tuplas (host_selector, inner_selector)

    Returns:
        WebElement no nível mais profundo

    Example:
        path = [
            ("custom-app", "custom-dialog"),
            ("custom-dialog", "button.confirm")
        ]
    """
    script = """
    let current = document;
    const path = arguments[0];

    for (let i = 0; i < path.length; i++) {
        const [hostSelector, innerSelector] = path[i];
        const host = current.querySelector(hostSelector);

        if (!host) return null;

        if (i < path.length - 1) {
            // Não é o último nível, entrar no shadowRoot
            if (!host.shadowRoot) return null;
            current = host.shadowRoot;
        } else {
            // Último nível, buscar elemento final
            if (host.shadowRoot) {
                return host.shadowRoot.querySelector(innerSelector);
            } else {
                return host.querySelector(innerSelector);
            }
        }
    }
    return null;
    """
    return driver.execute_script(script, path)
```

### Direct Routing: Extrair Links de Navegação

Em vez de clicar em botões dentro de Shadow DOM, extraia o link de navegação diretamente:

```python
def extract_navigation_link(driver, host_selector):
    """
    Extrai link de navegação de dentro de Shadow DOM.

    Args:
        driver: WebDriver instance
        host_selector: Seletor do componente host

    Returns:
        URL de navegação ou None
    """
    script = """
    const host = document.querySelector(arguments[0]);
    if (!host || !host.shadowRoot) return null;

    // Procurar por links ou botões com href/data-href
    const link = host.shadowRoot.querySelector('a[href], button[data-href]');
    if (!link) return null;

    return link.href || link.getAttribute('data-href');
    """
    url = driver.execute_script(script, host_selector)

    if url:
        driver.get(url)  # Navegar diretamente
        return url
    return None
```

## 2. Accessibility Tree Navigation (AXTree)

### Problema

O DOM pode ser um caos de `<div>` anônimos sem IDs ou classes estáveis. Mas a **Accessibility Tree** (usada por leitores de tela) é limpa e semântica.

### Vantagem

O Google raramente muda os atributos de acessibilidade (role, name, label) porque isso quebraria o site para deficientes visuais. Isso torna a AXTree mais estável que seletores CSS.

### Solução: Chrome DevTools Protocol (CDP)

Use CDP para acessar a Accessibility Tree:

```python
def find_by_accessibility_role(driver, role, name=None):
    """
    Encontra elemento por role de acessibilidade.

    Args:
        driver: WebDriver instance
        role: Role ARIA (ex: 'button', 'link', 'textbox')
        name: Nome acessível do elemento (opcional)

    Returns:
        WebElement ou None

    Example:
        button = find_by_accessibility_role(driver, 'button', 'Confirm')
    """
    # Habilitar CDP
    driver.execute_cdp_cmd('Accessibility.enable', {})

    # Obter Accessibility Tree
    ax_tree = driver.execute_cdp_cmd('Accessibility.getFullAXTree', {})

    # Procurar nó com role e name
    for node in ax_tree['nodes']:
        if node.get('role', {}).get('value') == role:
            if name is None or node.get('name', {}).get('value') == name:
                # Obter backend node ID
                backend_node_id = node.get('backendDOMNodeId')

                if backend_node_id:
                    # Resolver para WebElement
                    result = driver.execute_cdp_cmd(
                        'DOM.resolveNode',
                        {'backendNodeId': backend_node_id}
                    )

                    # Retornar elemento
                    object_id = result['object']['objectId']
                    element = driver.execute_script(
                        'return arguments[0]',
                        {'objectId': object_id}
                    )
                    return element

    return None
```

### Exemplo: Encontrar Botão por Role

```python
# HTML pode ser:
# <div class="x7s2f9k" data-id="abc123">
#   <span role="button" aria-label="Confirm">Confirm</span>
# </div>

# Encontrar por role (estável)
button = find_by_accessibility_role(driver, role='button', name='Confirm')
button.click()

# Em vez de seletor frágil:
# button = driver.find_element(By.CSS_SELECTOR, "div.x7s2f9k span")  # ❌ Quebra fácil
```

### Roles ARIA Comuns

- `button`: Botões
- `link`: Links
- `textbox`: Campos de texto
- `checkbox`: Checkboxes
- `radio`: Radio buttons
- `combobox`: Dropdowns
- `dialog`: Modais
- `navigation`: Menus de navegação
- `search`: Campos de busca
- `alert`: Alertas/notificações

## 3. Event Listener Interception (Interceptação de Eventos)

### Problema

Para fazer "Direct Routing", você precisa saber qual função JavaScript o botão chamaria ao ser clicado.

### Solução: getEventListeners()

Use `getEventListeners()` via console injection para descobrir handlers:

```python
def get_event_listeners(driver, selector):
    """
    Obtém event listeners de um elemento.

    Args:
        driver: WebDriver instance
        selector: Seletor CSS do elemento

    Returns:
        Dict com tipos de eventos e handlers

    Example:
        listeners = get_event_listeners(driver, "button.next")
        # {'click': [{'listener': 'function() { api.navigateTo("step2") }'}]}
    """
    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) return null;

    // getEventListeners só funciona no console, então usamos alternativa
    const listeners = {};

    // Tentar obter listeners via propriedades do elemento
    for (let key in element) {
        if (key.startsWith('on')) {
            const eventType = key.substring(2);
            if (element[key]) {
                listeners[eventType] = element[key].toString();
            }
        }
    }

    return listeners;
    """
    return driver.execute_script(script, selector)
```

### Direct Routing: Executar Função Diretamente

Em vez de clicar no botão, execute a função JavaScript diretamente:

```python
def direct_route(driver, selector):
    """
    Executa função de navegação diretamente sem clicar.

    Args:
        driver: WebDriver instance
        selector: Seletor do botão/link

    Returns:
        True se navegação bem-sucedida

    Example:
        # Botão chama: api.navigateTo('step2')
        # Em vez de clicar, executar diretamente
        direct_route(driver, "button.next")
    """
    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) return false;

    // Tentar extrair função de navegação
    const onclick = element.onclick;
    if (onclick) {
        // Executar função diretamente
        onclick.call(element);
        return true;
    }

    // Tentar extrair de atributos data-*
    const dataAction = element.getAttribute('data-action');
    if (dataAction) {
        // Executar ação
        eval(dataAction);
        return true;
    }

    // Tentar extrair href de navegação
    const href = element.getAttribute('href') || element.getAttribute('data-href');
    if (href && !href.startsWith('#')) {
        window.location.href = href;
        return true;
    }

    return false;
    """
    return driver.execute_script(script, selector)
```

### Exemplo: Bypass de Botão "Next"

```python
# HTML:
# <button onclick="api.navigateTo('step2')">Next</button>

# Método tradicional (lento, pode falhar)
# button = driver.find_element(By.CSS_SELECTOR, "button")
# button.click()

# Direct Routing (rápido, confiável)
driver.execute_script("api.navigateTo('step2')")

# Ou usar helper
direct_route(driver, "button")
```

## 4. Iframe Context Management (The Dimensional Rift)

### Problema

Iframes são "universos paralelos". Se você está no Iframe A, não pode ver elementos no Iframe B ou no documento principal.

### Solução: Context Path no Matrix Map

Adicione `context_path` ao MATRIX_MAP para rastrear caminho de contexto:

```python
MATRIX_MAP = {
    "API_KEY_BUTTON": {
        "selector": "button.generate-key",
        "depth": 2,
        "context_path": [
            {"type": "default"},  # Documento principal
            {"type": "iframe", "selector": "iframe#auth-frame"},  # Iframe 1
            {"type": "shadow", "selector": "console-component"}  # Shadow DOM
        ],
        "exits": ["KEY_GENERATED_MODAL"]
    }
}
```

### Dimensional Shift: Executar Combo de Contexto

```python
def dimensional_shift(driver, context_path):
    """
    Executa sequência de mudanças de contexto.

    Args:
        driver: WebDriver instance
        context_path: Lista de contextos a navegar

    Returns:
        True se bem-sucedido

    Example:
        context_path = [
            {"type": "default"},
            {"type": "iframe", "selector": "iframe#auth"},
            {"type": "shadow", "selector": "custom-console"}
        ]
    """
    # Sempre começar do contexto padrão
    driver.switch_to.default_content()

    current_element = None

    for context in context_path:
        context_type = context.get("type")

        if context_type == "default":
            # Já estamos no default
            continue

        elif context_type == "iframe":
            # Mudar para iframe
            iframe_selector = context.get("selector")
            iframe = driver.find_element(By.CSS_SELECTOR, iframe_selector)
            driver.switch_to.frame(iframe)

        elif context_type == "shadow":
            # Entrar em Shadow DOM
            shadow_selector = context.get("selector")
            script = """
            const host = document.querySelector(arguments[0]);
            return host ? host.shadowRoot : null;
            """
            shadow_root = driver.execute_script(script, shadow_selector)

            if not shadow_root:
                return False

            # Armazenar shadow root para próximas operações
            current_element = shadow_root

        elif context_type == "nested_iframe":
            # Iframe dentro de iframe
            iframe_selector = context.get("selector")
            iframe = driver.find_element(By.CSS_SELECTOR, iframe_selector)
            driver.switch_to.frame(iframe)

    return True
```

### Exemplo: Navegar para Botão em Iframe + Shadow DOM

```python
# Estrutura:
# Document (default)
#   └─ <iframe id="auth-frame">
#        └─ <console-component>
#             #shadow-root
#               └─ <button class="generate-key">Generate</button>

# Definir caminho de contexto
context_path = [
    {"type": "default"},
    {"type": "iframe", "selector": "iframe#auth-frame"},
    {"type": "shadow", "selector": "console-component"}
]

# Executar dimensional shift
dimensional_shift(driver, context_path)

# Agora podemos acessar o botão
button = driver.execute_script("""
    const host = document.querySelector('console-component');
    return host.shadowRoot.querySelector('button.generate-key');
""")
button.click()

# Voltar ao contexto padrão
driver.switch_to.default_content()
```

### Context Stack: Rastrear Contexto Atual

```python
class ContextStack:
    """Pilha para rastrear contexto atual e permitir rollback."""

    def __init__(self, driver):
        self.driver = driver
        self.stack = [{"type": "default"}]

    def push(self, context):
        """Adiciona novo contexto à pilha."""
        self.stack.append(context)
        self._apply_context(context)

    def pop(self):
        """Remove contexto atual e volta ao anterior."""
        if len(self.stack) > 1:
            self.stack.pop()
            # Voltar ao contexto anterior
            self.driver.switch_to.default_content()
            for context in self.stack[1:]:
                self._apply_context(context)

    def reset(self):
        """Volta ao contexto padrão."""
        self.driver.switch_to.default_content()
        self.stack = [{"type": "default"}]

    def _apply_context(self, context):
        """Aplica mudança de contexto."""
        context_type = context.get("type")

        if context_type == "iframe":
            iframe = self.driver.find_element(
                By.CSS_SELECTOR,
                context.get("selector")
            )
            self.driver.switch_to.frame(iframe)
```

### Exemplo: Uso do Context Stack

```python
# Inicializar stack
stack = ContextStack(driver)

# Entrar em iframe
stack.push({"type": "iframe", "selector": "iframe#auth"})

# Fazer operações no iframe
element = driver.find_element(By.CSS_SELECTOR, "button.login")
element.click()

# Voltar ao contexto anterior
stack.pop()

# Agora estamos de volta ao documento principal
```

## 5. Integração com Matrix Map

### Estrutura Completa de Zona

```python
MATRIX_MAP = {
    "GROQ_API_KEY_BUTTON": {
        # Identificação
        "selector": "button.generate-key",
        "depth": 2,

        # Contexto dimensional
        "context_path": [
            {"type": "default"},
            {"type": "iframe", "selector": "iframe#console-frame"},
            {"type": "shadow", "selector": "api-console"}
        ],

        # Navegação
        "exits": ["KEY_GENERATED_MODAL", "ERROR_DIALOG"],
        "entry_action": "click_api_keys_menu",

        # Validação
        "markers": [
            "button.generate-key",
            "span.key-label"
        ],

        # Acessibilidade
        "accessibility": {
            "role": "button",
            "name": "Generate API Key"
        },

        # Event routing
        "direct_route": "api.keys.generate()",

        # Descrição
        "description": "Botão de geração de API key (iframe + shadow DOM)"
    }
}
```

### Leap To com Dimensional Shift

```python
def leap_to(driver, zone_name, matrix_map):
    """
    Salta para zona com suporte a contexto dimensional.

    Args:
        driver: WebDriver instance
        zone_name: Nome da zona alvo
        matrix_map: Dicionário do Matrix Map

    Returns:
        True se bem-sucedido
    """
    zone = matrix_map.get(zone_name)
    if not zone:
        return False

    # 1. Executar dimensional shift se necessário
    context_path = zone.get("context_path", [{"type": "default"}])
    if not dimensional_shift(driver, context_path):
        return False

    # 2. Tentar direct routing primeiro
    direct_route_cmd = zone.get("direct_route")
    if direct_route_cmd:
        try:
            driver.execute_script(direct_route_cmd)
            return True
        except:
            pass  # Fallback para método tradicional

    # 3. Tentar acessibilidade
    accessibility = zone.get("accessibility")
    if accessibility:
        element = find_by_accessibility_role(
            driver,
            role=accessibility.get("role"),
            name=accessibility.get("name")
        )
        if element:
            element.click()
            return True

    # 4. Fallback: seletor tradicional
    selector = zone.get("selector")
    element = driver.find_element(By.CSS_SELECTOR, selector)
    element.click()

    return True
```

## 6. Debugging e Visualização

### Injetar Marcadores Visuais

```python
def inject_zone_marker(driver, zone_name, color="cyan"):
    """
    Injeta marcador visual na zona atual (debug).

    Args:
        driver: WebDriver instance
        zone_name: Nome da zona
        color: Cor do contorno (padrão: cyan)
    """
    script = f"""
    // Criar overlay
    const overlay = document.createElement('div');
    overlay.style.position = 'fixed';
    overlay.style.top = '10px';
    overlay.style.right = '10px';
    overlay.style.padding = '10px';
    overlay.style.background = 'rgba(0, 0, 0, 0.8)';
    overlay.style.color = '{color}';
    overlay.style.border = '2px solid {color}';
    overlay.style.borderRadius = '5px';
    overlay.style.zIndex = '999999';
    overlay.style.fontFamily = 'monospace';
    overlay.style.fontSize = '14px';
    overlay.textContent = 'ZONE: {zone_name}';

    document.body.appendChild(overlay);

    // Remover após 3 segundos
    setTimeout(() => overlay.remove(), 3000);
    """
    driver.execute_script(script)
```

## Resumo de Técnicas

| Técnica | Quando Usar | Vantagem |
|---------|-------------|----------|
| **Shadow DOM Injection** | Web Components | Acessa elementos encapsulados |
| **Accessibility Tree** | DOM caótico | Seletores estáveis (role/name) |
| **Event Interception** | Direct Routing | Bypass de cliques, mais rápido |
| **Context Path** | Iframes aninhados | Navegação dimensional precisa |
| **CDP Protocol** | Casos avançados | Acesso a APIs internas do Chrome |

## Próximos Passos

1. Implementar helpers no SelumOfPersistence
2. Adicionar suporte a context_path no Matrix Map
3. Criar testes para Shadow DOM e iframes
4. Integrar com Divine Inspiration para geração automática
5. Documentar casos de uso específicos (Gmail, Groq, etc.)
