# Sentinela Visual Templates

Este diretório contém templates visuais para detecção de elementos no Dashboard.

## Tipos de Templates

### 1. Anchor Templates (Ancoragem)
Templates de elementos fixos usados para confirmar que o Dashboard está visível:

- `dashboard_logo.png` - Logo do projeto (canto superior esquerdo)
- `refresh_button.png` - Botão de refresh/atualizar
- `status_icon.png` - Ícone de status do sistema

**Uso:** Estes 3 elementos devem ser detectados antes de qualquer ação no Dashboard.

### 2. Alert Templates
Templates de alertas visuais:

- `alert_quality_low.png` - Alerta de quality_score baixo (< 5)
- `alert_confirmation.png` - Confirmação de alerta emitido

**Uso:** Confirmação visual de que a missão foi concluída.

### 3. Page Load Indicators
Templates para detectar carregamento completo:

- `loading_spinner.png` - Spinner de carregamento (ausência indica página carregada)
- `dashboard_header.png` - Header do Dashboard
- `main_content.png` - Área de conteúdo principal
- `footer.png` - Footer do Dashboard

### 4. Noise Templates (Filtro de Ruído)
Templates de elementos que devem ser ignorados:

- `windows_notification.png` - Notificação do Windows
- `system_popup.png` - Popup do sistema
- `browser_popup.png` - Popup do navegador
- `update_notification.png` - Notificação de atualização

**Uso:** Teste de "Ambiente Ruidoso" - Sentinela ignora estes elementos.

## Como Criar Templates

1. **Capturar Screenshot:**
   ```python
   from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer
   analyzer = ScreenshotAnalyzer()
   screenshot = analyzer.capture_screenshot()
   ```

2. **Recortar Elemento:**
   - Use uma ferramenta de edição de imagem
   - Recorte apenas o elemento desejado
   - Mantenha tamanho razoável (50x50 a 200x200 pixels)

3. **Salvar como PNG:**
   - Formato: PNG (melhor qualidade)
   - Nome: descritivo e sem espaços (use underscore)
   - Localização: `templates/nome_do_elemento.png`

4. **Testar Template:**
   ```python
   from src.sentinela.visual_detector import VisualDetector
   detector = VisualDetector(templates_dir="./templates")
   result = detector.find_element("nome_do_elemento")
   print(f"Found: {result.found}, Confidence: {result.confidence}")
   ```

## Dicas para Bons Templates

- **Contraste:** Escolha elementos com bom contraste visual
- **Únicos:** Evite elementos que aparecem múltiplas vezes na tela
- **Estáveis:** Escolha elementos que não mudam de aparência
- **Tamanho:** Nem muito pequeno (difícil detectar) nem muito grande (lento)
- **Variantes:** Crie variantes para temas light/dark se necessário

## Estrutura de Nomes

```
<categoria>_<elemento>_<variante>.png

Exemplos:
- anchor_logo.png
- anchor_refresh_button.png
- alert_quality_low.png
- noise_windows_notification.png
- load_spinner.png
```

## Configuração de Anchors

```python
from src.sentinela.visual_detector import VisualDetector, AnchorPoint

detector = VisualDetector(templates_dir="./templates")

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

# Verificar Dashboard visível
is_visible, results = detector.verify_dashboard_visible()
if is_visible:
    print("✓ Dashboard confirmado!")
```

## Troubleshooting

**Template não detectado:**
- Verifique se o arquivo existe em `templates/`
- Confirme que o nome está correto (sem extensão ao chamar)
- Teste com confidence_threshold mais baixo
- Capture novo template com melhor qualidade

**Falsos positivos:**
- Aumente confidence_threshold
- Use template mais específico
- Adicione mais contexto ao template

**Performance lenta:**
- Reduza tamanho dos templates
- Use menos scales no multiscale matching
- Cache screenshots quando possível
