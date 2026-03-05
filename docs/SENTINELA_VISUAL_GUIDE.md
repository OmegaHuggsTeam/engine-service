# Guia Prático: Sistema Visual do Sentinela

## Visão Geral

O Sentinela Monitor usa visão computacional para detectar elementos visuais no Dashboard e confirmar que ações foram executadas com sucesso. Este guia explica como usar o sistema visual.

## Conceitos Principais

### 1. Templates Visuais

Templates são imagens de referência que o Sentinela usa para identificar elementos na tela.

**Tipos de templates:**
- **Anchors**: Elementos fixos que identificam o Dashboard (logo, botões, ícones)
- **Alerts**: Elementos que indicam alertas visuais
- **Noise**: Elementos que devem ser ignorados (notificações, popups)

### 2. Sistema de Ancoragem

O Sentinela usa 3 pontos de ancoragem para confirmar que está olhando para o Dashboard correto:

1. **Logo do projeto** (canto superior esquerdo)
2. **Botão de Refresh** (barra de ferramentas)
3. **Ícone de Status** (área de status)

**Por que 3 anchors?**
- Evita falsos positivos (outras janelas/aplicações)
- Garante que o Dashboard está completamente visível
- Permite detecção robusta mesmo com elementos parcialmente ocultos

### 3. Confirmação Visual

O Sentinela só marca uma missão como completa se "enxergar" o resultado esperado na tela.

**Exemplo:** Emitir alerta de quality_score baixo
- ❌ Não basta executar o clique no botão
- ✅ Precisa confirmar que o alerta apareceu na tela

### 4. Filtro de Ruído

O Sentinela ignora elementos que não fazem parte do Dashboard:
- Notificações do Windows
- Popups do navegador
- Alertas do sistema
- Janelas de atualização

## Uso Básico

### Passo 1: Criar Templates

```python
from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer
import cv2

# Capturar tela
analyzer = ScreenshotAnalyzer()
screenshot = analyzer.capture_screenshot()

# Salvar screenshot completo
cv2.imwrite("screenshot_full.png", screenshot)

# Agora use uma ferramenta de edição para recortar os elementos:
# 1. Abra screenshot_full.png
# 2. Recorte o logo do Dashboard
# 3. Salve como templates/dashboard_logo.png
# 4. Repita para refresh_button e status_icon
```

### Passo 2: Configurar Detector

```python
from src.sentinela.visual_detector import VisualDetector, AnchorPoint

# Criar detector
detector = VisualDetector(
    templates_dir="./templates",
    confidence_threshold=0.85
)

# Configurar anchors
anchors = [
    AnchorPoint(
        name="dashboard_logo",
        template_path="templates/dashboard_logo.png",
        required=True,
        min_confidence=0.85
    ),
    AnchorPoint(
        name="refresh_button",
        template_path="templates/refresh_button.png",
        required=True,
        min_confidence=0.80
    ),
    AnchorPoint(
        name="status_icon",
        template_path="templates/status_icon.png",
        required=True,
        min_confidence=0.80
    ),
]

detector.configure_anchors(anchors)
```

### Passo 3: Verificar Dashboard

```python
# Verificar se Dashboard está visível
is_visible, anchor_results = detector.verify_dashboard_visible()

if is_visible:
    print("✓ Dashboard confirmado - pode prosseguir")
    
    # Mostrar detalhes dos anchors
    for name, result in anchor_results.items():
        if result.found:
            print(f"  {name}: detectado em ({result.center_x}, {result.center_y})")
else:
    print("✗ Dashboard não visível")
    print("  Possíveis causas:")
    print("  - Dashboard não está aberto")
    print("  - Dashboard está parcialmente oculto")
    print("  - Outra janela está em primeiro plano")
```

### Passo 4: Confirmar Alerta

```python
# Após executar ação (ex: clicar em botão de alerta)
# Confirmar que alerta apareceu na tela

confirmed = detector.confirm_alert_visible("alert_quality_low")

if confirmed:
    print("✓ MISSÃO COMPLETA: Alerta confirmado!")
    # Pode marcar missão como concluída
else:
    print("✗ Alerta não detectado")
    # Não marcar como concluída, tentar novamente
```

### Passo 5: Filtrar Ruído

```python
# Verificar se há ruído visual (notificações, popups)
has_noise, detected_noise = detector.filter_noise()

if has_noise:
    print(f"⚠ Ruído detectado: {detected_noise}")
    print("  Sentinela vai ignorar e focar no Dashboard")
else:
    print("✓ Ambiente limpo")
```

## Workflow Completo

```python
from src.sentinela.visual_detector import VisualDetector, AnchorPoint
from src.neural_link.telemetry.provider import TelemetryHub

# 1. Setup
hub = TelemetryHub()
detector = VisualDetector(
    templates_dir="./templates",
    telemetry_hub=hub
)

# 2. Configurar anchors
anchors = [
    AnchorPoint(name="dashboard_logo", template_path="...", required=True),
    AnchorPoint(name="refresh_button", template_path="...", required=True),
    AnchorPoint(name="status_icon", template_path="...", required=True),
]
detector.configure_anchors(anchors)

# 3. Verificar Dashboard visível
is_visible, _ = detector.verify_dashboard_visible()
if not is_visible:
    print("✗ Dashboard não visível - abortando missão")
    exit(1)

# 4. Filtrar ruído
has_noise, _ = detector.filter_noise()
if has_noise:
    print("⚠ Ruído detectado - continuando com foco no Dashboard")

# 5. Executar ação (ex: clicar em botão)
# ... código de automação Jitbit ...

# 6. Confirmar resultado visual
confirmed = detector.confirm_alert_visible("alert_quality_low")
if confirmed:
    print("✓ MISSÃO COMPLETA")
    # Reportar sucesso ao TelemetryHub
else:
    print("✗ Missão falhou - alerta não detectado")
    # Reportar falha ao TelemetryHub

# 7. Verificar eventos no TelemetryHub
events = hub.get_event_log()
print(f"Total de eventos: {len(events)}")
```

## Troubleshooting

### Template não detectado

**Sintoma:** `result.found = False` mesmo com elemento visível

**Soluções:**
1. Verificar qualidade do template:
   ```python
   # Template deve ter bom contraste e ser único
   # Evite templates muito pequenos (< 30x30) ou muito grandes (> 300x300)
   ```

2. Ajustar confidence threshold:
   ```python
   detector = VisualDetector(
       templates_dir="./templates",
       confidence_threshold=0.75  # Reduzir de 0.85 para 0.75
   )
   ```

3. Verificar se template está no diretório:
   ```python
   print(detector.loaded_templates)
   # Deve incluir o nome do template
   ```

4. Testar detecção manualmente:
   ```python
   result = detector.find_element("dashboard_logo")
   print(f"Found: {result.found}")
   print(f"Confidence: {result.confidence}")
   print(f"Position: ({result.center_x}, {result.center_y})")
   ```

### Falsos positivos

**Sintoma:** Template detectado em local errado

**Soluções:**
1. Aumentar confidence threshold:
   ```python
   detector.confidence_threshold = 0.90
   ```

2. Usar template mais específico (com mais contexto)

3. Usar anchors para validar contexto:
   ```python
   # Só aceitar detecção se anchors também estiverem presentes
   is_visible, _ = detector.verify_dashboard_visible()
   if is_visible:
       result = detector.find_element("alert_quality_low")
   ```

### Performance lenta

**Sintoma:** Detecção demora muito tempo

**Soluções:**
1. Reduzir tamanho dos templates (max 200x200)

2. Usar menos scales no multiscale:
   ```python
   # Modificar em screenshot_analyzer.py
   scales = [1.0]  # Apenas escala 1:1
   ```

3. Capturar screenshot uma vez e reusar:
   ```python
   screenshot = analyzer.capture_screenshot()
   result1 = detector.find_element("logo", screenshot=screenshot)
   result2 = detector.find_element("button", screenshot=screenshot)
   ```

### Catarata Error

**Sintoma:** `CatarataError: Screen is black`

**Causas:**
- Tela realmente está preta (screensaver, tela desligada)
- Permissão de captura de tela negada
- Display não acessível

**Soluções:**
1. Verificar se tela está ligada e desbloqueada
2. Verificar permissões do sistema operacional
3. Testar captura manual:
   ```python
   from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer
   analyzer = ScreenshotAnalyzer()
   try:
       screenshot = analyzer.capture_screenshot()
       print("✓ Captura funcionando")
   except CatarataError as e:
       print(f"✗ Catarata: {e}")
   ```

## Boas Práticas

1. **Sempre use anchors** antes de ações críticas
2. **Sempre confirme visualmente** após ações importantes
3. **Filtre ruído** em ambientes com muitas notificações
4. **Use TelemetryHub** para auditoria e debugging
5. **Teste templates** em diferentes resoluções e temas
6. **Mantenha templates atualizados** quando UI mudar
7. **Use nomes descritivos** para templates
8. **Documente** quais elementos cada template representa

## Exemplos Práticos

Ver `examples/sentinela_visual_demo.py` para exemplos completos de uso.
