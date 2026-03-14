#!/usr/bin/env python3
"""
Ponte Jitbit/AutoIt: Interface para execução de macros
Permite que o Claude execute macros do Jitbit ou use pyautogui como fallback.

Uso:
    python bin/jitbit_bridge.py --execute macro_name.jmb
    python bin/jitbit_bridge.py --click 100 200
    python bin/jitbit_bridge.py --type "Hello World"
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    import pyautogui
except ImportError:
    print("❌ Erro: pyautogui não instalado")
    print("Execute: pip install pyautogui")
    sys.exit(1)


class JitbitBridge:
    """Ponte para execução de macros Jitbit e controle direto via pyautogui."""

    def __init__(self, jitbit_path: str = None, macros_dir: str = "macros"):
        self.jitbit_path = Path(jitbit_path) if jitbit_path else None
        self.macros_dir = Path(macros_dir)
        self.macros_dir.mkdir(parents=True, exist_ok=True)

        # Configurações de segurança
        pyautogui.FAILSAFE = True  # Mover mouse para canto superior esquerdo cancela
        pyautogui.PAUSE = 0.1  # Pausa entre comandos

    def execute_jitbit_macro(self, macro_file: str) -> bool:
        """Executa um macro do Jitbit via CLI."""
        macro_path = self.macros_dir / macro_file

        if not macro_path.exists():
            print(f"❌ Macro não encontrado: {macro_path}")
            return False

        if not self.jitbit_path or not self.jitbit_path.exists():
            print("⚠️  Jitbit CLI não configurado, usando fallback pyautogui")
            return False

        try:
            print(f"🎬 Executando macro Jitbit: {macro_file}")

            # Tentar executar via CLI do Jitbit
            # Nota: Ajustar comando conforme documentação do Jitbit
            result = subprocess.run(
                [str(self.jitbit_path), "/run", str(macro_path)],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print("✓ Macro executado com sucesso")
                return True
            else:
                print(f"❌ Erro ao executar macro: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("❌ Timeout ao executar macro (>60s)")
            return False
        except Exception as e:
            print(f"❌ Erro ao executar macro: {e}")
            return False

    def click_at(
        self, x: int, y: int, button: str = "left", clicks: int = 1, interval: float = 0.0
    ):
        """Clica em coordenadas específicas."""
        print(f"🖱️  Clicando em ({x}, {y}) - botão: {button}, cliques: {clicks}")

        try:
            pyautogui.click(x, y, clicks=clicks, interval=interval, button=button)
            print("✓ Click executado")
            return True
        except Exception as e:
            print(f"❌ Erro ao clicar: {e}")
            return False

    def move_to(self, x: int, y: int, duration: float = 0.5):
        """Move o mouse para coordenadas específicas."""
        print(f"🖱️  Movendo mouse para ({x}, {y}) em {duration}s")

        try:
            pyautogui.moveTo(x, y, duration=duration)
            print("✓ Mouse movido")
            return True
        except Exception as e:
            print(f"❌ Erro ao mover mouse: {e}")
            return False

    def type_text(self, text: str, interval: float = 0.05):
        """Digita texto com intervalo entre teclas."""
        print(f"⌨️  Digitando: '{text[:50]}{'...' if len(text) > 50 else ''}'")

        try:
            pyautogui.write(text, interval=interval)
            print(f"✓ Texto digitado ({len(text)} caracteres)")
            return True
        except Exception as e:
            print(f"❌ Erro ao digitar: {e}")
            return False

    def press_key(self, key: str, presses: int = 1, interval: float = 0.0):
        """Pressiona uma tecla específica."""
        print(f"⌨️  Pressionando tecla: {key} ({presses}x)")

        try:
            pyautogui.press(key, presses=presses, interval=interval)
            print("✓ Tecla pressionada")
            return True
        except Exception as e:
            print(f"❌ Erro ao pressionar tecla: {e}")
            return False

    def hotkey(self, *keys):
        """Executa combinação de teclas (ex: ctrl+c)."""
        keys_str = "+".join(keys)
        print(f"⌨️  Executando hotkey: {keys_str}")

        try:
            pyautogui.hotkey(*keys)
            print("✓ Hotkey executado")
            return True
        except Exception as e:
            print(f"❌ Erro ao executar hotkey: {e}")
            return False

    def get_mouse_position(self) -> tuple:
        """Retorna a posição atual do mouse."""
        x, y = pyautogui.position()
        return x, y

    def get_screen_size(self) -> tuple:
        """Retorna as dimensões da tela."""
        size = pyautogui.size()
        return size.width, size.height

    def execute_sequence(self, sequence_file: str) -> bool:
        """Executa uma sequência de ações definida em JSON."""
        sequence_path = Path(sequence_file)

        if not sequence_path.exists():
            print(f"❌ Arquivo de sequência não encontrado: {sequence_path}")
            return False

        try:
            with open(sequence_path, "r", encoding="utf-8") as f:
                sequence = json.load(f)

            print(f"🎬 Executando sequência: {sequence_path.name}")
            print(f"   Total de ações: {len(sequence.get('actions', []))}")

            for i, action in enumerate(sequence.get("actions", []), 1):
                action_type = action.get("type")
                print(f"\n[{i}/{len(sequence['actions'])}] Ação: {action_type}")

                if action_type == "click":
                    self.click_at(action["x"], action["y"], button=action.get("button", "left"))

                elif action_type == "move":
                    self.move_to(action["x"], action["y"], duration=action.get("duration", 0.5))

                elif action_type == "type":
                    self.type_text(action["text"], interval=action.get("interval", 0.05))

                elif action_type == "press":
                    self.press_key(action["key"], presses=action.get("presses", 1))

                elif action_type == "hotkey":
                    self.hotkey(*action["keys"])

                elif action_type == "wait":
                    wait_time = action.get("duration", 1.0)
                    print(f"⏳ Aguardando {wait_time}s...")
                    time.sleep(wait_time)

                else:
                    print(f"⚠️  Tipo de ação desconhecido: {action_type}")

                # Pausa entre ações
                if action.get("pause_after"):
                    time.sleep(action["pause_after"])

            print("\n✓ Sequência completa executada")
            return True

        except Exception as e:
            print(f"❌ Erro ao executar sequência: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Ponte Jitbit/AutoIt: Interface para execução de macros"
    )

    # Comandos principais
    parser.add_argument("--execute", "-e", type=str, help="Executar macro Jitbit (.jmb)")
    parser.add_argument("--sequence", "-s", type=str, help="Executar sequência JSON")
    parser.add_argument(
        "--click", nargs=2, type=int, metavar=("X", "Y"), help="Clicar em coordenadas"
    )
    parser.add_argument("--move", nargs=2, type=int, metavar=("X", "Y"), help="Mover mouse")
    parser.add_argument("--type", "-t", type=str, help="Digitar texto")
    parser.add_argument("--press", "-p", type=str, help="Pressionar tecla")
    parser.add_argument("--hotkey", nargs="+", help="Executar hotkey (ex: ctrl c)")

    # Opções
    parser.add_argument(
        "--button",
        default="left",
        choices=["left", "right", "middle"],
        help="Botão do mouse (padrão: left)",
    )
    parser.add_argument(
        "--duration", type=float, default=0.5, help="Duração do movimento (padrão: 0.5s)"
    )
    parser.add_argument(
        "--interval", type=float, default=0.05, help="Intervalo entre teclas (padrão: 0.05s)"
    )
    parser.add_argument("--jitbit-path", type=str, help="Caminho para executável do Jitbit")
    parser.add_argument(
        "--macros-dir", type=str, default="macros", help="Diretório de macros (padrão: macros)"
    )
    parser.add_argument("--info", action="store_true", help="Mostrar informações do sistema")

    args = parser.parse_args()

    # Criar bridge
    bridge = JitbitBridge(jitbit_path=args.jitbit_path, macros_dir=args.macros_dir)

    # Modo info
    if args.info:
        x, y = bridge.get_mouse_position()
        width, height = bridge.get_screen_size()
        print("📊 Informações do Sistema:")
        print(f"  Posição do Mouse: ({x}, {y})")
        print(f"  Dimensões da Tela: {width}x{height}")
        print(f"  Diretório de Macros: {bridge.macros_dir.absolute()}")
        if bridge.jitbit_path:
            print(f"  Jitbit Path: {bridge.jitbit_path}")
        return 0

    # Executar comandos
    success = False

    if args.execute:
        success = bridge.execute_jitbit_macro(args.execute)

    elif args.sequence:
        success = bridge.execute_sequence(args.sequence)

    elif args.click:
        x, y = args.click
        success = bridge.click_at(x, y, button=args.button)

    elif args.move:
        x, y = args.move
        success = bridge.move_to(x, y, duration=args.duration)

    elif args.type:
        success = bridge.type_text(args.type, interval=args.interval)

    elif args.press:
        success = bridge.press_key(args.press)

    elif args.hotkey:
        success = bridge.hotkey(*args.hotkey)

    else:
        parser.print_help()
        return 1

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
