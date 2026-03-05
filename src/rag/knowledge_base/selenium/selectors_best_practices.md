# Context: Seletores e Localização de Elementos
# Technical_Tag: #CSSSelector #XPath #LocatorStrategy #BestPractices

## Description

Boas práticas para escolher e usar seletores no Selenium. Priorize seletores estáveis, evite dependências frágeis (índices, textos longos) e prefira abstrações do Selum quando disponíveis.

## Implementation_Snippet

```python
# Prioridade 1: ID (único e estável)
element = driver.find_element(By.ID, "submit-btn")

# Prioridade 2: data-* attributes (semânticos, raramente mudam)
element = driver.find_element(By.CSS_SELECTOR, "[data-testid='settings-button']")

# Prioridade 3: CSS com classes estáveis (evite classes de estilo como .mt-4)
element = driver.find_element(By.CSS_SELECTOR, ".settings-panel .primary-action")

# Prioridade 4: XPath por atributos (mais robusto que texto)
element = driver.find_element(By.XPATH, "//button[@aria-label='Settings']")

# Múltiplos caminhos com scout() - ideal para i18n e variações de layout
possibilities = [
    {"text": "Settings", "type": "link"},
    {"text": "Definições", "type": "link"},
    {"css": "[data-testid='settings']"},
    {"xpath": "//button[contains(@class, 'settings')]"}
]
element = selum.scout(possibilities)
```

## Failure_Signs

- `NoSuchElementException` ocorre quando o seletor não encontra nenhum elemento.
- O DOM se comporta de forma dinâmica: elementos carregam via AJAX, React ou Vue.
- Classes como `.btn-primary` mudam entre deploys; prefira `data-testid` ou `aria-label`.
- XPath por texto (`//*[text()='Exato']`) quebra com traduções ou espaços extras.

## Abstraction_Mapping

- Use a Skill: `selum.scout()` para múltiplos seletores (i18n, fallbacks).
- Use a Skill: `selum.vigilance()` antes de `find_element` em conteúdo dinâmico.
- Use a Skill: `selum.steady_gaze()` antes de clicar em elementos fora do viewport.
- Evite `find_element` direto em elementos que podem estar em iframe ou Shadow DOM.
