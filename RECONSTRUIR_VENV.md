# Reconstrucao do Ambiente Virtual (.venv)

## Pre-requisito

**Feche o Cursor completamente** antes de executar. O `.venv` fica bloqueado enquanto o IDE esta aberto.

## Opcao A: PowerShell (recomendado)

Abra um **novo PowerShell** (fora do Cursor) e execute:

```powershell
cd C:\labs\inteligence\mcp-engine-service
.\scripts\rebuild_venv.ps1
```

## Opcao B: Manual

### 1. Instalar Python 3.12 (se nao tiver)

- Baixe em: https://www.python.org/downloads/release/python-3120/
- Marque "Add Python to PATH"
- Ou use o Python Launcher: `py -3.12`

### 2. Remover .venv antigo

```powershell
cd C:\labs\inteligence\mcp-engine-service
Remove-Item -Recurse -Force .venv
```

Se falhar com "acesso negado", feche o Cursor e tente novamente.

### 3. Criar novo venv com Python 3.12

```powershell
# Se tiver python3.12 no PATH:
python3.12 -m venv .venv

# Ou com Python Launcher:
py -3.12 -m venv .venv

# Fallback (Python padrao):
python -m venv .venv
```

### 4. Instalar dependencias

```powershell
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Se **chromadb/pyroaring** falhar (erro de C++ Build Tools):

```powershell
pip install -r requirements-minimal.txt
```

Isso instala Selenium, Bot e Groq sem ChromaDB.

### 5. Validar

```powershell
python run_init.py
```

O resumo deve mostrar [OK] em "Dependencias".
