# Selenium WebDriver - Documentação Simplificada

Esta é uma documentação simplificada do Selenium WebDriver focada nos conceitos essenciais para entender as abstrações do SelumOfPersistence.

**IMPORTANTE**: Você NÃO deve usar estes comandos diretamente. Use as abstrações do SelumOfPersistence listadas em Abstractions.md.

---

## O que é Selenium?

Selenium WebDriver é uma biblioteca para automação de navegadores web. Permite controlar navegadores programaticamente para testar aplicações web ou realizar tarefas automatizadas.

---

## Conceitos Fundamentais

### WebDriver

O WebDriver é o objeto principal que controla o navegador.

```python
from selenium import webdriver

# Criar instância do Chrome
driver = webdriver.Chrome()

# Navegar para URL
driver.get("https://example.com")

# Fechar navegador
driver.quit()
```

**No SelumOfPersistence**: O driver é encapsulado e gerenciado internamente. Você não precisa criar ou gerenciar o driver diretamente.

### WebElement

WebElement representa um elemento HTML na página (botão, input, div, etc.).

```python
# Localizar elemento
element = driver.find_element(By.CSS_SELECTOR, ".button")

# Interagir com elemento
element.click()
element.send_keys("texto")
element.clear()

# Obter informações
text = element.text
value = element.get_attribute("value")
is_displayed = element.is_displayed()
```

**No SelumOfPersistence**: Use `scout()` para localizar elementos e `strike()` para clicar. Elementos são gerenciados automaticamente.

---

## Estratégias de Localização (By)

Selenium oferece várias formas de localizar elementos:

```python
from selenium.webdriver.common.by import By

# Por CSS Selector
element = driver.find_element(By.CSS_SELECTOR, ".class-name")

# Por XPath
element = driver.find_element(By.XPATH, "//button[@id='submit']")

# Por ID
element = driver.find_element(By.ID, "username")

# Por Name
element = driver.find_element(By.NAME, "email")

# Por Link Text
element = driver.find_element(By.LINK_TEXT, "Click here")

# Por Partial Link Text
element = driver.find_element(By.PARTIAL_LINK_TEXT, "Click")

# Por Tag Name
element = driver.find_element(By.TAG_NAME, "button")

# Por Class Name
element = driver.find_element(By.CLASS_NAME, "btn-primary")
```

**No SelumOfPersistence**: Use `scout()` com dicionários que especificam a estratégia:
```python
element = selum.scout([
    {"css": ".class-name"},
    {"xpath": "//button[@id='submit']"},
    {"id": "username"},
    {"name": "email"},
    {"text": "Click here", "type": "link"}
])
```

---

## Esperas (Waits)

### Espera Implícita

```python
# Aguardar até 10 segundos para encontrar elementos
driver.implicitly_wait(10)
```

**Problema**: Aplica-se a TODAS as buscas, pode deixar testes lentos.

### Espera Explícita

```python
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Aguardar até elemento estar presente
element = WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.ID, "myElement"))
)

# Aguardar até elemento estar clicável
element = WebDriverWait(driver, 10).until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, ".button"))
)
```

**No SelumOfPersistence**: Use `vigilance()` que implementa espera explícita com logs de progresso:
```python
element = selum.vigilance(".button", timeout=10)
```

---

## Exceções Comuns

### NoSuchElementException

Lançada quando elemento não é encontrado.

```python
from selenium.common.exceptions import NoSuchElementException

try:
    element = driver.find_element(By.ID, "missing")
except NoSuchElementException:
    print("Elemento não encontrado")
```

**No SelumOfPersistence**: `scout()` retorna `None` ao invés de lançar exceção. `vigilance()` lança `TimeoutException` após timeout.

### TimeoutException

Lançada quando espera explícita excede o timeout.

```python
from selenium.common.exceptions import TimeoutException

try:
    element = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "slow-element"))
    )
except TimeoutException:
    print("Elemento não apareceu no tempo esperado")
```

**No SelumOfPersistence**: `vigilance()` lança `TimeoutException` com logs narrativos de progresso.

### ElementClickInterceptedException

Lançada quando outro elemento está sobrepondo o elemento alvo.

```python
from selenium.common.exceptions import ElementClickInterceptedException

try:
    element.click()
except ElementClickInterceptedException:
    print("Elemento está bloqueado por outro elemento")
```

**No SelumOfPersistence**: `strike()` com strategy='smart' automaticamente usa JavaScript click como fallback.

### StaleElementReferenceException

Lançada quando elemento foi removido ou modificado no DOM.

```python
from selenium.common.exceptions import StaleElementReferenceException

try:
    element.click()
except StaleElementReferenceException:
    print("Elemento não está mais no DOM")
```

**No SelumOfPersistence**: Sistema de detecção de erros estruturais rastreia e tenta resolver automaticamente.

### ElementNotInteractableException

Lançada quando elemento não está visível ou interagível.

```python
from selenium.common.exceptions import ElementNotInteractableException

try:
    element.click()
except ElementNotInteractableException:
    print("Elemento não está interagível")
```

**No SelumOfPersistence**: Use `steady_gaze()` para garantir visibilidade antes de interagir.

---

## JavaScript Execution

Selenium permite executar JavaScript arbitrário:

```python
# Clicar via JavaScript
driver.execute_script("arguments[0].click();", element)

# Scroll até elemento
driver.execute_script("arguments[0].scrollIntoView();", element)

# Modificar valor de input
driver.execute_script("arguments[0].value = 'texto';", element)
```

**ATENÇÃO**: Executar JavaScript direto é PROIBIDO pelo Voto de Abstração.

**No SelumOfPersistence**: 
- Use `strike(strategy='force')` para JavaScript click
- Use `steady_gaze()` para scroll
- NUNCA modifique valores via JavaScript (especialmente em campos sensíveis)

---

## ActionChains

ActionChains permite ações complexas como hover, drag-and-drop:

```python
from selenium.webdriver.common.action_chains import ActionChains

# Hover sobre elemento
ActionChains(driver).move_to_element(element).perform()

# Drag and drop
ActionChains(driver).drag_and_drop(source, target).perform()

# Click and hold
ActionChains(driver).click_and_hold(element).perform()
```

**No SelumOfPersistence**: Use `strike()` com strategy='force' para casos complexos. ActionChains direto é PROIBIDO.

---

## Navegação

```python
# Navegar para URL
driver.get("https://example.com")

# Voltar
driver.back()

# Avançar
driver.forward()

# Recarregar
driver.refresh()

# Obter URL atual
current_url = driver.current_url

# Obter título
title = driver.title
```

**No SelumOfPersistence**: Navegação básica pode ser feita através do driver, mas operações complexas devem usar abstrações.

---

## Janelas e Frames

```python
# Trocar para janela
driver.switch_to.window(window_handle)

# Trocar para frame
driver.switch_to.frame(frame_element)

# Voltar para conteúdo principal
driver.switch_to.default_content()

# Trocar para alert
alert = driver.switch_to.alert
alert.accept()  # Clicar OK
alert.dismiss()  # Clicar Cancel
```

**No SelumOfPersistence**: Operações de janela/frame podem ser feitas diretamente, mas considere criar abstrações se usar frequentemente.

---

## Screenshots

```python
# Screenshot da página inteira
driver.save_screenshot("screenshot.png")

# Screenshot de elemento específico
element.screenshot("element.png")
```

**No SelumOfPersistence**: Screenshots podem ser úteis para debugging. Considere adicionar ao logging narrativo.

---

## Cookies

```python
# Adicionar cookie
driver.add_cookie({"name": "key", "value": "value"})

# Obter cookie
cookie = driver.get_cookie("key")

# Obter todos os cookies
cookies = driver.get_cookies()

# Deletar cookie
driver.delete_cookie("key")

# Deletar todos os cookies
driver.delete_all_cookies()
```

**No SelumOfPersistence**: Gerenciamento de cookies pode ser feito diretamente quando necessário.

---

## Resumo: Selenium vs SelumOfPersistence

| Operação | Selenium Bruto (PROIBIDO) | SelumOfPersistence (CORRETO) |
|----------|---------------------------|------------------------------|
| Clicar | `driver.find_element().click()` | `selum.strike(".button")` |
| Localizar | `driver.find_element(By.CSS, ".el")` | `selum.scout([{"css": ".el"}])` |
| Aguardar | `WebDriverWait(driver, 10).until(...)` | `selum.vigilance(".el", timeout=10)` |
| Scroll | `driver.execute_script("...scrollIntoView")` | `selum.steady_gaze(".el")` |
| Remover overlay | `driver.execute_script("...remove()")` | `selum.cleansing_aura()` |
| JS Click | `driver.execute_script("...click()")` | `selum.strike(".el", strategy='force')` |

---

## Referências

- Documentação oficial: https://www.selenium.dev/documentation/
- Python bindings: https://selenium-python.readthedocs.io/
- Expected Conditions: https://www.selenium.dev/selenium/docs/api/py/webdriver_support/selenium.webdriver.support.expected_conditions.html

**Lembre-se**: Esta documentação é apenas para referência. SEMPRE use as abstrações do SelumOfPersistence ao invés de Selenium bruto.
