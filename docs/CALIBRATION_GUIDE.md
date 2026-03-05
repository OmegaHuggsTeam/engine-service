# Guia de Calibração Visual do Sentinela

## Visão Geral

Este guia explica como calibrar o sistema visual do Sentinela para seu Dashboard específico usando o Template Capture Tool e o Learning Mode.

## Quando Calibrar

Você deve calibrar o Sentinela quando:

1. **Primeira instalação** - Templates padrão são apenas placeholders
2. **UI do Dashboard mudou** - Redesign, novo tema, novos elementos
3. **Learning Mode sugere** - Templates detectados com baixa confidence
4. **Mudança de resolução** - Novo monitor, DPI diferente
5. **Falsos negativos** - Anchors não sendo detectados

## Passo 1: Preparar o Dashboard

Antes de capturar templates:

1. Abra o Dashboard no navegador
2. Maximize a janela
3. Certifique-se de que está completamente carregado
4. Feche todas as notificações e popups
5. Use o tema/modo que será usado em produção (light/dark)

## Passo 2: Executar Template Capture Tool

```bash
python -m src.sentinela.tools.capture_templates
```

### Fluxo Interativo

O tool vai guiá-lo através de 3 etapas:

#### Etapa 1: Confirmação de Foco

```
PASSO 1: Abra o Dashboard no navegador
Certifique-se de que:
  - Dashboard está completamente carregado
  - Nenhuma notificação está cobrindo a tela
  - Janela está em foco e maximizada

Pressione ENTER quando estiver pronto...
```

**Ação:** Verifique tudo e pressione ENTER

#### Etapa 2: Captura de Screenshot

O tool captura um screenshot completo e salva como `_reference_screenshot.png` em `./templates/`

#### Etapa 3: Seleção de Anchors

Para cada anchor (logo, refresh, status), o tool:

1. Mostra coordenadas sugeridas
2. Pede confirmação ou novas coordenadas
3. Extrai a região
4. Valida o tamanho
5. Salva o template

**Exemplo de interação:**

```
Capturando: dashboard_logo
Descrição: Logo do projeto (geralmente canto superior esquerdo)

Região sugerida: x=10, y=10, width=150, height=80
Pressione ENTER para aceitar ou digite novas coordenadas
Formato: x,y,width,height (ex: 10,10,100,50)
> [ENTER para aceitar ou digite: 20,15,120,70]
```

### Dicas para Seleção de Regiões

**Logo do Dashboard:**
- Geralmente canto superior esquerdo
- Tamanho típico: 100x50 a 150x80 pixels
- Deve ser único e sempre visível

**Botão de Refresh:**
- Geralmente barra de ferramentas superior
- Tamanho típico: 80x40 a 120x60 pixels
- Inclua o ícone e um pouco de contexto

**Ícone de Status:**
- Pode estar em qualquer canto
- Tamanho típico: 60x60 a 100x100 pixels
- Escolha elemento que muda pouco

### Validação de Tamanho

O tool valida automaticamente:

- ✗ Muito pequeno: < 20x20 pixels (não confiável)
- ⚠ Pequeno: 20x30 pixels (pode funcionar)
- ✓ Ideal: 50x50 a 200x200 pixels
- ⚠ Grande: > 200x200 pixels (lento)

## Passo 3: Testar Templates

Após capturar, teste imediatamente:

```bash
python examples/sentinela_visual_demo.py
```

Verifique a saída:

```
=== Demo 3: Verificação de Dashboard (Ancoragem) ===

Resultado da verificação:
  Dashboard visível: ✓ SIM

Status dos anchors:
  - dashboard_logo: ✓ DETECTADO (conf=0.950)
    Posição: (75, 40)
  - refresh_button: ✓ DETECTADO (conf=0.920)
    Posição: (1800, 35)
  - status_icon: ✓ DETECTADO (conf=0.880)
    Posição: (1850, 1020)
```

**Objetivo:** Todos os 3 anchors com confidence > 0.85

## Passo 4: Ajustar se Necessário

### Se confidence < 0.85

**Opção 1: Re-capturar template**
```bash
python -m src.sentinela.tools.capture_templates
```
- Use região maior (mais contexto)
- Certifique-se de que elemento está nítido
- Evite áreas com gradientes ou sombras

**Opção 2: Ajustar threshold**
```python
detector = VisualDetector(
    templates_dir="./templates",
    confidence_threshold=0.75  # Reduzir de 0.85
)
```

### Se falsos positivos

**Opção 1: Template mais específico**
- Capture região maior com mais contexto
- Inclua elementos únicos ao redor

**Opção 2: Aumentar threshold**
```python
detector = VisualDetector(
    templates_dir="./templates",
    confidence_threshold=0.90  # Aumentar de 0.85
)
```

## Learning Mode

### O que é?

Learning Mode detecta quando templates estão funcionando, mas com confidence abaixo do ideal (entre 0.60 e 0.85).

### Como usar?

```python
detector = VisualDetector(
    templates_dir="./templates",
    learning_mode=True,          # Ativado por padrão
    learning_threshold=0.60,     # Mínimo para sugestões
    confidence_threshold=0.85    # Threshold normal
)

# Usar normalmente
is_visible, results = detector.verify_dashboard_visible()

# Verificar sugestões
if detector.learning_suggestions:
    print(detector.get_learning_report())
```

### Exemplo de Saída

```
LEARNING MODE REPORT
======================================================================
Total suggestions: 2

1. Template: dashboard_logo
   Confidence: 0.720 (threshold: 0.850)
   Position: (75, 40)
   Recommendation: Re-capture this template
   Command: python -m src.sentinela.tools.capture_templates

2. Template: status_icon
   Confidence: 0.680 (threshold: 0.850)
   Position: (1850, 1020)
   Recommendation: Re-capture this template
   Command: python -m src.sentinela.tools.capture_templates
```

### Quando agir?

- **1-2 sugestões ocasionais:** Normal, pode ignorar
- **Mesma sugestão repetida:** Re-capture o template
- **Muitas sugestões:** Dashboard pode ter mudado, re-calibrar tudo

## Noise Clearing

### O que é?

Se uma notificação do Windows ou popup estiver cobrindo um anchor, o Sentinela pode enviar ESC para limpar a tela.

### Como usar?

```python
# Automático durante verificação
detector.filter_noise(clear_on_detection=True)

# Workflow completo
has_noise, detected = detector.filter_noise(clear_on_detection=True)
if has_noise:
    print(f"Ruído detectado e limpo: {detected}")
    # Tentar detecção novamente
    is_visible, results = detector.verify_dashboard_visible()
```

### Quando usar?

- Ambiente com muitas notificações
- Testes automatizados em máquina compartilhada
- Dashboard em segundo plano ocasionalmente

## Manutenção

### Verificação Regular

Execute mensalmente ou após mudanças:

```bash
# 1. Testar detecção atual
python examples/sentinela_visual_demo.py

# 2. Verificar Learning Mode
python examples/sentinela_calibration_demo.py

# 3. Re-calibrar se necessário
python -m src.sentinela.tools.capture_templates
```

### Monitoramento em Produção

```python
from src.neural_link.telemetry.provider import TelemetryHub

hub = TelemetryHub()
detector = VisualDetector(
    templates_dir="./templates",
    learning_mode=True,
    telemetry_hub=hub
)

# Usar normalmente...

# Verificar eventos de Learning
events = hub.get_event_log()
learning_events = [e for e in events if "LEARNING" in e.message]

if learning_events:
    print("⚠ Templates podem precisar de atualização:")
    for event in learning_events:
        print(f"  - {event.message}")
```

## Troubleshooting

### Templates não detectados (confidence < 0.60)

**Causas:**
- Template capturado de resolução diferente
- Tema do Dashboard mudou (light/dark)
- Elemento mudou de aparência
- Zoom do navegador diferente

**Soluções:**
1. Re-capturar templates na resolução/tema atual
2. Verificar se Dashboard está completamente carregado
3. Usar região maior com mais contexto

### Detecção lenta

**Causas:**
- Templates muito grandes (> 200x200)
- Muitos templates carregados
- Multi-scale com muitas escalas

**Soluções:**
1. Reduzir tamanho dos templates
2. Remover templates não usados
3. Desabilitar multi-scale se não necessário

### Falsos positivos

**Causas:**
- Template muito genérico
- Elemento aparece múltiplas vezes
- Threshold muito baixo

**Soluções:**
1. Capturar template mais específico
2. Aumentar confidence_threshold
3. Usar anchors para validar contexto

## Boas Práticas

1. **Sempre teste após capturar** - Execute demo imediatamente
2. **Mantenha backup** - Copie `templates/` antes de re-calibrar
3. **Use Learning Mode** - Detecta problemas antes de falhar
4. **Monitore TelemetryHub** - Eventos indicam quando re-calibrar
5. **Documente mudanças** - Anote quando e por que re-calibrou
6. **Versione templates** - Use git para rastrear mudanças
7. **Teste em produção** - Valide em ambiente real antes de deploy

## Comandos Rápidos

```bash
# Capturar templates
python -m src.sentinela.tools.capture_templates

# Testar detecção
python examples/sentinela_visual_demo.py

# Ver Learning Mode
python examples/sentinela_calibration_demo.py

# Verificar qualidade
python -c "from src.sentinela.visual_detector import VisualDetector; d = VisualDetector('./templates'); print(f'Templates: {d.template_count}')"
```
