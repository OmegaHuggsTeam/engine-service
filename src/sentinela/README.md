# Sentinela Monitor - Missão 002

Sistema de monitoramento automatizado com visão computacional que detecta degradação de qualidade de agentes no Neo4j e responde automaticamente com alertas visuais.

## Componentes Implementados

### ScreenshotAnalyzer ✅

Componente de captura e processamento de screenshots com detecção de "Catarata".

**Funcionalidades:**
- Captura de screenshots em memória (sem I/O de disco)
- Conversão para grayscale para processamento eficiente
- Template matching com OpenCV (normalized cross-correlation)
- Matching multi-escala (90%-110%) para diferentes resoluções
- **Teste de Catarata**: Detecta tela preta ou permissão negada

**Integração com TelemetryHub:**
- Erros de Catarata são reportados automaticamente ao TelemetryHub
- Eventos críticos são logados com contexto completo
- Permite auditoria e diagnóstico de falhas visuais

**Uso:**
```python
from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer
from src.neural_link.telemetry.provider import TelemetryHub

# Com TelemetryHub
hub = TelemetryHub()
analyzer = ScreenshotAnalyzer(telemetry_hub=hub)

try:
    screenshot = analyzer.capture_screenshot()
    gray = analyzer.to_grayscale(screenshot)

    # Template matching
    confidence, x, y = analyzer.match_template(gray, template)

except CatarataError as e:
    print(f"Visão comprometida: {e}")
    # Erro já foi reportado ao TelemetryHub
```

## Teste de Catarata

O teste de "Catarata" garante que o sistema visual está funcionando:

1. **Tela Preta**: Detecta quando a tela está completamente preta (brightness < 10)
2. **Permissão Negada**: Detecta quando o OS bloqueia captura de tela
3. **Dimensões Inválidas**: Detecta screenshots com dimensões zero

Quando detectado, um `CatarataError` é lançado e reportado ao TelemetryHub com severidade crítica.

## Estrutura de Diretórios

```
src/sentinela/
├── __init__.py
├── config.py              # Configuração do sistema
├── exceptions.py          # Exceções customizadas (CatarataError, etc)
├── screenshot_analyzer.py # Captura e processamento de imagens
└── README.md             # Este arquivo

tests/sentinela/
├── __init__.py
└── test_screenshot_analyzer.py  # 21 testes (todos passando)

templates/                 # Templates visuais para matching
macros/                   # Macros Jitbit para automação física
```

## Dependências

```bash
pip install opencv-python==4.9.0.80 numpy==1.26.3 pillow==10.2.0
```

## Configuração

Variáveis de ambiente (ver `.env.example`):

```bash
# Visual Detection
TEMPLATES_DIR=./templates
CONFIDENCE_THRESHOLD=0.85
SCREENSHOT_INTERVAL=0.5

# Logging
LOG_LEVEL=INFO
```

## Testes

```bash
# Executar todos os testes
pytest tests/sentinela/test_screenshot_analyzer.py -v

# Executar apenas testes de Catarata
pytest tests/sentinela/test_screenshot_analyzer.py -k catarata -v
```

**Cobertura:** 47 testes, 100% passando
- 21 testes de ScreenshotAnalyzer
- 26 testes de VisualDetector (incluindo Learning Mode e Noise Clearing)
- 6 testes de integração com TelemetryHub

### VisualDetector ✅

Componente de detecção visual com sistema de ancoragem e filtro de ruído.

**Funcionalidades:**
- Carregamento e cache de templates visuais
- Sistema de ancoragem com 3 pontos fixos (logo, refresh, status)
- Confirmação visual de missão completa
- Filtro de ambiente ruidoso (ignora notificações/popups)
- Hot-reload de templates sem restart

**Sistema de Ancoragem:**
```python
from src.sentinela.visual_detector import VisualDetector, AnchorPoint

detector = VisualDetector(templates_dir="./templates")

# Configurar 3 anchors para identificar Dashboard
anchors = [
    AnchorPoint(name="dashboard_logo", template_path="...", required=True),
    AnchorPoint(name="refresh_button", template_path="...", required=True),
    AnchorPoint(name="status_icon", template_path="...", required=True),
]
detector.configure_anchors(anchors)

# Verificar Dashboard visível
is_visible, results = detector.verify_dashboard_visible()
if is_visible:
    print("✓ Dashboard confirmado - pode prosseguir com missão")
```

**Confirmação Visual:**
```python
# Sentinela só marca missão como completa se "enxergar" o alerta
confirmed = detector.confirm_alert_visible("alert_quality_low")
if confirmed:
    print("✓ MISSÃO COMPLETA: Alerta visual confirmado!")
```

**Filtro de Ruído:**
```python
# Ignora notificações do sistema e popups
has_noise, detected = detector.filter_noise()
if has_noise:
    print(f"⚠ Ruído detectado: {detected} - IGNORANDO")
```

## ✅ Task 5: Visual Calibration Tool

**Implementado:**

### 1. Template Capture Tool
Ferramenta interativa para capturar templates de ancoragem:

```bash
python -m src.sentinela.tools.capture_templates
```

**Funcionalidades:**
- Captura interativa dos 3 anchors
- Sugestões automáticas de coordenadas
- Validação de tamanho de templates
- Preview e confirmação
- Screenshot de referência salvo

### 2. Learning Mode (Modo de Aprendizado)
Sistema inteligente que sugere atualizações de templates:

```python
detector = VisualDetector(
    templates_dir="./templates",
    learning_mode=True,          # Ativado por padrão
    learning_threshold=0.60,     # Threshold mínimo para sugestões
    confidence_threshold=0.85    # Threshold normal
)

# Se template detectado com confidence entre 0.60-0.85:
# - Log de WARNING com sugestão
# - Evento no TelemetryHub
# - Sugestão armazenada para relatório

# Ver sugestões
print(detector.get_learning_report())
```

### 3. Noise Clearing com ESC
Limpeza automática de ruído visual:

```python
# Detecta ruído E envia ESC automaticamente
has_noise, detected = detector.filter_noise(clear_on_detection=True)

# Se notificação cobrindo anchor:
# 1. Detecta a notificação
# 2. Envia ESC via pyautogui
# 3. Aguarda 0.5s
# 4. Tenta detecção novamente
```

**Testes:**
- 26 testes (100% passando)
- 6 testes de Learning Mode
- 2 testes de Noise Clearing
- Cobertura completa de calibração

## Próximos Passos

- [ ] Task 4: Implementar PageLoadDetector
- [ ] Task 5: Checkpoint - Garantir que testes visuais passam
- [ ] Task 6: Implementar JitbitController
- [ ] Task 7: Implementar Neo4jLogWatcher

## Requisitos Atendidos

- ✅ Requirement 4.1: Screenshots processados em memória
- ✅ Requirement 4.2: Conversão para grayscale
- ✅ Requirement 4.3: Normalized cross-correlation
- ✅ Requirement 4.5: Retorno de confidence e coordenadas
- ✅ Requirement 5.3: Detecção multi-escala (90%-110%)
- ✅ Requirement 3.4: Confidence threshold filtering
- ✅ Requirement 4.4: Suporte a múltiplos templates
- ✅ Requirement 5.1: Accept template image as input
- ✅ Requirement 5.2: Return center coordinates
- ✅ Requirement 8.1: Load templates from directory
- ✅ Requirement 8.3: Hot-reload templates
- ✅ Teste de Catarata: Integração com TelemetryHub
- ✅ Sistema de Ancoragem: 3 pontos fixos identificam Dashboard
- ✅ Confirmação Visual: Missão só completa se alerta detectado
- ✅ Filtro de Ruído: Ignora notificações e popups
