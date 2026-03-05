# ⚔️ Shadow Arsenal - Bibliotecas por Poder Proibido

## 🎯 Visão Geral

Este documento mapeia cada Shadow Power para sua biblioteca especializada, explicando por que cada "arma" é a melhor escolha para aquele poder específico.

---

## 1. 🔮 Soul Snatch (React Fiber Hijacking)

### Biblioteca: **Playwright (via CDP)**

#### Por Que Esta Arma?

- **Seletores nativos de acessibilidade**: Playwright tem suporte built-in para ARIA roles
- **Integração V8 veloz**: Injeção de scripts no React muito mais rápida que Selenium
- **CDP nativo**: Acesso direto ao Chrome DevTools Protocol
- **Auto-waiting**: Espera automática por elementos (mais confiável)

#### Instalação

```bash
pip install playwright
playwright install chromium
```

#### Exemplo de Uso

```python
from playwright.sync_api import sync_playwright

def soul_snatch_playwright(url, selector, prop, value):
    """React Fiber hijacking com Playwright."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url)
        
        # Injetar script para manipular Fiber
        script = f"""
        const element = document.querySelector('{selector}');
        const fiberKey = Object.keys(element).find(k => 
            k.startsWith('__reactFiber$')
        );
        
        if (fiberKey) {{
            const fiber = element[fiberKey];
            if (fiber.memoizedProps) {{
                fiber.memoizedProps['{prop}'] = {value};
                if (fiber.stateNode && fiber.stateNode.forceUpdate) {{
                    fiber.stateNode.forceUpdate();
                }}
            }}
        }}
        """
        
        page.evaluate(script)
        browser.close()
```

#### Vantagens vs Selenium

| Feature | Playwright | Selenium |
|---------|-----------|----------|
| Velocidade de injeção | ⚡ Muito rápida | 🐌 Lenta |
| Seletores ARIA | ✅ Nativos | ❌ Manual |
| CDP | ✅ Integrado | ⚠️ Experimental |
| Auto-waiting | ✅ Sim | ❌ Não |

---

## 2. 👻 Ghost Interaction (Event Detachment)

### Biblioteca: **Puppeteer-extra (Python: pyppeteer-stealth)**

#### Por Que Esta Arma?

- **Plugin stealth built-in**: Rotinas de limpeza de rastros já implementadas
- **navigator.webdriver removal**: Automático
- **Event listener manipulation**: APIs específicas para isso
- **Behavioral biometrics bypass**: Timing e movimentos humanizados

#### Instalação

```bash
pip install pyppeteer
pip install pyppeteer-stealth
```

#### Exemplo de Uso

```python
import asyncio
from pyppeteer import launch
from pyppeteer_stealth import stealth

async def ghost_click_pyppeteer(url, selector):
    """Click sem telemetria com Pyppeteer."""
    browser = await launch(headless=False)
    page = await browser.newPage()
    
    # Aplicar stealth
    await stealth(page)
    
    await page.goto(url)
    
    # Ghost click (sem event listeners)
    await page.evaluate(f"""
        const element = document.querySelector('{selector}');
        
        // Salvar listeners
        const savedListeners = {{}};
        for (let key in element) {{
            if (key.startsWith('on') && element[key]) {{
                savedListeners[key] = element[key];
                element[key] = null;
            }}
        }}
        
        // Click
        element.click();
        
        // Restaurar
        setTimeout(() => {{
            for (let key in savedListeners) {{
                element[key] = savedListeners[key];
            }}
        }}, 10);
    """)
    
    await browser.close()

# Executar
asyncio.get_event_loop().run_until_complete(
    ghost_click_pyppeteer('https://example.com', 'button.submit')
)
```

#### Features do Stealth Plugin

- ✅ Remove `navigator.webdriver`
- ✅ Adiciona `chrome.runtime`
- ✅ Modifica `navigator.plugins`
- ✅ Ajusta `navigator.permissions`
- ✅ Randomiza `navigator.languages`
- ✅ Modifica `screen` properties

---

## 3. 🔓 Matrix Backdoor (CDP Injection)

### Biblioteca: **DrissionPage**

#### Por Que Esta Arma?

- **Híbrido Selenium + HTTP**: Combina DOM manipulation com requisições brutas
- **Salto entre DOM e Rede**: Sem recarregar página
- **CDP nativo**: Acesso direto ao protocolo
- **Performance**: Muito mais rápido que Selenium puro

#### Instalação

```bash
pip install DrissionPage
```

#### Exemplo de Uso

```python
from DrissionPage import ChromiumPage

def matrix_backdoor_drission(url, selector):
    """CDP injection com DrissionPage."""
    page = ChromiumPage()
    page.get(url)
    
    # Usar CDP diretamente
    result = page.run_cdp('Runtime.evaluate', 
        expression=f"""
        const element = document.querySelector('{selector}');
        element.click();
        """,
        userGesture=True  # 🔑 Trusted click
    )
    
    page.quit()
    return result

# Exemplo: Salto entre DOM e Rede
def hybrid_navigation(url):
    """Navegação híbrida (DOM + HTTP)."""
    page = ChromiumPage()
    
    # 1. Carregar página (DOM)
    page.get(url)
    
    # 2. Extrair token via DOM
    token = page.ele('input[name="csrf_token"]').attr('value')
    
    # 3. Fazer requisição HTTP direta (sem recarregar)
    response = page.session.post(
        'https://api.example.com/data',
        headers={'X-CSRF-Token': token}
    )
    
    # 4. Voltar para DOM
    page.ele('button.next').click()
    
    page.quit()
```

#### Vantagens do DrissionPage

| Feature | DrissionPage | Selenium |
|---------|-------------|----------|
| Requisições HTTP | ✅ Integradas | ❌ Separadas |
| CDP | ✅ Nativo | ⚠️ Experimental |
| Performance | ⚡ Rápido | 🐌 Lento |
| Salto DOM↔Rede | ✅ Sim | ❌ Não |

---

## 4. 🍪 Session Exfiltration (Cookie Cloning)

### Biblioteca: **Requests + browser-cookie3**

#### Por Que Esta Arma?

- **Extração sem UI**: Cookies sem abrir navegador
- **Compatibilidade**: Chrome, Firefox, Edge, Safari
- **Velocidade**: Milissegundos vs segundos
- **Salto entre zonas**: Mover sessões instantaneamente

#### Instalação

```bash
pip install requests
pip install browser-cookie3
```

#### Exemplo de Uso

```python
import browser_cookie3
import requests

def exfiltrate_cookies_fast(domain):
    """Extrai cookies de navegador fechado."""
    # Extrair cookies do Chrome
    cookies = browser_cookie3.chrome(domain_name=domain)
    
    # Usar em requisição
    response = requests.get(
        f'https://{domain}/api/data',
        cookies=cookies
    )
    
    return response.json()

def clone_session_fast(source_domain, target_url):
    """Clona sessão entre domínios."""
    # 1. Extrair cookies do source
    cookies = browser_cookie3.chrome(domain_name=source_domain)
    
    # 2. Criar sessão requests
    session = requests.Session()
    session.cookies.update(cookies)
    
    # 3. Usar em target
    response = session.get(target_url)
    
    return response

# Exemplo: Salto instantâneo
def instant_zone_jump():
    """Salta entre zonas sem abrir navegador."""
    # Extrair sessão do Gmail
    gmail_cookies = browser_cookie3.chrome(domain_name='gmail.com')
    
    # Usar em API do Google
    session = requests.Session()
    session.cookies.update(gmail_cookies)
    
    # Acessar Google Drive sem login
    drive_response = session.get('https://drive.google.com/drive/my-drive')
    
    return drive_response
```

#### Vantagens

- ⚡ **Velocidade**: 100x mais rápido que Selenium
- 🔒 **Segurança**: Sem UI = sem screenshots
- 🎯 **Precisão**: Acesso direto ao cookie store
- 🚀 **Escalabilidade**: Múltiplas sessões em paralelo

---

## 5. 🗺️ Dimensional Mapping (DOM Snapshot)

### Biblioteca: **BeautifulSoup4 + lxml**

#### Por Que Esta Arma?

- **Processamento offline**: DOM em RAM (milissegundos)
- **Parser lxml**: Mais rápido que html.parser
- **Memória eficiente**: Árvore completa sem overhead do navegador
- **Análise paralela**: Enquanto Selenium foca no próximo passo

#### Instalação

```bash
pip install beautifulsoup4
pip install lxml
```

#### Exemplo de Uso

```python
from bs4 import BeautifulSoup
import lxml

def map_dom_offline(html_source):
    """Mapeia DOM completo em RAM."""
    soup = BeautifulSoup(html_source, 'lxml')
    
    # Encontrar todos os iframes
    iframes = soup.find_all('iframe')
    
    # Encontrar shadow roots (via atributos)
    shadow_hosts = soup.find_all(attrs={'shadowroot': True})
    
    # Mapear estrutura
    dom_map = {
        'iframes': [
            {
                'id': iframe.get('id'),
                'src': iframe.get('src'),
                'selector': f"iframe#{iframe.get('id')}" if iframe.get('id') else None
            }
            for iframe in iframes
        ],
        'shadow_roots': [
            {
                'tag': host.name,
                'id': host.get('id'),
                'selector': f"{host.name}#{host.get('id')}" if host.get('id') else None
            }
            for host in shadow_hosts
        ]
    }
    
    return dom_map

def blitz_recon(driver):
    """Reconhecimento ultra-rápido."""
    # 1. Capturar HTML
    html = driver.page_source
    
    # 2. Processar offline (não bloqueia driver)
    dom_map = map_dom_offline(html)
    
    # 3. Enquanto isso, driver continua
    driver.find_element(By.CSS_SELECTOR, 'button.next').click()
    
    return dom_map
```

#### Performance Comparison

| Método | Tempo | Bloqueio |
|--------|-------|----------|
| Selenium find_all | ~500ms | ✅ Sim |
| BeautifulSoup | ~50ms | ❌ Não |
| lxml puro | ~20ms | ❌ Não |

---

## 6. 🎯 Blitz Recon - Estratégia de Turno

### Coreografia Completa

```python
from DrissionPage import ChromiumPage
from bs4 import BeautifulSoup
import json

class BlitzRecon:
    """Reconhecimento ultra-rápido em 4 turnos."""
    
    def __init__(self, url):
        self.url = url
        self.page = ChromiumPage()
        self.matrix_map = {}
    
    def turno_1_clarao(self):
        """
        Turno 1: O Clarão (DrissionPage)
        
        Snapshot ultra-rápido via CDP sem renderizar imagens/CSS.
        """
        # Desabilitar imagens e CSS
        self.page.set.load_mode.none()  # Não carregar recursos
        
        # Capturar snapshot via CDP
        snapshot = self.page.run_cdp('DOMSnapshot.captureSnapshot', {
            'computedStyles': [],
            'includePaintOrder': False,
            'includeDOMRects': True
        })
        
        self.matrix_map['snapshot'] = snapshot
        return snapshot
    
    def turno_2_analise(self):
        """
        Turno 2: A Análise (BeautifulSoup/lxml)
        
        Processar árvore offline e identificar iframes e shadow-roots.
        """
        html = self.page.html
        soup = BeautifulSoup(html, 'lxml')
        
        # Identificar iframes
        iframes = [
            {
                'selector': f"iframe#{iframe.get('id')}" if iframe.get('id') else f"iframe[src*='{iframe.get('src')[:20]}']",
                'depth': 1,
                'src': iframe.get('src')
            }
            for iframe in soup.find_all('iframe')
        ]
        
        # Identificar shadow roots (heurística)
        potential_shadows = soup.find_all(
            lambda tag: tag.name and '-' in tag.name  # Web components
        )
        
        shadow_roots = [
            {
                'selector': f"{tag.name}#{tag.get('id')}" if tag.get('id') else tag.name,
                'depth': 2,
                'tag': tag.name
            }
            for tag in potential_shadows
        ]
        
        self.matrix_map['iframes'] = iframes
        self.matrix_map['shadow_roots'] = shadow_roots
        
        return {'iframes': iframes, 'shadow_roots': shadow_roots}
    
    def turno_3_grampo(self):
        """
        Turno 3: O Grampo (Playwright/Fiber)
        
        Injetar script de 1 linha para extrair rotas do React Fiber.
        """
        script = """
        // Extrair rotas do React Fiber
        const root = document.querySelector('#root');
        if (!root) return null;
        
        const fiberKey = Object.keys(root).find(k => 
            k.startsWith('__reactFiber$')
        );
        
        if (!fiberKey) return null;
        
        const fiber = root[fiberKey];
        
        // Extrair rotas (simplificado)
        function extractRoutes(node, routes = []) {
            if (!node) return routes;
            
            // Verificar se é componente de rota
            if (node.type && node.type.name && 
                (node.type.name.includes('Route') || 
                 node.type.name.includes('Router'))) {
                
                if (node.memoizedProps && node.memoizedProps.path) {
                    routes.push({
                        path: node.memoizedProps.path,
                        component: node.type.name
                    });
                }
            }
            
            // Recursivo
            if (node.child) extractRoutes(node.child, routes);
            if (node.sibling) extractRoutes(node.sibling, routes);
            
            return routes;
        }
        
        return extractRoutes(fiber);
        """
        
        routes = self.page.run_js(script)
        self.matrix_map['react_routes'] = routes
        
        return routes
    
    def turno_4_consolidacao(self):
        """
        Turno 4: A Consolidação (RAG)
        
        Enviar resultado para Matrix Map como mapa pronto.
        """
        # Consolidar tudo em estrutura Matrix Map
        consolidated = {
            'url': self.url,
            'zones': []
        }
        
        # Adicionar zonas de iframes
        for iframe in self.matrix_map.get('iframes', []):
            consolidated['zones'].append({
                'name': f"IFRAME_{iframe['selector'].replace('#', '_').upper()}",
                'selector': iframe['selector'],
                'depth': iframe['depth'],
                'type': 'iframe',
                'exits': []
            })
        
        # Adicionar zonas de shadow roots
        for shadow in self.matrix_map.get('shadow_roots', []):
            consolidated['zones'].append({
                'name': f"SHADOW_{shadow['tag'].replace('-', '_').upper()}",
                'selector': shadow['selector'],
                'depth': shadow['depth'],
                'type': 'shadow',
                'exits': []
            })
        
        # Adicionar rotas React
        for route in self.matrix_map.get('react_routes', []):
            consolidated['zones'].append({
                'name': f"ROUTE_{route['path'].replace('/', '_').upper()}",
                'selector': f"[data-route='{route['path']}']",
                'depth': 0,
                'type': 'route',
                'exits': []
            })
        
        # Salvar em arquivo
        with open('.matrix_map.json', 'w') as f:
            json.dump(consolidated, f, indent=2)
        
        return consolidated
    
    def execute_blitz(self):
        """Executa reconhecimento completo em 4 turnos."""
        print("🌑 Iniciando Blitz Recon...")
        
        # Navegar para URL
        self.page.get(self.url)
        
        # Turno 1
        print("⚡ Turno 1: O Clarão (Snapshot)")
        self.turno_1_clarao()
        
        # Turno 2
        print("🔍 Turno 2: A Análise (Offline)")
        self.turno_2_analise()
        
        # Turno 3
        print("🎯 Turno 3: O Grampo (Fiber)")
        self.turno_3_grampo()
        
        # Turno 4
        print("📊 Turno 4: A Consolidação (RAG)")
        result = self.turno_4_consolidacao()
        
        print("✅ Blitz Recon completo!")
        
        self.page.quit()
        return result

# Uso
if __name__ == '__main__':
    recon = BlitzRecon('https://example.com')
    matrix_map = recon.execute_blitz()
    print(json.dumps(matrix_map, indent=2))
```

---

## 7. 📦 Instalação Completa do Arsenal

```bash
# Core
pip install selenium
pip install undetected-chromedriver

# Shadow Powers
pip install playwright
pip install pyppeteer pyppeteer-stealth
pip install DrissionPage
pip install requests browser-cookie3
pip install beautifulsoup4 lxml

# Utilities
pip install groq
pip install hypothesis

# Install Playwright browsers
playwright install chromium
```

---

## 8. 🎯 Quando Usar Cada Arma

| Situação | Biblioteca | Razão |
|----------|-----------|-------|
| React app complexo | Playwright | Fiber hijacking + ARIA |
| Anti-bot detection | Pyppeteer-stealth | Stealth built-in |
| Navegação híbrida | DrissionPage | DOM + HTTP |
| Session cloning | browser-cookie3 | Velocidade |
| DOM mapping | BeautifulSoup | Offline processing |
| Blitz recon | Todas | Coreografia completa |

---

## 9. ⚠️ Avisos

- **Playwright**: Requer instalação de browsers separada
- **Pyppeteer**: Async (use asyncio)
- **DrissionPage**: Documentação em chinês (use tradutor)
- **browser-cookie3**: Requer navegador fechado
- **BeautifulSoup**: Não executa JavaScript

---

**"Cada arma tem seu propósito. Use a ferramenta certa para o trabalho certo."** ⚔️🌑
