"""
Inicia o bot do Telegram.

Uso: python scripts/run_telegram_bot.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.interfaces.telegram_handler import run_bot

if __name__ == "__main__":
    run_bot()
