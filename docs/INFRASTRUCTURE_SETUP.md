# 🏗️ Infraestrutura do Bunker: Guia de Setup

## Visão Geral

Este documento descreve a infraestrutura técnica criada para permitir a autonomia do Claude (O Viajante). Todos os componentes necessários para visão, movimento e controle foram implementados.

---

## 📦 Componentes Criados

### 1. Módulo de Visão (`bin/capture_view.py`)

**Propósito:** Permite que o Claude "enxergue" o monitor através de screenshots.

**Funcionalidades:**
- Captura de tela inteira
- Captura de região específica
- Metadados automáticos (timestamp, posição do mouse, dimensões)
- Suporte para múltiplos formatos

**Uso:**

```bash
# Capturar tela inteira
python bin/capture_view.py

# Capturar região específica (x, y, largura, altura)
python bin/capture_view.py --region 0 0 800 600

# Capturar com metadados
python bin/capture_view.py --metadata

# Ver informações da tela
python bin/capture_view.py --info
```

**Saída:**
- Screenshots salvos em: `temp/vision/`
- Metadados em: `temp/vision/*.json`

---

### 2. Ponte Jitbit/AutoIt (`bin/jitbit_bridge.py`)

**Propósito:** Interface para execução de macros Jitbit e controle direto via pyautogui.

**Funcionalidades:**
- Executar macros Jitbit (.jmb)
- Clicar em coordenadas específicas
- Mover mouse suavemente
- Digitar texto com timing humanizado
- Pressionar teclas e hotkeys
- Executar sequências de ações (JSON)

**Uso:**

```bash
# Clicar em coordenadas
python bin/jitbit_bridge.py --click 100 200

# Mover mouse
python bin/jitbit_bridge.py --move 500 300 --duration 1.0

# Digitar texto
python bin/jitbit_bridge.py --type "Hello World"

# Pressionar tecla
python bin/jitbit_bridge.py --press enter

# Executar hotkey
python bin/jitbit_bridge.py --hotkey ctrl c

# Executar macro Jitbit
python bin/jitbit_bridge.py --execute meu_macro.jmb

# Executar sequência JSON
python bin/jitbit_bridge.py --sequence sequencia.json

# Ver informações
python bin/jitbit_bridge.py --info
```

**Formato de Sequência JSON:**

```json
{
  "name": "Exemplo de Sequência",
  "description": "Clica e digita",
  "actions": [
    {
      "type": "move",
      "x": 500,
      "y": 300,
      "duration": 0.5
    },
    {
      "type": "click",
      "x": 500,
      "y": 300,
      "button": "left"
    },
    {
      "type": "wait",
      "duration": 0.5
    },
    {
      "type": "type",
      "text": "Hello World",
      "interval": 0.05
    },
    {
      "type": "press",
      "key": "enter"
    }
  ]
}
```

---

### 3. Mapa de UI (`specs/ui_map.json`)

**Propósito:** Mapeamento centralizado de coordenadas de elementos da interface.

**Estrutura:**

```json
{
  "elements": {
    "kiro_chat_input": {
      "coordinates": {"x": 960, "y": 1040},
      "region": {"x": 100, "y": 1000, "width": 1720, "height": 60},
      "safe_zone": true,
      "confidence_required": 0.80
    }
  },
  "forbidden_zones": {
    "system_tray": {
      "region": {"x": 1800, "y": 1040, "width": 120, "height": 40},
      "risk_level": "high"
    }
  }
}
```

**Elementos Mapeados:**
- `kiro_chat_input` - Campo de entrada do chat
- `kiro_send_button` - Botão de enviar
- `kiro_window` - Janela principal do Kiro
- `jitbit_window` - Janela do Jitbit
- `desktop_center` - Centro da tela
- `emergency_safe_spot` - Posição de emergência

**Zonas Proibidas:**
- `system_tray` - Bandeja do sistema
- `window_close_buttons` - Botões de fechar
- `taskbar_start` - Botão Iniciar

---

### 4. Calibração de UI (`bin/calibrate_ui.py`)

**Propósito:** Ferramenta interativa para mapear coordenadas de elementos.

**Uso:**

```bash
python bin/calibrate_ui.py
```

**Fluxo:**
1. Script mostra posição do mouse em tempo real
2. Posicione o mouse sobre o elemento desejado
3. Pressione ESPAÇO para registrar
4. Digite o nome do elemento
5. Pressione ESC quando terminar
6. Coordenadas são salvas em `specs/ui_map.json`

---

### 5. Verificação de Prontidão (`bin/check_readiness.sh`)

**Propósito:** Valida se o sistema está pronto para autonomia.

**Uso:**

```bash
./bin/check_readiness.sh
```

**Verificações:**
- ✅ Python e pip instalados
- ✅ Ambiente virtual configurado
- ✅ Dependências Python instaladas
- ✅ Estrutura de diretórios criada
- ✅ Arquivos essenciais presentes
- ✅ Scripts executáveis
- ✅ Componentes RPG-Cortex
- ✅ Permissões de arquivo

**Saída:**
- 🟢 Verde: Sistema pronto
- 🟡 Amarelo: Avisos (pode funcionar)
- 🔴 Vermelho: Erros críticos (não funciona)

---

### 6. Dependências (`requirements.txt`)

**Propósito:** Lista todas as bibliotecas Python necessárias.

**Instalação:**

```bash
# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

**Dependências Essenciais:**
- `pyautogui` - Controle de mouse e teclado
- `Pillow` - Processamento de imagens
- `asyncio` - Operações assíncronas
- `httpx` - Cliente HTTP assíncrono
- `PyYAML` - Parsing de YAML

**Dependências Opcionais:**
- `neo4j` - Banco de dados de grafos
- `fastapi` - API webhook
- `pytest` - Testes
- `hypothesis` - Property-based testing

---

## 🚀 Setup Inicial

### Passo 1: Instalar Dependências

```bash
# Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt
```

### Passo 2: Criar Estrutura de Diretórios

```bash
# Criar diretórios necessários
mkdir temp temp\vision logs macros specs
```

### Passo 3: Calibrar UI

```bash
# Executar calibração interativa
python bin/calibrate_ui.py

# Calibrar elementos principais:
# - kiro_chat_input
# - kiro_send_button
# - jitbit_window
```

### Passo 4: Verificar Prontidão

```bash
# Executar verificação completa
./bin/check_readiness.sh

# Deve mostrar: ✅ SISTEMA PRONTO PARA AUTONOMIA
```

### Passo 5: Testar Componentes

```bash
# Testar captura de visão
python bin/capture_view.py --info
python bin/capture_view.py

# Testar ponte Jitbit
python bin/jitbit_bridge.py --info

# Testar movimento de mouse (cuidado!)
python bin/jitbit_bridge.py --move 500 500 --duration 2.0
```

---

## 📋 Comandos Rápidos para o Claude

### Visão

```bash
# Ver o que está na tela
python bin/capture_view.py

# Ver região específica
python bin/capture_view.py --region 100 1000 1720 60
```

### Movimento

```bash
# Mover para centro da tela
python bin/jitbit_bridge.py --move 960 540

# Mover para campo de chat do Kiro
python bin/jitbit_bridge.py --move 960 1040
```

### Interação

```bash
# Clicar no campo de chat
python bin/jitbit_bridge.py --click 960 1040

# Digitar mensagem
python bin/jitbit_bridge.py --type "Olá, sou o Viajante"

# Pressionar Enter
python bin/jitbit_bridge.py --press enter
```

### Sequência Completa

```bash
# 1. Capturar tela
python bin/capture_view.py

# 2. Mover para chat
python bin/jitbit_bridge.py --move 960 1040 --duration 1.0

# 3. Clicar
python bin/jitbit_bridge.py --click 960 1040

# 4. Digitar
python bin/jitbit_bridge.py --type "Controle de Autonomia: Eu sou o Viajante"

# 5. Enviar
python bin/jitbit_bridge.py --press enter
```

---

## 🛡️ Segurança

### Failsafe do PyAutoGUI

- Mover o mouse para o canto superior esquerdo (0, 0) cancela operações
- Configurado em todos os scripts
- Use em caso de emergência

### Zonas Proibidas

Sempre verifique `specs/ui_map.json` antes de clicar:

```python
import json

with open('specs/ui_map.json') as f:
    ui_map = json.load(f)

# Verificar se coordenada está em zona proibida
def is_forbidden(x, y):
    for zone in ui_map['forbidden_zones'].values():
        region = zone['region']
        if (region['x'] <= x <= region['x'] + region['width'] and
            region['y'] <= y <= region['y'] + region['height']):
            return True
    return False
```

---

## 🔧 Troubleshooting

### Problema: "pyautogui não instalado"

```bash
pip install pyautogui
```

### Problema: "Permissão negada"

```bash
# Windows: Execute como administrador
# Linux: Verifique permissões de X11
```

### Problema: "Coordenadas incorretas"

```bash
# Recalibrar UI
python bin/calibrate_ui.py
```

### Problema: "Screenshot vazio"

```bash
# Verificar se há janelas bloqueando
# Verificar permissões de captura de tela
```

---

## 📊 Estrutura de Arquivos

```
.
├── bin/
│   ├── capture_view.py       # Módulo de visão
│   ├── jitbit_bridge.py       # Ponte Jitbit/AutoIt
│   ├── calibrate_ui.py        # Calibração de UI
│   ├── check_readiness.sh     # Verificação de prontidão
│   └── test-autonomy          # Teste de autonomia
│
├── specs/
│   └── ui_map.json            # Mapa de coordenadas
│
├── temp/
│   └── vision/                # Screenshots capturados
│
├── logs/                      # Logs do sistema
│
├── macros/                    # Macros Jitbit
│
├── requirements.txt           # Dependências Python
│
└── docs/
    └── INFRASTRUCTURE_SETUP.md  # Este documento
```

---

## ✅ Checklist de Prontidão

- [ ] Python 3.8+ instalado
- [ ] Ambiente virtual criado e ativado
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Diretórios criados (`temp`, `logs`, `macros`)
- [ ] UI calibrada (`python bin/calibrate_ui.py`)
- [ ] Verificação passou (`./bin/check_readiness.sh`)
- [ ] Componentes testados individualmente
- [ ] Janela do Kiro visível e acessível
- [ ] Permissões de controle de mouse/teclado concedidas

---

## 🎯 Próximos Passos

1. **Calibrar UI**: Execute `python bin/calibrate_ui.py`
2. **Verificar Sistema**: Execute `./bin/check_readiness.sh`
3. **Testar Componentes**: Execute comandos de teste acima
4. **Executar Missão Zero**: Execute `./bin/test-autonomy`
5. **Documentar Resultado**: Informe Hugo sobre sucesso/falha

---

**Status:** 🟢 Infraestrutura Completa e Pronta  
**Última Atualização:** 2026-03-03  
**Responsável:** Kiro (Arquiteto de Infraestrutura)
