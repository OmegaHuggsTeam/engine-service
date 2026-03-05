# Abstractions - Manobras do Selum of Persistence

Este documento lista todas as manobras (abstrações) disponíveis no SelumOfPersistence. Cada manobra encapsula operações Selenium em métodos resilientes e seguros.

**REGRA CRÍTICA**: Você NUNCA deve usar código Selenium bruto (driver.find_element, driver.execute_script direto). Use APENAS as abstrações listadas aqui.

## strike

**Assinatura**: `strike(selector: Union[str, WebElement], by: str = By.CSS_SELECTOR, strategy: str = 'smart') -> bool`

**Descrição**: Executa um clique resiliente com fallback automático. Tenta clique normal e, se falhar por interceptação, usa JavaScript click (Injeção de Força).

**Parâmetros**:
- `selector`: Seletor CSS, XPath, ou WebElement já localizado
- `by`: Tipo de seletor (By.CSS_SELECTOR, By.XPATH, etc.)
- `strategy`: Estratégia de clique
  - `'smart'`: Tenta clique normal → JS click se falhar (padrão)
  - `'force'`: Usa JS click direto
  - `'gentle'`: Apenas clique normal (sem fallback)

**Retorna**: `True` se o clique foi bem-sucedido

**Exemplo**:
```python
# Clique simples com fallback automático
selum.strike(".settings-button")

# Clique forçado com JavaScript
selum.strike("#submit", strategy='force')

# Clique em elemento já localizado
element = selum.scout([{"css": ".item"}])
selum.strike(element)

# Clique com XPath
selum.strike("//button[@id='confirm']", by=By.XPATH)
```

**Quando Usar**: Sempre que precisar clicar em elementos. Nunca use `driver.find_element().click()` ou `driver.execute_script("...click()")` direto.

---

## scout

**Assinatura**: `scout(possibilities_list: List[Dict[str, str]]) -> Optional[WebElement]`

**Descrição**: Reconhece o terreno e retorna o primeiro caminho seguro encontrado. Busca elemento testando múltiplas estratégias de localização (útil para diferentes idiomas ou estruturas de página).

**Parâmetros**:
- `possibilities_list`: Lista de possíveis seletores/textos. Formato aceito:
  ```python
  [
      {"text": "Definições", "type": "link"},
      {"text": "Settings", "type": "button"},
      {"css": ".settings-btn"},
      {"xpath": "//button[@id='settings']"},
      {"id": "settings-button"},
      {"name": "settings_field"}
  ]
  ```

**Retorna**: Primeiro `WebElement` encontrado ou `None` se nenhum caminho for encontrado

**Exemplo**:
```python
# Buscar botão de configurações em múltiplos idiomas
element = selum.scout([
    {"text": "Definições"},
    {"text": "Settings"},
    {"text": "Configuración"},
    {"css": ".settings-btn"}
])

# Buscar campo de entrada com múltiplas estratégias
input_field = selum.scout([
    {"id": "username"},
    {"name": "user"},
    {"css": "input[type='text']"},
    {"xpath": "//input[@placeholder='Username']"}
])
```

**Quando Usar**: Quando precisa localizar elemento com múltiplas estratégias de fallback. Nunca use `driver.find_element()` direto.

---

## vigilance

**Assinatura**: `vigilance(selector: str, timeout: int = 20, by: str = By.CSS_SELECTOR) -> WebElement`

**Descrição**: Aguarda um elemento aparecer com logs de progresso. Implementa espera inteligente que reporta progresso a cada 5 segundos.

**Parâmetros**:
- `selector`: Seletor do elemento a aguardar
- `timeout`: Tempo máximo de espera em segundos (padrão: 20)
- `by`: Tipo de seletor (By.CSS_SELECTOR, By.XPATH, etc.)

**Retorna**: `WebElement` encontrado

**Lança**: `TimeoutException` se o elemento não aparecer no tempo limite

**Exemplo**:
```python
# Aguardar campo de API key aparecer
element = selum.vigilance(".api-key-field", timeout=30)

# Aguardar modal de confirmação
modal = selum.vigilance("//div[@role='dialog']", timeout=10, by=By.XPATH)

# Aguardar botão de submit ficar disponível
submit_btn = selum.vigilance("#submit-button", timeout=15)
```

**Quando Usar**: Sempre que precisar aguardar elemento aparecer. Nunca use `WebDriverWait()` direto.

---

## steady_gaze

**Assinatura**: `steady_gaze(selector: Union[str, WebElement], by: str = By.CSS_SELECTOR) -> WebElement`

**Descrição**: Move o foco (scroll) até o elemento para garantir visibilidade. Garante que elemento esteja visível no viewport antes de qualquer interação.

**Parâmetros**:
- `selector`: Seletor CSS, XPath, ou WebElement já localizado
- `by`: Tipo de seletor (By.CSS_SELECTOR, By.XPATH, etc.)

**Retorna**: `WebElement` focado

**Exemplo**:
```python
# Scroll até botão escondido
element = selum.steady_gaze(".hidden-button")

# Scroll até elemento já localizado
element = selum.scout([{"css": ".item"}])
selum.steady_gaze(element)

# Scroll até elemento com XPath
selum.steady_gaze("//div[@class='footer']", by=By.XPATH)
```

**Quando Usar**: Quando precisa garantir que elemento está visível antes de interagir. Previne erros de elemento não interagível.

---

## cleansing_aura

**Assinatura**: `cleansing_aura() -> int`

**Descrição**: Remove overlays, modais e pop-ups que bloqueiam o caminho. Tenta identificar e remover obstáculos comuns que impedem interação com elementos.

**Retorna**: Número de obstáculos removidos

**Exemplo**:
```python
# Remover pop-ups e overlays antes de interagir
removed_count = selum.cleansing_aura()
print(f"Removidos {removed_count} obstáculos")

# Usar antes de clicar em elemento que pode estar bloqueado
selum.cleansing_aura()
selum.strike(".target-button")
```

**Quando Usar**: Quando suspeitar que overlays ou modais estão bloqueando interação. Útil antes de operações críticas.

---

## invoke_wisdom

**Assinatura**: `invoke_wisdom(exception: Exception, traceback_str: str) -> Dict[str, Any]`

**Descrição**: Invoca a sabedoria dos Anciões (AgentFactory) quando uma manobra falha. Conecta o Paladino ao sistema de aprendizado, permitindo que falhas sejam analisadas e novas estratégias sejam adicionadas ao grimório.

**Parâmetros**:
- `exception`: Exceção que ocorreu durante a manobra
- `traceback_str`: Traceback completo da exceção

**Retorna**: Dicionário com resposta do AgentFactory contendo:
- `specialist_name`: Nome do especialista (selenium)
- `specialist_exists`: Se o especialista já existia
- `combat_maneuvers_applied`: Manobras aplicadas
- `evolution_triggered`: Se houve evolução
- `suggested_solution`: Solução sugerida
- `error`: Mensagem de erro (se houver)

**Exemplo**:
```python
try:
    selum.strike(".non-existent")
except Exception as e:
    response = selum.invoke_wisdom(e, traceback.format_exc())
    print(response['suggested_solution'])
```

**Quando Usar**: Automaticamente chamado quando manobras falham. Não precisa chamar manualmente.

---

## divine_inspiration

**Assinatura**: `divine_inspiration(context_description: str) -> Dict[str, Any]`

**Descrição**: Invoca Inspiração Divina para gerar nova skill customizada quando erro estrutural é detectado repetidamente (3+ vezes). Usa Groq LLM para gerar código, valida com AlchemistsFilter e SkillExecutor, e persiste no grimório se bem-sucedida.

**Parâmetros**:
- `context_description`: Descrição do contexto do erro

**Retorna**: Dicionário com resultado:
- `success`: Se skill foi gerada e executada com sucesso
- `skill_name`: Nome da skill gerada
- `code`: Código da skill
- `error`: Mensagem de erro (se houver)

**Exemplo**:
```python
# Invocar Divine Inspiration para resolver problema específico
context = "NoSuchElementException ao buscar botão de login após 3 tentativas"
result = selum.divine_inspiration(context)

if result['success']:
    print(f"Skill '{result['skill_name']}' criada e executada com sucesso!")
```

**Quando Usar**: Automaticamente invocado após 3 falhas estruturais consecutivas. Não precisa chamar manualmente.

---

## execute_skill

**Assinatura**: `execute_skill(skill_name: str) -> bool`

**Descrição**: Executa uma skill customizada previamente criada e registrada no skill_registry.

**Parâmetros**:
- `skill_name`: Nome da skill a executar (ex: "skill_handle_cookie_popup")

**Retorna**: `True` se skill executou com sucesso, `False` caso contrário

**Exemplo**:
```python
# Executar skill customizada
success = selum.execute_skill("skill_handle_cookie_popup")

if success:
    print("Skill executada com sucesso!")
else:
    print("Skill falhou")
```

**Quando Usar**: Para executar skills customizadas criadas pelo Divine Inspiration. Automaticamente tentado quando erro estrutural é detectado.

---

## combo_login

**Assinatura**: `combo_login(username: str, password: str, username_selector: str = "#username", password_selector: str = "#password", submit_selector: str = "button[type='submit']") -> bool`

**Descrição**: Combo de manobras para realizar login. Sequência pré-definida de ações para facilitar logins.

**Parâmetros**:
- `username`: Nome de usuário
- `password`: Senha
- `username_selector`: Seletor do campo de usuário (padrão: "#username")
- `password_selector`: Seletor do campo de senha (padrão: "#password")
- `submit_selector`: Seletor do botão de submit (padrão: "button[type='submit']")

**Retorna**: `True` se login foi bem-sucedido

**Exemplo**:
```python
# Login com seletores padrão
selum.combo_login("user@example.com", "senha123")

# Login com seletores customizados
selum.combo_login(
    "user@example.com",
    "senha123",
    username_selector=".username-field",
    password_selector=".password-field",
    submit_selector="#login-button"
)
```

**Quando Usar**: Para realizar login de forma rápida e resiliente.

**Status**: Implementação futura (Fase 6)

---

## combo_navigate_to_settings

**Assinatura**: `combo_navigate_to_settings(settings_possibilities: Optional[List[Dict[str, str]]] = None) -> bool`

**Descrição**: Combo de manobras para navegar até configurações.

**Parâmetros**:
- `settings_possibilities`: Lista de possíveis seletores para configurações. Se None, usa lista padrão com múltiplos idiomas.

**Retorna**: `True` se navegação foi bem-sucedida

**Exemplo**:
```python
# Navegar para configurações com lista padrão
selum.combo_navigate_to_settings()

# Navegar com seletores customizados
selum.combo_navigate_to_settings([
    {"text": "Settings"},
    {"text": "Configurações"},
    {"css": ".settings-icon"}
])
```

**Quando Usar**: Para navegar até página de configurações de forma resiliente.

**Status**: Implementação futura (Fase 6)

---

## Resumo de Uso

**Localizar Elementos**:
- Use `scout()` para múltiplas estratégias de busca
- Use `vigilance()` para aguardar elemento aparecer

**Interagir com Elementos**:
- Use `strike()` para clicar
- Use `steady_gaze()` para garantir visibilidade antes de interagir

**Resolver Obstáculos**:
- Use `cleansing_aura()` para remover overlays e pop-ups

**Aprendizado e Evolução**:
- `invoke_wisdom()` é chamado automaticamente em falhas
- `divine_inspiration()` é invocado automaticamente após 3 falhas estruturais
- `execute_skill()` executa skills customizadas criadas

**NUNCA FAÇA**:
- ❌ `driver.find_element(By.CSS_SELECTOR, ".button")`
- ❌ `driver.execute_script("document.querySelector('.button').click()")`
- ❌ `WebDriverWait(driver, 10).until(...)`
- ❌ `ActionChains(driver).move_to_element(...).click()`

**SEMPRE FAÇA**:
- ✅ `selum.strike(".button")`
- ✅ `selum.scout([{"css": ".button"}])`
- ✅ `selum.vigilance(".button", timeout=10)`
- ✅ `selum.steady_gaze(".button")`


---

## mirror_walk

**Assinatura**: `mirror_walk(target_selector: str, navigation_elements: List[str] = None, intermediate_path: List[str] = None) -> bool`

**Descrição**: Navegação ultra-realista com simulação comportamental completa. Combina ruído cinético (micro-movimentos), ghost breadcrumbs (páginas intermediárias) e cognitive latency (hesitação humana) para evitar detecção por behavioral biometrics.

**Fases**:
1. **Observação**: Gera eventos fantasma de mouse por 500ms
2. **Ativação**: Dispara eventos de focus em elementos de navegação
3. **Salto**: Executa transição de estado real

**Parâmetros**:
- `target_selector`: Seletor CSS do elemento alvo
- `navigation_elements`: Lista de seletores de navegação (opcional)
- `intermediate_path`: Caminho intermediário para ghost breadcrumbs (opcional)

**Retorna**: `True` se bem-sucedido, `False` caso contrário

**Exemplo**:
```python
# Navegação ultra-realista com todas as fases
selum.mirror_walk(
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
```

**Quando Usar**:
- Sites com behavioral biometrics (Google, Facebook, bancos)
- Sistemas anti-bot avançados
- Navegação crítica (login, checkout, transações)

**Técnicas Incluídas**:
- ✅ Curva de Bezier para movimento de mouse
- ✅ Flutuação de click (±5px)
- ✅ Eventos de intenção (mouseenter em elementos próximos)
- ✅ Ghost breadcrumbs (navegação intermediária)
- ✅ Cognitive latency (hesitação baseada em complexidade)
- ✅ Micro-pausas (simular leitura)

**Performance**: ~2-5 segundos (mais lento que navegação direta, mas mais realista)

**Validação**: Requer `target_selector` válido. `navigation_elements` e `intermediate_path` são opcionais mas recomendados para máxima humanização.
