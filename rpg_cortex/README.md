# RPG-Cortex - Medula Espinhal (Phase 1)

Primitivas de hardware e movimento orgânico para controle de PC via IA.

## Estrutura

```
rpg_cortex/
├── hardware/
│   ├── rpg_controls.py    # Clique, digitação, captura de tela
│   ├── smooth_movement.py # Movimento Bezier (humanizado)
│   ├── cartographer.py    # Mapeador de janelas (Cursor, Kiro)
│   └── emergency.py       # Emergency Stop
├── knowledge/
│   └── mapa_interface.json # Gerado pelo cartographer
├── logs/
│   └── hardware.log
└── tests/
    └── first_step.py     # Teste de vida
```

## Instalação

```powershell
pip install pyautogui
```

## Uso

```python
from rpg_cortex.hardware import (
    click_at,
    move_to_coord,
    take_vision,
    type_text,
    map_interface,
    travel_to,
)
```

## Teste First Step

```powershell
cd rpg_cortex
python tests/first_step.py
```

**Emergency Stop:** ESC ou Ctrl+C

O script:
1. Mapeia janelas Cursor e Kiro
2. Move o mouse organicamente do centro até o chat do Kiro
3. Dá um clique no campo de digitação
4. Captura screenshot

## Permissões Windows

Se houver erro de permissão de tela, execute o terminal como Administrador ou ajuste o Manifesto de Execução para solicitar permissões de captura de tela.
