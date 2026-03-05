# 🛡️ Selum of Persistence - Quick Start

## 30 Segundos para o Primeiro Combate

### 1. Import
```python
from selenium import webdriver
from src.utils.selum_of_persistence import SelumOfPersistence
```

### 2. Inicializar
```python
driver = webdriver.Chrome()
selum = SelumOfPersistence(driver)
```

### 3. Usar
```python
# Clique resiliente
selum.strike(".button")

# Busca multi-idioma
element = selum.scout([
    {"text": "Settings"},
    {"text": "Configurações"}
])

# Espera inteligente
field = selum.vigilance("#input", timeout=20)
```

## 🎯 Manobras Principais

| Manobra | Uso | Quando Usar |
|---------|-----|-------------|
| `strike()` | Clique resiliente | Sempre que precisar clicar |
| `scout()` | Busca multi-seletor | Elementos com nomes variáveis |
| `vigilance()` | Espera inteligente | Conteúdo dinâmico |
| `cleansing_aura()` | Remove overlays | Antes de interações críticas |
| `steady_gaze()` | Scroll até elemento | Elementos fora do viewport |

## 📖 Documentação Completa

- **Guia Completo**: `docs/SELUM_GUIDE.md`
- **Spec Técnica**: `.kiro/specs/selum-persistence-paladin.md`
- **Exemplos**: `examples/selum_demo.py`

## 🧪 Testar

```bash
python tests/unit/test_selum_basic.py
```

## 🎮 Exemplo Completo

```python
from selenium import webdriver
from src.utils.selum_of_persistence import SelumOfPersistence

driver = webdriver.Chrome()
selum = SelumOfPersistence(driver)

try:
    driver.get("https://example.com")
    
    # Limpar obstáculos
    selum.cleansing_aura()
    
    # Buscar e clicar
    btn = selum.scout([{"text": "More information"}])
    if btn:
        selum.strike(btn)
    
    # Ver relatório
    report = selum.get_battle_report()
    print(f"Turnos: {len(report)}")
    
finally:
    driver.quit()
```

## 🏆 Pronto!

Você agora tem um Paladino ao seu lado para guiar seus cliques através das trevas do DOM! ⚔️🛡️

---

**Mais informações:** `docs/SELUM_GUIDE.md`
