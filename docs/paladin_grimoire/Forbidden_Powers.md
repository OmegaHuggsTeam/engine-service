# Forbidden Powers - Poderes Proibidos do Paladino

## ⚠️ Aviso

Este documento contém técnicas avançadas de web scraping e automação que exploram APIs internas de frameworks e navegadores. Use com responsabilidade e apenas em aplicações que você tem permissão para automatizar.

**"Com grande poder vem grande responsabilidade."**

---

## 1. 🔮 React Fiber Tree - O Santo Graal

### O Segredo

O React não usa o DOM diretamente - ele usa o **Virtual DOM** através do **Fiber Tree**. Cada elemento DOM em uma aplicação React tem propriedades secretas que começam com `__reactFiber$` ou `__reactProps$`.

### Descobrindo o Fiber

```javascript
// No console do Chrome, em qualquer site React
const root = document.querySelector('#root');
const reactKeys = Object.keys(root).filter(k => k.startsWith('__react'));
console.log(reactKeys);
// Output: ["__reactFiber$...", "__reactContainer$..."]
```

### Acessando State e Props

```python
def get_react_fiber(driver, selector):
    """
    Acessa React Fiber Tree de um elemento.
    
    Args:
        driver: WebDriver instance
        selector: Seletor CSS do elemento React
        
    Returns:
        Dict com state, props e outras informações internas
        
    Example:
        fiber = get_react_fiber(driver, "button.submit")
        print(fiber['memoizedState'])  # State interno
        print(fiber['memoizedProps'])  # Props do componente
    """
    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) return null;
    
    // Encontrar chave do Fiber
    const fiberKey = Object.keys(element).find(k => k.startsWith('__reactFiber$'));
    if (!fiberKey) return null;
    
    const fiber = element[fiberKey];
    
    // Extrair informações relevantes
    return {
        type: fiber.type?.name || fiber.type,
        memoizedState: fiber.memoizedState,
        memoizedProps: fiber.memoizedProps,
        key: fiber.key,
        stateNode: fiber.stateNode,
        return: fiber.return?.type?.name
    };
    """
    return driver.execute_script(script, selector)
```

### Poder Proibido: Manipular State Interno

```python
def manipulate_react_state(driver, selector, state_path, new_value):
    """
    Manipula state interno de componente React.
    
    ⚠️ ATENÇÃO: Isso pode quebrar a aplicação!
    
    Args:
        driver: WebDriver instance
        selector: Seletor CSS do elemento React
        state_path: Caminho para o state (ex: "disabled", "value")
        new_value: Novo valor do state
        
    Returns:
        True se bem-sucedido
        
    Example:
        # Habilitar botão desabilitado
        manipulate_react_state(driver, "button.submit", "disabled", False)
    """
    script = """
    const element = document.querySelector(arguments[0]);
    const statePath = arguments[1];
    const newValue = arguments[2];
    
    if (!element) return false;
    
    // Encontrar Fiber
    const fiberKey = Object.keys(element).find(k => k.startsWith('__reactFiber$'));
    if (!fiberKey) return false;
    
    const fiber = element[fiberKey];
    
    // Manipular state
    if (fiber.memoizedState) {
        fiber.memoizedState[statePath] = newValue;
        
        // Forçar re-render
        if (fiber.stateNode && fiber.stateNode.forceUpdate) {
            fiber.stateNode.forceUpdate();
        }
        
        return true;
    }
    
    return false;
    """
    return driver.execute_script(script, selector, state_path, new_value)
```

### Exemplo: Bypass de Botão Desabilitado

```python
# Cenário: Botão "Submit" está desabilitado no React
# HTML: <button disabled>Submit</button>

# Método tradicional: ❌ Não funciona
# button = driver.find_element(By.CSS_SELECTOR, "button")
# button.click()  # ElementNotInteractableException

# Poder Proibido: ✅ Manipular state interno
manipulate_react_state(driver, "button", "disabled", False)

# Agora o botão está habilitado internamente
button = driver.find_element(By.CSS_SELECTOR, "button")
button.click()  # Funciona!
```

### Extrair Dados de Componentes React

```python
def extract_react_component_data(driver, selector):
    """
    Extrai todos os dados de um componente React.
    
    Args:
        driver: WebDriver instance
        selector: Seletor CSS do componente
        
    Returns:
        Dict com state, props e context
        
    Example:
        data = extract_react_component_data(driver, "div.user-profile")
        print(data['props']['username'])
        print(data['state']['isLoggedIn'])
    """
    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) return null;
    
    const fiberKey = Object.keys(element).find(k => k.startsWith('__reactFiber$'));
    if (!fiberKey) return null;
    
    const fiber = element[fiberKey];
    
    // Função recursiva para serializar objetos (evitar circular refs)
    function serialize(obj, depth = 0) {
        if (depth > 3) return '[Max Depth]';
        if (obj === null || obj === undefined) return obj;
        if (typeof obj !== 'object') return obj;
        if (Array.isArray(obj)) return obj.map(item => serialize(item, depth + 1));
        
        const result = {};
        for (let key in obj) {
            if (obj.hasOwnProperty(key)) {
                try {
                    result[key] = serialize(obj[key], depth + 1);
                } catch (e) {
                    result[key] = '[Error]';
                }
            }
        }
        return result;
    }
    
    return {
        props: serialize(fiber.memoizedProps),
        state: serialize(fiber.memoizedState),
        type: fiber.type?.name || String(fiber.type)
    };
    """
    return driver.execute_script(script, selector)
```

---

## 2. 🚪 Chrome DevTools Protocol (CDP) - O Backdoor

### O Segredo

O Selenium é apenas uma **capa** sobre o CDP. O Chrome usa CDP para debugar a si mesmo. Acessando CDP diretamente, você tem poderes que o Selenium não expõe.

### Habilitando CDP

```python
from selenium import webdriver

# Habilitar CDP
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(options=options)

# Agora você pode usar execute_cdp_cmd
driver.execute_cdp_cmd('Network.enable', {})
```

### Poder Proibido: DOMSnapshot - Mapa Instantâneo

```python
def capture_dom_snapshot(driver):
    """
    Captura snapshot completo do DOM incluindo Shadow DOM.
    
    Retorna árvore inteira com coordenadas de layout em um único dump JSON.
    
    Args:
        driver: WebDriver instance
        
    Returns:
        Dict com snapshot completo do DOM
        
    Example:
        snapshot = capture_dom_snapshot(driver)
        print(snapshot['documents'])  # Todos os documentos
        print(snapshot['strings'])    # Strings indexadas
    """
    # Habilitar DOM domain
    driver.execute_cdp_cmd('DOM.enable', {})
    
    # Capturar snapshot
    snapshot = driver.execute_cdp_cmd('DOMSnapshot.captureSnapshot', {
        'computedStyles': [],  # Não precisamos de estilos computados
        'includePaintOrder': True,
        'includeDOMRects': True  # Incluir coordenadas de layout
    })
    
    return snapshot
```

### Extrair Todos os Shadow DOMs

```python
def find_all_shadow_roots(driver):
    """
    Encontra todos os Shadow DOMs na página usando CDP.
    
    Args:
        driver: WebDriver instance
        
    Returns:
        Lista de dicts com informações de Shadow DOMs
        
    Example:
        shadows = find_all_shadow_roots(driver)
        for shadow in shadows:
            print(f"Host: {shadow['host']}, Children: {shadow['children']}")
    """
    snapshot = capture_dom_snapshot(driver)
    
    shadow_roots = []
    
    # Parsear snapshot para encontrar shadow roots
    for doc in snapshot.get('documents', []):
        nodes = doc.get('nodes', {})
        
        for i, node_type in enumerate(nodes.get('nodeType', [])):
            # nodeType 11 = DOCUMENT_FRAGMENT_NODE (shadow root)
            if node_type == 11:
                shadow_roots.append({
                    'index': i,
                    'host': nodes.get('nodeName', [])[i],
                    'children': nodes.get('childNodeIndexes', [])[i] if i < len(nodes.get('childNodeIndexes', [])) else []
                })
    
    return shadow_roots
```

### Interceptar Requisições de Rede

```python
def intercept_network_requests(driver, url_pattern):
    """
    Intercepta requisições de rede que correspondem ao padrão.
    
    Args:
        driver: WebDriver instance
        url_pattern: Padrão de URL para interceptar (regex)
        
    Returns:
        Lista de requisições interceptadas
        
    Example:
        # Interceptar chamadas de API
        requests = intercept_network_requests(driver, "*/api/keys*")
    """
    # Habilitar Network domain
    driver.execute_cdp_cmd('Network.enable', {})
    
    # Configurar interceptação
    driver.execute_cdp_cmd('Network.setRequestInterception', {
        'patterns': [{'urlPattern': url_pattern}]
    })
    
    # Coletar requisições (simplificado - na prática, use event listeners)
    # Aqui você precisaria de um listener assíncrono
    pass
```

### Runtime.evaluate - Injeção Stealth

```python
def stealth_execute_script(driver, script):
    """
    Executa JavaScript sem deixar rastros no console.
    
    Usa Runtime.evaluate do CDP em vez de execute_script do Selenium.
    
    Args:
        driver: WebDriver instance
        script: Código JavaScript a executar
        
    Returns:
        Resultado da execução
        
    Example:
        result = stealth_execute_script(driver, "return document.title")
    """
    result = driver.execute_cdp_cmd('Runtime.evaluate', {
        'expression': script,
        'returnByValue': True,
        'awaitPromise': True
    })
    
    if result.get('exceptionDetails'):
        raise Exception(f"Script error: {result['exceptionDetails']}")
    
    return result.get('result', {}).get('value')
```

### Obter Performance Metrics

```python
def get_performance_metrics(driver):
    """
    Obtém métricas de performance da página.
    
    Args:
        driver: WebDriver instance
        
    Returns:
        Dict com métricas de performance
        
    Example:
        metrics = get_performance_metrics(driver)
        print(f"Load time: {metrics['DomContentLoaded']}ms")
    """
    # Habilitar Performance domain
    driver.execute_cdp_cmd('Performance.enable', {})
    
    # Obter métricas
    metrics = driver.execute_cdp_cmd('Performance.getMetrics', {})
    
    # Converter para dict
    metrics_dict = {}
    for metric in metrics.get('metrics', []):
        metrics_dict[metric['name']] = metric['value']
    
    return metrics_dict
```

---

## 3. 🥷 Web Scraping Stealth - Técnicas Furtivas

### O Segredo

Existem comunidades dedicadas a contornar proteções anti-bot do Google, Cloudflare, e outros. As melhores técnicas estão em bibliotecas open-source.

### Recursos Essenciais

1. **Playwright Selectors**: Estude `playwright/packages/playwright-core/src/server/injected/selectorEngine.ts`
2. **Undetected Chromedriver**: `undetected-chromedriver` no GitHub
3. **Puppeteer Extra Stealth**: `puppeteer-extra-plugin-stealth`

### Bypass de Detecção: Remover Webdriver Flag

```python
def remove_webdriver_flag(driver):
    """
    Remove flag 'navigator.webdriver' que identifica automação.
    
    Args:
        driver: WebDriver instance
        
    Example:
        remove_webdriver_flag(driver)
        # Agora navigator.webdriver === undefined
    """
    script = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': script
    })
```

### Bypass de Detecção: Chrome Runtime

```python
def spoof_chrome_runtime(driver):
    """
    Adiciona chrome.runtime para parecer extensão legítima.
    
    Args:
        driver: WebDriver instance
    """
    script = """
    window.chrome = {
        runtime: {
            connect: function() {},
            sendMessage: function() {}
        }
    };
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': script
    })
```

### Bypass de Detecção: Permissions

```python
def spoof_permissions(driver):
    """
    Modifica API de permissões para evitar detecção.
    
    Args:
        driver: WebDriver instance
    """
    script = """
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': script
    })
```

### Bypass de Detecção: Plugins

```python
def spoof_plugins(driver):
    """
    Adiciona plugins falsos para parecer navegador real.
    
    Args:
        driver: WebDriver instance
    """
    script = """
    Object.defineProperty(navigator, 'plugins', {
        get: () => [
            {
                0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                description: "Portable Document Format",
                filename: "internal-pdf-viewer",
                length: 1,
                name: "Chrome PDF Plugin"
            },
            {
                0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                description: "Portable Document Format",
                filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                length: 1,
                name: "Chrome PDF Viewer"
            }
        ]
    });
    """
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': script
    })
```

### Stealth Mode Completo

```python
def enable_stealth_mode(driver):
    """
    Habilita modo stealth completo com todos os bypasses.
    
    Args:
        driver: WebDriver instance
        
    Example:
        driver = webdriver.Chrome()
        enable_stealth_mode(driver)
        driver.get("https://bot-detection-test.com")
    """
    remove_webdriver_flag(driver)
    spoof_chrome_runtime(driver)
    spoof_permissions(driver)
    spoof_plugins(driver)
    
    # User agent realista
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {
        'userAgent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    # Timezone
    driver.execute_cdp_cmd('Emulation.setTimezoneOverride', {
        'timezoneId': 'America/New_York'
    })
    
    # Locale
    driver.execute_cdp_cmd('Emulation.setLocaleOverride', {
        'locale': 'en-US'
    })
```

---

## 4. ♿ Accessibility Tree (AXTree) - O Caminho Resiliente

### O Segredo

Frameworks como React e Angular mudam classes CSS constantemente, mas mantêm a estrutura semântica de acessibilidade. A **Accessibility Tree** é o caminho mais resiliente para automação.

### Por Que É Resiliente?

- Google não muda roles ARIA (quebraria acessibilidade)
- Estrutura semântica é estável entre versões
- Funciona mesmo com CSS/IDs dinâmicos
- Suportado por todos os frameworks modernos

### Acessar AXTree Completa

```python
def get_full_accessibility_tree(driver):
    """
    Obtém Accessibility Tree completa da página.
    
    Args:
        driver: WebDriver instance
        
    Returns:
        Dict com árvore de acessibilidade completa
        
    Example:
        ax_tree = get_full_accessibility_tree(driver)
        for node in ax_tree['nodes']:
            print(f"{node['role']}: {node['name']}")
    """
    # Habilitar Accessibility domain
    driver.execute_cdp_cmd('Accessibility.enable', {})
    
    # Obter árvore completa
    ax_tree = driver.execute_cdp_cmd('Accessibility.getFullAXTree', {})
    
    return ax_tree
```

### Buscar por Role e Name (Avançado)

```python
def find_by_ax_tree(driver, role, name=None, description=None):
    """
    Busca elemento por role, name e description na AXTree.
    
    Args:
        driver: WebDriver instance
        role: Role ARIA (ex: 'button', 'link')
        name: Nome acessível (opcional)
        description: Descrição acessível (opcional)
        
    Returns:
        WebElement ou None
        
    Example:
        # Encontrar botão "Submit" mesmo com classe dinâmica
        button = find_by_ax_tree(driver, 'button', name='Submit')
    """
    ax_tree = get_full_accessibility_tree(driver)
    
    for node in ax_tree.get('nodes', []):
        # Verificar role
        node_role = node.get('role', {}).get('value')
        if node_role != role:
            continue
        
        # Verificar name
        if name is not None:
            node_name = node.get('name', {}).get('value', '')
            if name.lower() not in node_name.lower():
                continue
        
        # Verificar description
        if description is not None:
            node_desc = node.get('description', {}).get('value', '')
            if description.lower() not in node_desc.lower():
                continue
        
        # Encontrou! Resolver para WebElement
        backend_node_id = node.get('backendDOMNodeId')
        if backend_node_id:
            try:
                # Resolver node
                result = driver.execute_cdp_cmd('DOM.resolveNode', {
                    'backendNodeId': backend_node_id
                })
                
                # Obter elemento
                remote_object = result.get('object', {})
                object_id = remote_object.get('objectId')
                
                if object_id:
                    # Executar script para retornar elemento
                    element = driver.execute_script(
                        'return arguments[0]',
                        {'ELEMENT': object_id}
                    )
                    return element
            except:
                continue
    
    return None
```

### Listar Todos os Elementos Interativos

```python
def list_interactive_elements(driver):
    """
    Lista todos os elementos interativos da página via AXTree.
    
    Args:
        driver: WebDriver instance
        
    Returns:
        Lista de dicts com role, name e description
        
    Example:
        elements = list_interactive_elements(driver)
        for elem in elements:
            print(f"{elem['role']}: {elem['name']}")
    """
    ax_tree = get_full_accessibility_tree(driver)
    
    interactive_roles = [
        'button', 'link', 'textbox', 'checkbox', 'radio',
        'combobox', 'listbox', 'menuitem', 'tab', 'switch'
    ]
    
    elements = []
    
    for node in ax_tree.get('nodes', []):
        role = node.get('role', {}).get('value')
        
        if role in interactive_roles:
            elements.append({
                'role': role,
                'name': node.get('name', {}).get('value', ''),
                'description': node.get('description', {}).get('value', ''),
                'focused': node.get('focused', False),
                'disabled': node.get('disabled', False)
            })
    
    return elements
```

---

## 5. 🎯 Integração: Selum com Poderes Proibidos

### Classe ForbiddenPowers

```python
class ForbiddenPowers:
    """
    Wrapper para poderes proibidos do Paladino.
    
    Centraliza técnicas avançadas de automação.
    """
    
    def __init__(self, driver):
        self.driver = driver
        self._enable_stealth()
    
    def _enable_stealth(self):
        """Habilita modo stealth automaticamente."""
        enable_stealth_mode(self.driver)
    
    def react_fiber(self, selector):
        """Acessa React Fiber Tree."""
        return get_react_fiber(self.driver, selector)
    
    def manipulate_react(self, selector, state_path, value):
        """Manipula state interno do React."""
        return manipulate_react_state(self.driver, selector, state_path, value)
    
    def dom_snapshot(self):
        """Captura snapshot completo do DOM."""
        return capture_dom_snapshot(self.driver)
    
    def ax_tree(self):
        """Obtém Accessibility Tree completa."""
        return get_full_accessibility_tree(self.driver)
    
    def find_by_role(self, role, name=None):
        """Busca elemento por role de acessibilidade."""
        return find_by_ax_tree(self.driver, role, name)
    
    def stealth_eval(self, script):
        """Executa script sem rastros."""
        return stealth_execute_script(self.driver, script)
```

### Uso no SelumOfPersistence

```python
# Adicionar ao __init__ do Selum
self.forbidden = ForbiddenPowers(self.driver)

# Usar poderes proibidos
fiber = self.forbidden.react_fiber("button.submit")
self.forbidden.manipulate_react("button.submit", "disabled", False)
button = self.forbidden.find_by_role("button", "Submit")
```

---

## ⚠️ Avisos Finais

### Ética e Legalidade

- Use apenas em aplicações que você tem permissão para automatizar
- Respeite robots.txt e termos de serviço
- Não use para bypass de segurança malicioso
- Considere impacto em servidores (rate limiting)

### Riscos Técnicos

- Manipular React Fiber pode quebrar a aplicação
- CDP bypasses podem ser detectados por anti-bots avançados
- Técnicas podem parar de funcionar em novas versões
- Sempre tenha fallback para métodos tradicionais

### Manutenção

- Teste regularmente (frameworks mudam)
- Monitore logs de erro
- Documente casos de uso específicos
- Mantenha biblioteca de bypasses atualizada

---

## 📚 Recursos Adicionais

### Repositórios GitHub

- `undetected-chromedriver`: Bypass de detecção
- `playwright`: Seletores avançados
- `puppeteer-extra-plugin-stealth`: Técnicas stealth
- `selenium-stealth`: Bypasses para Selenium

### Documentação Oficial

- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/
- React Fiber Architecture: https://github.com/acdlite/react-fiber-architecture
- ARIA Roles: https://www.w3.org/TR/wai-aria-1.2/

### Comunidades

- r/webscraping (Reddit)
- Selenium Users Group
- Playwright Discord

---

**"O conhecimento é poder. Use-o sabiamente."** ⚡
