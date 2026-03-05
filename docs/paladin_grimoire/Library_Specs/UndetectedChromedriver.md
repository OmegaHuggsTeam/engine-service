# Undetected Chromedriver - Documentação Simplificada

Esta é uma documentação simplificada do undetected-chromedriver focada nos conceitos essenciais para evitar detecção de automação.

**IMPORTANTE**: O SelumOfPersistence já usa undetected-chromedriver internamente. Você não precisa configurá-lo diretamente.

---

## O que é Undetected Chromedriver?

Undetected Chromedriver é uma versão modificada do Selenium ChromeDriver que evita detecção por sistemas anti-bot. Sites modernos usam várias técnicas para detectar automação (Selenium, Puppeteer, etc.) e bloquear bots.

**Repositório**: https://github.com/ultrafunkamsterdam/undetected-chromedriver

---

## Por que Usar?

Sites modernos detectam Selenium através de:

1. **Propriedade `navigator.webdriver`**: Selenium define como `true`
2. **Chrome DevTools Protocol**: Detectável via CDP
3. **Padrões de comportamento**: Movimentos de mouse não-humanos, timing perfeito
4. **Fingerprinting**: Análise de características do navegador

Undetected Chromedriver:
- Remove propriedade `navigator.webdriver`
- Oculta sinais de automação
- Usa perfil de usuário real
- Randomiza timing e comportamento

---

## Instalação

```bash
pip install undetected-chromedriver
```

**No SelumOfPersistence**: Já instalado e configurado. Não precisa instalar manualmente.

---

## Uso Básico

```python
import undetected_chromedriver as uc

# Criar driver
driver = uc.Chrome()

# Usar como Selenium normal
driver.get("https://example.com")
element = driver.find_element("css selector", ".button")
element.click()

# Fechar
driver.quit()
```

**No SelumOfPersistence**: O driver é criado e gerenciado internamente. Use as abstrações normalmente.

---

## Opções de Configuração

### Headless Mode

```python
options = uc.ChromeOptions()
options.add_argument('--headless')
driver = uc.Chrome(options=options)
```

**Atenção**: Headless mode pode ser detectado por alguns sites. Use com cuidado.

### User Data Directory

```python
# Usar perfil de usuário existente
driver = uc.Chrome(user_data_dir="/path/to/profile")
```

**Benefício**: Mantém cookies, histórico e configurações entre execuções.

### Versão do Chrome

```python
# Especificar versão do Chrome
driver = uc.Chrome(version_main=120)
```

**Uso**: Útil quando Chrome atualiza e driver precisa ser compatível.

### Proxy

```python
options = uc.ChromeOptions()
options.add_argument('--proxy-server=http://proxy:port')
driver = uc.Chrome(options=options)
```

### Desabilitar Imagens (Performance)

```python
options = uc.ChromeOptions()
prefs = {"profile.managed_default_content_settings.images": 2}
options.add_experimental_option("prefs", prefs)
driver = uc.Chrome(options=options)
```

---

## Técnicas Anti-Detecção

### 1. Randomizar User Agent

```python
options = uc.ChromeOptions()
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...')
driver = uc.Chrome(options=options)
```

### 2. Desabilitar Automação Flags

```python
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
driver = uc.Chrome(options=options)
```

**Nota**: Undetected Chromedriver já faz isso automaticamente.

### 3. Usar Perfil Real

```python
# Usar perfil do Chrome do usuário
driver = uc.Chrome(user_data_dir="C:/Users/User/AppData/Local/Google/Chrome/User Data")
```

**Benefício**: Site vê sessão como usuário real com histórico.

### 4. Adicionar Delays Humanos

```python
import time
import random

# Delay aleatório entre ações
time.sleep(random.uniform(0.5, 2.0))
```

**No SelumOfPersistence**: Considere adicionar delays em skills customizadas para parecer mais humano.

---

## Limitações

### 1. Não é 100% Indetectável

Sites sofisticados (Cloudflare, PerimeterX, DataDome) podem ainda detectar:
- Padrões de comportamento
- Fingerprinting avançado
- Análise de rede
- Machine learning

### 2. Requer Manutenção

Chrome atualiza frequentemente. Undetected Chromedriver precisa ser atualizado para manter compatibilidade.

### 3. Performance

Undetected Chromedriver pode ser ligeiramente mais lento que ChromeDriver normal devido às técnicas anti-detecção.

---

## Melhores Práticas

### 1. Sempre Usar Delays

```python
# Adicionar delay entre ações
import time
time.sleep(1)  # 1 segundo

# Delay aleatório (mais humano)
import random
time.sleep(random.uniform(0.5, 2.0))
```

### 2. Evitar Padrões Óbvios

```python
# MAU: Timing perfeito
for i in range(10):
    click_button()
    time.sleep(1.0)  # Sempre 1 segundo

# BOM: Timing variável
for i in range(10):
    click_button()
    time.sleep(random.uniform(0.8, 1.5))
```

### 3. Simular Comportamento Humano

```python
# Scroll gradual ao invés de instantâneo
for i in range(0, 1000, 100):
    driver.execute_script(f"window.scrollTo(0, {i});")
    time.sleep(0.1)
```

**No SelumOfPersistence**: `steady_gaze()` já faz scroll suave.

### 4. Usar Perfil de Usuário

```python
# Manter cookies e sessões
driver = uc.Chrome(user_data_dir="./chrome_profile")
```

### 5. Rotacionar User Agents

```python
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...",
    "Mozilla/5.0 (X11; Linux x86_64) ..."
]

options = uc.ChromeOptions()
options.add_argument(f'--user-agent={random.choice(user_agents)}')
driver = uc.Chrome(options=options)
```

---

## Detecção de Cloudflare

Cloudflare é um dos sistemas anti-bot mais sofisticados. Técnicas para passar:

### 1. Aguardar Challenge Completar

```python
# Aguardar até 30 segundos para Cloudflare challenge
time.sleep(30)
```

### 2. Usar Cookies de Sessão Válida

```python
# Salvar cookies após passar Cloudflare manualmente
cookies = driver.get_cookies()

# Reusar cookies em próxima execução
for cookie in cookies:
    driver.add_cookie(cookie)
```

### 3. Usar Proxy Residencial

```python
# Proxies residenciais são menos detectáveis
options = uc.ChromeOptions()
options.add_argument('--proxy-server=http://residential-proxy:port')
driver = uc.Chrome(options=options)
```

---

## Debugging

### Verificar se Detecção Está Funcionando

```python
# Testar em site que detecta automação
driver.get("https://bot.sannysoft.com/")

# Verificar navigator.webdriver
is_detected = driver.execute_script("return navigator.webdriver")
print(f"Detectado: {is_detected}")  # Deve ser None ou undefined
```

### Verificar Chrome DevTools Protocol

```python
# CDP não deve estar ativo
cdp_active = driver.execute_script(
    "return window.chrome && window.chrome.runtime"
)
print(f"CDP Ativo: {cdp_active}")
```

---

## Integração com SelumOfPersistence

O SelumOfPersistence já usa undetected-chromedriver internamente. Configurações recomendadas:

```python
import undetected_chromedriver as uc
from src.utils.selum_of_persistence import SelumOfPersistence

# Criar driver com configurações anti-detecção
options = uc.ChromeOptions()
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument('--start-maximized')

driver = uc.Chrome(options=options, use_subprocess=True)

# Criar Selum com driver configurado
selum = SelumOfPersistence(driver, groq_api_key="your_key")

# Usar abstrações normalmente
selum.strike(".button")
```

---

## Troubleshooting

### Erro: "Chrome version must be specified"

```python
# Especificar versão do Chrome
driver = uc.Chrome(version_main=120)
```

### Erro: "Chrome binary not found"

```python
# Especificar caminho do Chrome
options = uc.ChromeOptions()
options.binary_location = "/path/to/chrome"
driver = uc.Chrome(options=options)
```

### Site Ainda Detecta Automação

1. Verificar se undetected-chromedriver está atualizado
2. Adicionar delays entre ações
3. Usar perfil de usuário real
4. Considerar proxy residencial
5. Verificar fingerprinting avançado

---

## Alternativas

Se undetected-chromedriver não funcionar:

1. **Playwright Stealth**: Similar ao UC mas para Playwright
2. **Puppeteer Extra Stealth**: Para Node.js
3. **Selenium Stealth**: Plugin para Selenium
4. **Proxies Rotativos**: Mudar IP frequentemente
5. **CAPTCHA Solving Services**: 2Captcha, Anti-Captcha

---

## Referências

- GitHub: https://github.com/ultrafunkamsterdam/undetected-chromedriver
- Documentação Selenium: https://www.selenium.dev/documentation/
- Bot Detection Tests: https://bot.sannysoft.com/
- Cloudflare Challenge: https://www.cloudflare.com/learning/bots/what-is-a-bot/

**Lembre-se**: Use automação de forma ética e respeite os termos de serviço dos sites.
