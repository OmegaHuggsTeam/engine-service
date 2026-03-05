# 🎭 Behavioral Mimicry - Simulação de Comportamento Humano

## ⚠️ CLASSIFICAÇÃO: ADMIN ONLY

Este documento descreve técnicas avançadas para simular comportamento humano e evitar detecção por sistemas de **Behavioral Biometrics** (impressão digital comportamental).

---

## 1. 🌊 Camada de Ruído Cinético (Micro-Movimentos)

### Problema

Humanos não clicam em pontos estáticos `(x, y)`. O cursor **flutua** antes de clicar. Bots clicam em coordenadas exatas instantaneamente.

### Solução: Curva de Bezier Aleatória

```python
import random
import time
import math

def bezier_curve(start, end, control_points=2):
    """
    Gera curva de Bezier para movimento de mouse humanizado.
    
    Args:
        start: Tupla (x, y) inicial
        end: Tupla (x, y) final
        control_points: Número de pontos de controle
        
    Returns:
        Lista de pontos (x, y) ao longo da curva
    """
    # Gerar pontos de controle aleatórios
    controls = []
    for _ in range(control_points):
        x = random.uniform(start[0], end[0])
        y = random.uniform(start[1], end[1])
        controls.append((x, y))
    
    # Calcular pontos da curva
    points = []
    steps = random.randint(15, 30)  # Número variável de passos
    
    for i in range(steps):
        t = i / steps
        
        # Bezier quadrática (2 pontos de controle)
        if control_points == 2:
            x = (1-t)**3 * start[0] + \
                3*(1-t)**2*t * controls[0][0] + \
                3*(1-t)*t**2 * controls[1][0] + \
                t**3 * end[0]
            
            y = (1-t)**3 * start[1] + \
                3*(1-t)**2*t * controls[0][1] + \
                3*(1-t)*t**2 * controls[1][1] + \
                t**3 * end[1]
        
        points.append((int(x), int(y)))
    
    return points

def kinetic_noise_click(driver, element):
    """
    Click com ruído cinético (micro-movimentos).
    
    Args:
        driver: WebDriver instance
        element: WebElement alvo
        
    Returns:
        True se bem-sucedido
    """
    # Obter posição do elemento
    location = element.location
    size = element.size
    
    # Calcular centro do elemento
    target_x = location['x'] + size['width'] / 2
    target_y = location['y'] + size['height'] / 2
    
    # Adicionar flutuação aleatória (±5px)
    target_x += random.uniform(-5, 5)
    target_y += random.uniform(-5, 5)
    
    # Posição inicial aleatória
    start_x = random.randint(0, driver.execute_script('return window.innerWidth'))
    start_y = random.randint(0, driver.execute_script('return window.innerHeight'))
    
    # Gerar curva de Bezier
    curve = bezier_curve((start_x, start_y), (target_x, target_y))
    
    # Simular movimento ao longo da curva
    script = """
    const points = arguments[0];
    let i = 0;
    
    function moveNext() {
        if (i >= points.length) return;
        
        const [x, y] = points[i];
        const event = new MouseEvent('mousemove', {
            clientX: x,
            clientY: y,
            bubbles: true
        });
        
        document.dispatchEvent(event);
        i++;
        
        if (i < points.length) {
            setTimeout(moveNext, Math.random() * 10 + 5);  // 5-15ms entre pontos
        }
    }
    
    moveNext();
    """
    
    driver.execute_script(script, curve)
    
    # Aguardar movimento completar
    time.sleep(len(curve) * 0.01)
    
    # Click final
    element.click()
    
    return True
```

### Rastro Humano: Eventos de Intenção

```python
def generate_intention_trail(driver, target_element, decoy_elements):
    """
    Gera rastro de intenção (mousemove/mouseenter em elementos próximos).
    
    Preenche logs de telemetria com "intenção de movimento".
    
    Args:
        driver: WebDriver instance
        target_element: Elemento alvo real
        decoy_elements: Elementos "decoy" para gerar ruído
    """
    script = """
    const target = arguments[0];
    const decoys = arguments[1];
    
    // Disparar eventos em decoys primeiro
    decoys.forEach((decoy, index) => {
        setTimeout(() => {
            // MouseEnter
            const enterEvent = new MouseEvent('mouseenter', {
                bubbles: true,
                cancelable: true
            });
            decoy.dispatchEvent(enterEvent);
            
            // MouseMove
            const moveEvent = new MouseEvent('mousemove', {
                bubbles: true,
                cancelable: true
            });
            decoy.dispatchEvent(moveEvent);
            
        }, index * 100);  // 100ms entre cada decoy
    });
    
    // Finalmente, target
    setTimeout(() => {
        const enterEvent = new MouseEvent('mouseenter', {
            bubbles: true,
            cancelable: true
        });
        target.dispatchEvent(enterEvent);
    }, decoys.length * 100 + 200);
    """
    
    driver.execute_script(script, target_element, decoy_elements)
    
    # Aguardar eventos completarem
    time.sleep((len(decoy_elements) * 0.1) + 0.3)
```

---

## 2. 👻 Mimetismo de Fluxo (Ghost Breadcrumbs)

### Problema

"Teletransporte" entre páginas é detectável. Humanos navegam através de páginas intermediárias.

### Solução: Matrix Click Ultra-Rápido em Intermediários

```python
def ghost_breadcrumbs(driver, path):
    """
    Navega através de páginas intermediárias ultra-rápido.
    
    Garante que servidor registre GET/POST intermediários.
    
    Args:
        driver: WebDriver instance
        path: Lista de seletores do caminho [A, B, C, D]
        
    Example:
        # Em vez de A → D, fazer A → B → C → D
        ghost_breadcrumbs(driver, [
            'a[href="/step1"]',
            'a[href="/step2"]',
            'a[href="/step3"]',
            'button.final'
        ])
    """
    for i, selector in enumerate(path):
        # Encontrar elemento
        element = driver.find_element(By.CSS_SELECTOR, selector)
        
        # Matrix click (trusted via CDP)
        driver.execute_cdp_cmd('Runtime.evaluate', {
            'expression': f"""
                const el = document.querySelector('{selector}');
                if (el) el.click();
            """,
            'userGesture': True
        })
        
        # Aguardar navegação (se não for último)
        if i < len(path) - 1:
            # Aguardo mínimo (50-150ms)
            time.sleep(random.uniform(0.05, 0.15))
            
            # Cleansing Aura: Fechar pop-ups/anúncios
            cleansing_aura(driver)
    
    return True

def cleansing_aura(driver):
    """
    Remove pop-ups e anúncios que podem travar navegação.
    
    Args:
        driver: WebDriver instance
    """
    script = """
    // Fechar modais comuns
    const closeSelectors = [
        '[class*="close"]',
        '[class*="dismiss"]',
        '[aria-label*="close"]',
        '[aria-label*="Close"]',
        'button[class*="modal-close"]'
    ];
    
    closeSelectors.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            if (el.offsetParent !== null) {  // Visível
                el.click();
            }
        });
    });
    
    // Remover overlays
    const overlays = document.querySelectorAll('[class*="overlay"], [class*="backdrop"]');
    overlays.forEach(overlay => overlay.remove());
    """
    
    driver.execute_script(script)
```

---

## 3. ⏱️ Assinatura de Hesitação (Cognitive Latency)

### Problema

Bots agem em 0.1s após carga. Humanos levam 0.8s+ para "entender" o layout.

### Solução: Human Delay Baseado em Complexidade

```python
def calculate_page_complexity(driver):
    """
    Calcula complexidade da página baseado em número de elementos.
    
    Args:
        driver: WebDriver instance
        
    Returns:
        Score de complexidade (0-1)
    """
    script = """
    // Contar elementos interativos
    const interactive = document.querySelectorAll(
        'a, button, input, select, textarea, [onclick], [role="button"]'
    ).length;
    
    // Contar imagens
    const images = document.querySelectorAll('img').length;
    
    // Contar texto
    const textLength = document.body.innerText.length;
    
    return {
        interactive: interactive,
        images: images,
        textLength: textLength
    };
    """
    
    metrics = driver.execute_script(script)
    
    # Calcular score (normalizado 0-1)
    complexity = (
        (metrics['interactive'] / 50) * 0.4 +  # Peso 40%
        (metrics['images'] / 20) * 0.3 +        # Peso 30%
        (metrics['textLength'] / 5000) * 0.3    # Peso 30%
    )
    
    return min(complexity, 1.0)  # Cap em 1.0

def cognitive_latency(driver, base_delay=0.8):
    """
    Aguarda tempo baseado em complexidade da página.
    
    Simula tempo de "leitura" do usuário.
    
    Args:
        driver: WebDriver instance
        base_delay: Delay base em segundos (padrão: 0.8s)
        
    Returns:
        Tempo aguardado em segundos
    """
    complexity = calculate_page_complexity(driver)
    
    # Calcular delay
    # Páginas simples: 0.8-1.2s
    # Páginas complexas: 1.5-2.5s
    min_delay = base_delay
    max_delay = base_delay + (complexity * 1.5)
    
    delay = random.uniform(min_delay, max_delay)
    
    # Adicionar micro-pausas (simular leitura)
    chunks = int(delay / 0.3)  # Dividir em chunks de 300ms
    for _ in range(chunks):
        time.sleep(0.3 + random.uniform(-0.05, 0.05))
    
    # Resto
    remaining = delay - (chunks * 0.3)
    if remaining > 0:
        time.sleep(remaining)
    
    return delay
```

---

## 4. 🪞 Mirror Walk - Caminhada no Espelho

### Conceito

Skill completa que combina todas as técnicas de mimicry para navegação ultra-realista.

### Implementação

```python
class MirrorWalk:
    """
    Skill avançada de navegação com simulação comportamental completa.
    
    Fases:
    1. Observação: Gera eventos fantasma de mouse
    2. Ativação: Dispara eventos de focus em elementos
    3. Salto: Executa transição de estado real
    """
    
    def __init__(self, driver):
        self.driver = driver
    
    def fase_observacao(self, duration_ms=500):
        """
        Fase 1: Observação
        
        Gera "fantasma" de eventos de mouse aleatórios.
        
        Args:
            duration_ms: Duração da fase em milissegundos
        """
        script = f"""
        const duration = {duration_ms};
        const startTime = Date.now();
        
        function generateGhostEvent() {{
            const elapsed = Date.now() - startTime;
            if (elapsed >= duration) return;
            
            // Posição aleatória
            const x = Math.random() * window.innerWidth;
            const y = Math.random() * window.innerHeight;
            
            // Evento de mousemove
            const event = new MouseEvent('mousemove', {{
                clientX: x,
                clientY: y,
                bubbles: true
            }});
            
            document.dispatchEvent(event);
            
            // Próximo evento (10-50ms)
            setTimeout(generateGhostEvent, Math.random() * 40 + 10);
        }}
        
        generateGhostEvent();
        """
        
        self.driver.execute_script(script)
        time.sleep(duration_ms / 1000)
    
    def fase_ativacao(self, navigation_elements):
        """
        Fase 2: Ativação
        
        Dispara eventos de focus em elementos do menu.
        
        Args:
            navigation_elements: Lista de seletores de navegação
        """
        script = """
        const selectors = arguments[0];
        
        selectors.forEach((selector, index) => {
            setTimeout(() => {
                const element = document.querySelector(selector);
                if (element) {
                    // Focus event
                    const focusEvent = new FocusEvent('focus', {
                        bubbles: true
                    });
                    element.dispatchEvent(focusEvent);
                    
                    // MouseEnter event
                    const enterEvent = new MouseEvent('mouseenter', {
                        bubbles: true
                    });
                    element.dispatchEvent(enterEvent);
                }
            }, index * 100);
        });
        """
        
        self.driver.execute_script(script, navigation_elements)
        time.sleep(len(navigation_elements) * 0.1 + 0.2)
    
    def fase_salto(self, target_selector, intermediate_path=None):
        """
        Fase 3: Salto
        
        Executa transição de estado real após eventos falsos.
        
        Args:
            target_selector: Seletor do elemento alvo
            intermediate_path: Caminho intermediário (opcional)
        """
        # Se há caminho intermediário, usar ghost breadcrumbs
        if intermediate_path:
            ghost_breadcrumbs(self.driver, intermediate_path + [target_selector])
        else:
            # Click direto com ruído cinético
            element = self.driver.find_element(By.CSS_SELECTOR, target_selector)
            kinetic_noise_click(self.driver, element)
    
    def execute(self, target_selector, navigation_elements=None, intermediate_path=None):
        """
        Executa Mirror Walk completo.
        
        Args:
            target_selector: Seletor do elemento alvo
            navigation_elements: Elementos de navegação para fase de ativação
            intermediate_path: Caminho intermediário para ghost breadcrumbs
            
        Returns:
            True se bem-sucedido
            
        Example:
            mirror = MirrorWalk(driver)
            mirror.execute(
                target_selector='button.submit',
                navigation_elements=['nav a.home', 'nav a.products', 'nav a.cart'],
                intermediate_path=['a[href="/step1"]', 'a[href="/step2"]']
            )
        """
        # Fase 1: Observação (500ms de eventos fantasma)
        self.fase_observacao(duration_ms=500)
        
        # Fase 2: Ativação (focus em elementos de navegação)
        if navigation_elements:
            self.fase_ativacao(navigation_elements)
        
        # Cognitive Latency (hesitação humana)
        cognitive_latency(self.driver, base_delay=0.8)
        
        # Fase 3: Salto (transição real)
        self.fase_salto(target_selector, intermediate_path)
        
        return True
```

### Exemplo de Uso Completo

```python
from selenium import webdriver

# Inicializar driver
driver = webdriver.Chrome()
driver.get('https://example.com')

# Criar Mirror Walk
mirror = MirrorWalk(driver)

# Executar navegação ultra-realista
mirror.execute(
    target_selector='button#checkout',
    navigation_elements=[
        'nav a.home',
        'nav a.products',
        'nav a.cart'
    ],
    intermediate_path=[
        'a[href="/products"]',
        'button.add-to-cart',
        'a[href="/cart"]'
    ]
)

driver.quit()
```

---

## 5. 🎯 Integração com SelumOfPersistence

### Adicionar ao Grimoire

```python
class SelumOfPersistence:
    """Paladino com Mirror Walk."""
    
    def __init__(self, driver, groq_api_key=None):
        self.driver = driver
        self.mirror = MirrorWalk(driver)
        # ... resto da inicialização
    
    def mirror_walk(self, target_selector, navigation_elements=None, intermediate_path=None):
        """
        Executa Mirror Walk (navegação ultra-realista).
        
        Combina:
        - Ruído cinético (micro-movimentos)
        - Ghost breadcrumbs (páginas intermediárias)
        - Cognitive latency (hesitação humana)
        
        Args:
            target_selector: Seletor do elemento alvo
            navigation_elements: Elementos de navegação
            intermediate_path: Caminho intermediário
            
        Returns:
            True se bem-sucedido
        """
        self.logger.wisdom(f"🪞 Iniciando Mirror Walk para {target_selector}")
        
        try:
            result = self.mirror.execute(
                target_selector,
                navigation_elements,
                intermediate_path
            )
            
            self.logger.result(f"✅ Mirror Walk concluído")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Mirror Walk falhou: {e}")
            return False
```

---

## 6. 📊 Métricas de Humanização

### Checklist de Comportamento Humano

- ✅ **Movimento de mouse**: Curva de Bezier (não linear)
- ✅ **Flutuação de click**: ±5px do centro
- ✅ **Eventos de intenção**: MouseEnter em elementos próximos
- ✅ **Navegação intermediária**: Ghost breadcrumbs
- ✅ **Hesitação cognitiva**: 0.8-2.5s baseado em complexidade
- ✅ **Micro-pausas**: Chunks de 300ms (simular leitura)
- ✅ **Timing variável**: Random entre ações

### Comparação: Bot vs Humano vs Mirror Walk

| Métrica | Bot | Humano | Mirror Walk |
|---------|-----|--------|-------------|
| Movimento mouse | Linear | Curva | Curva Bezier ✅ |
| Click position | Exato | ±5px | ±5px ✅ |
| Tempo de reação | 0.1s | 0.8-2.5s | 0.8-2.5s ✅ |
| Eventos de intenção | ❌ | ✅ | ✅ |
| Navegação | Direta | Intermediária | Ghost breadcrumbs ✅ |
| Hesitação | ❌ | ✅ | Cognitive latency ✅ |

---

## 7. ⚠️ Avisos

### Limitações

- **Não é 100% indetectável**: Sistemas avançados podem detectar
- **Performance**: Mais lento que automação direta
- **Complexidade**: Requer tuning para cada site

### Quando Usar

- ✅ Sites com behavioral biometrics
- ✅ Sistemas anti-bot avançados
- ✅ Navegação crítica (login, checkout)
- ❌ Scraping em massa (muito lento)
- ❌ APIs (não precisam de mimicry)

### Ética

Use apenas para:
- Testes em suas próprias aplicações
- Automação legítima com permissão
- Pesquisa de segurança autorizada

---

## 8. 📚 Referências

- **Behavioral Biometrics**: Mouse dynamics, keystroke dynamics
- **Bezier Curves**: Smooth mouse movement
- **Cognitive Load Theory**: Human reaction times
- **Web Analytics**: Google Analytics event tracking

---

**"Imitar é a forma mais sincera de bypass."** 🎭🪞
