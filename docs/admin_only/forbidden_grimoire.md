# 🌑 Forbidden Grimoire - Shadow Techniques for Admin Constructor

## ⚠️ CLASSIFICAÇÃO: ADMIN ONLY

**AVISO CRÍTICO**: Este documento contém técnicas avançadas de automação web que operam em níveis profundos do navegador e frameworks.

**USE APENAS EM AMBIENTES CONTROLADOS E COM PERMISSÃO EXPLÍCITA.**

---

## 1. 👻 React Fiber Hijacking (The Soul Snatch)

### Conceito
Manipular o estado interno do React ignorando completamente a UI através do Fiber Tree.

### Implementação Completa

```python
def hijack_fiber_props(driver, selector, prop_name, new_value):
    """Altera props diretamente no Fiber node."""
    script = """
    const element = document.querySelector(arguments[0]);
    const propName = arguments[1];
    const newValue = arguments[2];
    
    if (!element) return false;
    
    const fiberKey = Object.keys(element).find(k => 
        k.startsWith('__reactFiber$')
    );
    
    if (!fiberKey) return false;
    
    const fiber = element[fiberKey];
    
    if (fiber.memoizedProps) {
        fiber.memoizedProps[propName] = newValue;
        
        if (fiber.stateNode && fiber.stateNode.forceUpdate) {
            fiber.stateNode.forceUpdate();
        }
        
        if (propName === 'disabled') {
            element.disabled = newValue;
        }
        
        return true;
    }
    
    return false;
    """
    return driver.execute_script(script, selector, prop_name, new_value)
```

Ver documento completo em: `docs/paladin_grimoire/Forbidden_Powers.md`

---

## 2. 👤 Event Listener Detachment (Ghost Interaction)

### Conceito
Interagir sem disparar rastreadores de telemetria e behavioral biometrics.

### Ghost Click Implementation

```python
def ghost_click(driver, selector):
    """Click sem telemetria."""
    script = """
    const element = document.querySelector(arguments[0]);
    if (!element) return false;
    
    // Salvar listeners
    const savedListeners = {};
    for (let key in element) {
        if (key.startsWith('on') && element[key]) {
            savedListeners[key] = element[key];
            element[key] = null;
        }
    }
    
    // Click
    element.click();
    
    // Restaurar após 10ms
    setTimeout(() => {
        for (let key in savedListeners) {
            element[key] = savedListeners[key];
        }
    }, 10);
    
    return true;
    """
    return driver.execute_script(script, selector)
```

---

## 3. 🔓 CDP Raw Injection (The Matrix Backdoor)

### Conceito
Falar direto com o motor V8 do Chrome via CDP, bypassando Selenium.

### Trusted Click via CDP

```python
def cdp_trusted_click(driver, selector):
    """Click com userGesture=true (navegador acredita ser humano)."""
    script = f"""
    const element = document.querySelector('{selector}');
    if (element) {{
        element.click();
        return true;
    }}
    return false;
    """
    
    result = driver.execute_cdp_cmd('Runtime.evaluate', {
        'expression': script,
        'userGesture': True,  # 🔑 Chave mágica
        'awaitPromise': True,
        'returnByValue': True
    })
    
    return result.get('result', {}).get('value', False)
```

---

## 4. 🍪 Stealth Cookie/Token Exfiltration

### Conceito
Clonar sessões completas incluindo cookies HttpOnly.

### Exfiltração via CDP

```python
def exfiltrate_httponly_cookies(driver):
    """Extrai TODOS os cookies incluindo HttpOnly."""
    driver.execute_cdp_cmd('Network.enable', {})
    result = driver.execute_cdp_cmd('Network.getAllCookies', {})
    return result.get('cookies', [])

def clone_browser_session(driver_source, driver_target):
    """Clona sessão completa entre navegadores."""
    # 1. Exfiltrar cookies
    cookies = exfiltrate_httponly_cookies(driver_source)
    
    # 2. Exfiltrar storages
    local_storage = driver_source.execute_script("""
        const storage = {};
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            storage[key] = localStorage.getItem(key);
        }
        return storage;
    """)
    
    # 3. Navegar e injetar no target
    driver_target.get(driver_source.current_url)
    
    for cookie in cookies:
        try:
            driver_target.execute_cdp_cmd('Network.setCookie', cookie)
        except:
            pass
    
    driver_target.execute_script("""
        const storage = arguments[0];
        for (let key in storage) {
            localStorage.setItem(key, storage[key]);
        }
    """, local_storage)
    
    driver_target.refresh()
    return True
```

---

## 5. 🥷 CDP Bypass - Anti-Detecção

### Remover Rastros de Automação

```python
def remove_automation_traces(driver):
    """Remove todos os rastros detectáveis."""
    stealth_script = """
    // 1. Remover navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    
    // 2. Adicionar chrome.runtime
    window.chrome = { runtime: {} };
    
    // 3. Modificar permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
    """
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': stealth_script
    })
```

---

## 6. 🎭 ShadowConstructor Class

### Integração Completa

```python
class ShadowConstructor:
    """Constructor com poderes proibidos."""
    
    def __init__(self, driver):
        self.driver = driver
        self._enable_stealth()
    
    def _enable_stealth(self):
        remove_automation_traces(self.driver)
    
    def soul_snatch(self, selector, prop, value):
        """React Fiber hijacking."""
        return hijack_fiber_props(self.driver, selector, prop, value)
    
    def ghost_click(self, selector):
        """Click sem telemetria."""
        return ghost_click(self.driver, selector)
    
    def matrix_click(self, selector):
        """Click trusted via CDP."""
        return cdp_trusted_click(self.driver, selector)
    
    def exfiltrate_session(self):
        """Extrai sessão completa."""
        return exfiltrate_httponly_cookies(self.driver)
    
    def clone_to(self, target_driver):
        """Clona sessão."""
        return clone_browser_session(self.driver, target_driver)
```

---

## ⚠️ AVISOS FINAIS

### Quando Usar?
1. Apenas em último caso
2. Ambientes controlados
3. Com permissão explícita
4. Sempre com fallback

### Riscos
- Detecção por anti-bots avançados
- Quebra de aplicação
- Violação de termos de serviço
- Problemas legais

### Ética
Use apenas para:
- Testes em suas próprias aplicações
- Pesquisa de segurança autorizada
- Automação legítima com permissão

**NUNCA use para fraude, bypass malicioso ou violação de privacidade.**

---

**"O poder corrompe. Use com sabedoria."** 🌑

Para implementações completas, consulte: `docs/paladin_grimoire/Forbidden_Powers.md`
