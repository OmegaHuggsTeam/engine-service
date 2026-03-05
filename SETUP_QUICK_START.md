# 🚀 Setup Rápido - RPG-Cortex

Guia rápido para preparar o Bunker para autonomia do Claude.

## ✅ Status Atual

O sistema está **PRONTO** para testes de autonomia!

## 📋 Pré-requisitos

- ✅ Python 3.x instalado
- ✅ Ambiente virtual (.venv) configurado
- ✅ Dependências instaladas (pyautogui, Pillow)
- ✅ Estrutura de diretórios criada

## 🔧 Instalação (se necessário)

```bash
# 1. Criar ambiente virtual
python -m venv .venv

# 2. Ativar ambiente virtual
.venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Criar diretórios necessários
mkdir temp logs macros
```

## 🧪 Verificar Prontidão

Execute o script de verificação:

```bash
# Windows
bin\check_readiness.cmd

# Linux/Mac
bash bin/check_readiness.sh
```

## 🎯 Testar Componentes Individuais

### 1. Módulo de Visão (Screenshots)

```bash
# Capturar tela inteira
python bin/capture_view.py

# Capturar com metadados
python bin/capture_view.py --metadata

# Ver informações da tela
python bin/capture_view.py --info
```

### 2. Ponte Jitbit (Controle de Mouse/Teclado)

```bash
# Ver informações do sistema
python bin/jitbit_bridge.py --info

# Mover mouse para posição
python bin/jitbit_bridge.py --move 500 500

# Clicar em coordenadas
python bin/jitbit_bridge.py --click 100 200

# Digitar texto
python bin/jitbit_bridge.py --type "Hello World"
```

### 3. Calibração de UI

```bash
# Calibrar coordenadas dos elementos
python bin/calibrate_ui.py

# Instruções:
# 1. Mova o mouse sobre o elemento desejado
# 2. Pressione ESPAÇO para registrar
# 3. Digite o nome do elemento
# 4. Pressione ESC quando terminar
```

## 🛡️ Missão Zero - Teste de Autonomia

Execute o teste completo de autonomia:

```bash
# Executar Missão Zero
python tests/mission_zero_autonomy.py --verbose

# Ou usar o script wrapper (Linux/Mac)
./bin/test-autonomy
```

### O que a Missão Zero faz:

1. **Visão**: Captura screenshot da tela
2. **Percepção**: Localiza o campo de chat do Kiro
3. **Movimento**: Move o mouse com curva suave (Bézier)
4. **Interação**: Clica e digita mensagem de autenticação
5. **Verificação**: Valida que a mensagem apareceu

### Mensagem esperada:

```
Controle de Autonomia: Eu sou o Viajante e este é o meu primeiro passo no Bunker.
```

## 📁 Estrutura de Arquivos

```
.
├── bin/
│   ├── capture_view.py       # Módulo de visão
│   ├── jitbit_bridge.py      # Ponte Jitbit/AutoIt
│   ├── calibrate_ui.py       # Calibração de UI
│   ├── check_readiness.cmd   # Verificação (Windows)
│   └── check_readiness.sh    # Verificação (Linux/Mac)
├── specs/
│   └── ui_map.json           # Mapa de coordenadas
├── tests/
│   └── mission_zero_autonomy.py  # Teste de autonomia
├── temp/                     # Screenshots temporários
├── logs/                     # Logs de execução
├── macros/                   # Macros do Jitbit
└── requirements.txt          # Dependências Python
```

## 📚 Documentação Completa

Para documentação detalhada, consulte:

- **Atlas do Viajante**: `.kiro/specs/rpg-cortex/atlas_and_conduct.md`
- **Missão Zero**: `.kiro/specs/rpg-cortex/mission_zero.md`
- **Instruções Claude**: `.kiro/specs/rpg-cortex/CLAUDE_INSTRUCTIONS.md`
- **README**: `.kiro/specs/rpg-cortex/README.md`
- **Setup Infraestrutura**: `docs/INFRASTRUCTURE_SETUP.md`

## 🔍 Troubleshooting

### Erro: "pyautogui não instalado"

```bash
pip install pyautogui pillow
```

### Erro: "Permissão negada"

```bash
# Criar diretórios manualmente
mkdir temp logs macros
```

### Erro: "Módulo não encontrado"

```bash
# Verificar ambiente virtual está ativado
.venv\Scripts\activate

# Reinstalar dependências
pip install -r requirements.txt
```

### Scripts não executam

```bash
# Windows: Usar python explicitamente
python bin/capture_view.py

# Linux/Mac: Dar permissão de execução
chmod +x bin/*.py bin/*.sh
```

## 🎮 Próximos Passos

1. ✅ Verificar prontidão: `bin\check_readiness.cmd`
2. ✅ Calibrar UI: `python bin/calibrate_ui.py`
3. ✅ Testar visão: `python bin/capture_view.py --metadata`
4. ✅ Testar controle: `python bin/jitbit_bridge.py --info`
5. 🎯 Executar Missão Zero: `python tests/mission_zero_autonomy.py --verbose`

## 🚨 Segurança

- **Emergency Stop**: Mova o mouse para o canto superior esquerdo para cancelar
- **Zonas Proibidas**: Definidas em `specs/ui_map.json`
- **Logs**: Todas as ações são registradas em `logs/`

## 📞 Suporte

Se encontrar problemas:

1. Verificar logs em `logs/mission_zero.log`
2. Verificar screenshots em `temp/`
3. Executar `bin\check_readiness.cmd` para diagnóstico
4. Consultar documentação em `.kiro/specs/rpg-cortex/`

---

**O Bunker está pronto. O Viajante aguarda suas ordens.**
