#!/usr/bin/env python3
"""
Calibração de UI: Ferramenta para mapear coordenadas de elementos
Permite que o usuário clique em elementos para registrar suas coordenadas.

Uso:
    python bin/calibrate_ui.py

Instruções:
    1. O script mostrará a posição do mouse em tempo real
    2. Posicione o mouse sobre o elemento desejado
    3. Pressione ESPAÇO para registrar a coordenada
    4. Pressione ESC para finalizar
"""

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
    from pynput import keyboard
except ImportError as e:
    print(f"❌ Erro: Dependência faltando - {e}")
    print("Execute: pip install pyautogui pynput")
    sys.exit(1)


class UICalibrator:
    """Ferramenta de calibração de coordenadas da UI."""

    def __init__(self, ui_map_path: str = "specs/ui_map.json"):
        self.ui_map_path = Path(ui_map_path)
        self.calibration_points = []
        self.running = True

        # Carregar mapa existente
        if self.ui_map_path.exists():
            with open(self.ui_map_path, "r", encoding="utf-8") as f:
                self.ui_map = json.load(f)
        else:
            print(f"⚠️  Mapa UI não encontrado: {self.ui_map_path}")
            self.ui_map = {}

    def on_press(self, key):
        """Handler para teclas pressionadas."""
        try:
            if key == keyboard.Key.space:
                # Registrar coordenada atual
                x, y = pyautogui.position()

                element_name = input(
                    f"\n📍 Coordenada capturada: ({x}, {y})\n   Nome do elemento: "
                )

                if element_name:
                    self.calibration_points.append(
                        {
                            "name": element_name,
                            "x": x,
                            "y": y,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    print(f"✓ '{element_name}' registrado em ({x}, {y})")

                print("\n[ESPAÇO] Capturar | [ESC] Finalizar")
                print("Posição do mouse: ", end="", flush=True)

            elif key == keyboard.Key.esc:
                # Finalizar calibração
                print("\n\n🛑 Finalizando calibração...")
                self.running = False
                return False  # Para o listener

        except Exception as e:
            print(f"\n❌ Erro: {e}")

    def run(self):
        """Executar calibração interativa."""
        print("=" * 60)
        print("🎯 Calibração de UI - Mapeamento de Coordenadas")
        print("=" * 60)
        print()
        print("Instruções:")
        print("  1. Mova o mouse sobre o elemento desejado")
        print("  2. Pressione ESPAÇO para registrar a coordenada")
        print("  3. Digite o nome do elemento")
        print("  4. Pressione ESC quando terminar")
        print()
        print("Elementos sugeridos para calibrar:")
        print("  - kiro_chat_input (campo de entrada do chat)")
        print("  - kiro_send_button (botão de enviar)")
        print("  - jitbit_window (janela do Jitbit)")
        print()
        print("[ESPAÇO] Capturar | [ESC] Finalizar")
        print()
        print("Posição do mouse: ", end="", flush=True)

        # Mostrar posição do mouse em tempo real
        try:
            with keyboard.Listener(on_press=self.on_press) as listener:
                while self.running:
                    x, y = pyautogui.position()
                    print(f"\rPosição do mouse: ({x:4d}, {y:4d})", end="", flush=True)

                    import time

                    time.sleep(0.1)

                listener.join()

        except KeyboardInterrupt:
            print("\n\n🛑 Calibração interrompida")

        # Salvar resultados
        if self.calibration_points:
            self.save_calibration()
        else:
            print("\n⚠️  Nenhum ponto calibrado")

    def save_calibration(self):
        """Salvar pontos calibrados no mapa UI."""
        print(f"\n\n💾 Salvando {len(self.calibration_points)} pontos calibrados...")

        # Atualizar mapa UI
        if "elements" not in self.ui_map:
            self.ui_map["elements"] = {}

        for point in self.calibration_points:
            element_key = point["name"].lower().replace(" ", "_")

            self.ui_map["elements"][element_key] = {
                "name": point["name"],
                "coordinates": {"x": point["x"], "y": point["y"]},
                "calibrated_at": point["timestamp"],
                "confidence_required": 0.80,
                "safe_zone": True,
            }

            print(f"  ✓ {point['name']}: ({point['x']}, {point['y']})")

        # Atualizar metadados de calibração
        if "calibration" not in self.ui_map:
            self.ui_map["calibration"] = {}

        self.ui_map["calibration"]["last_calibrated"] = datetime.now().isoformat()
        self.ui_map["calibration"]["calibration_required"] = False
        self.ui_map["calibration"]["points_calibrated"] = len(self.calibration_points)

        # Salvar arquivo
        self.ui_map_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.ui_map_path, "w", encoding="utf-8") as f:
            json.dump(self.ui_map, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Calibração salva em: {self.ui_map_path}")
        print(f"   Total de elementos: {len(self.ui_map.get('elements', {}))}")

        # Criar backup
        backup_path = self.ui_map_path.with_suffix(".backup.json")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(self.ui_map, f, indent=2, ensure_ascii=False)

        print(f"   Backup criado: {backup_path}")


def main():
    calibrator = UICalibrator()
    calibrator.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
