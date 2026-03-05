# Context: Manobras Proibidas (Anti-Detecção)
# Technical_Tag: #Stealth #AntiBot #Prohibited #GoogleDetection

## Description

Lista de ações que o Paladino **NÃO** deve executar, pois aumentam o risco de detecção por sistemas anti-bot (Google, Cloudflare, reCAPTCHA). O RAG deve injetar este conhecimento quando a IA sugerir tais manobras.

## Implementation_Snippet

```python
# NÃO FAZER: time.sleep() fixo e longo (padrão de bot)
# time.sleep(5)  # PROIBIDO

# NÃO FAZER: velocidade humana impossível (cliques em <100ms)
# for btn in buttons: btn.click()  # PROIBIDO - sem delay

# NÃO FAZER: desabilitar WebDriver flag (detectável)
# driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {...})  # CUIDADO

# NÃO FAZER: navegação direta para URLs sensíveis sem contexto
# driver.get("https://accounts.google.com")  # Sem fluxo natural = suspeito

# FAZER: usar undetected-chromedriver para bypass básico
# FAZER: delays aleatórios entre ações (random.uniform(0.5, 1.5))
# FAZER: scroll natural antes de interagir (steady_gaze)
```

## Failure_Signs

- Erro "Chrome is being controlled by automated software" indica detecção.
- reCAPTCHA aparece com frequência anormal.
- Conta Google bloqueada ou exigindo verificação de telefone.
- Cloudflare challenge em sites que usuários normais acessam sem problema.

## Abstraction_Mapping

- Use a Skill: `selum.steady_gaze()` antes de clicar (simula scroll humano).
- Use a Skill: `selum.cleansing_aura()` para overlays, não para esconder rastros.
- Nunca: `driver.execute_script("return navigator.webdriver")` para falsificar.
- Prefira: undetected-chromedriver + delays humanos + fluxos naturais.
