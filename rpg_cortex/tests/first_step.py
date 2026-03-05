"""
First Step - Teste de "Vida" da Medula Espinhal.
1. Mapeia janelas (Cursor, Kiro)
2. Mouse viaja organicamente do centro da tela ate o chat do Kiro
3. Clique de "ola" no campo de digitacao

Emergency Stop: ESC ou Ctrl+C
"""

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Flag de Emergency Stop
_stop_requested = False


def _listen_emergency_stop():
    """Thread que escuta ESC ou Ctrl+C."""
    global _stop_requested
    try:
        import msvcrt
        while not _stop_requested:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b"\x1b", b"\x03"):  # ESC ou Ctrl+C
                    _stop_requested = True
                    print("\n[EMERGENCY STOP] ESC/Ctrl+C detectado.")
                    from hardware.rpg_controls import trigger_emergency_stop
                    trigger_emergency_stop()
                    break
            time.sleep(0.05)
    except ImportError:
        pass  # msvcrt so no Windows


def run_first_step():
    """Executa o teste de vida."""
    global _stop_requested
    from hardware.rpg_controls import (
        check_emergency_stop,
        trigger_emergency_stop,
        reset_emergency_stop,
        take_vision,
        click_at,
        move_to_coord,
    )
    from hardware.cartographer import map_interface, get_kiro_chat_coords, get_screen_center

    print("=" * 50)
    print("RPG-Cortex - First Step (Medula Espinhal)")
    print("Emergency Stop: ESC ou Ctrl+C")
    print("=" * 50)

    # Thread de Emergency Stop
    stop_thread = threading.Thread(target=_listen_emergency_stop, daemon=True)
    stop_thread.start()

    try:
        reset_emergency_stop()

        # 1. Mapear janelas
        print("\n1. Mapeando janelas (Cursor, Kiro)...")
        mapa = map_interface()
        if mapa.get("cursor"):
            print(f"   Cursor: {mapa['cursor']['title'][:40]}...")
        if mapa.get("kiro"):
            print(f"   Kiro: {mapa['kiro']['title'][:40]}...")
        if not mapa.get("kiro") and not mapa.get("cursor"):
            print("   AVISO: Nenhuma janela Cursor/Kiro encontrada. Usando centro da tela.")

        if check_emergency_stop():
            return

        # 2. Coordenadas
        center = get_screen_center()
        kiro_coords = get_kiro_chat_coords()
        target = kiro_coords if kiro_coords else center

        print(f"\n2. Origem: centro da tela {center}")
        print(f"   Destino: chat Kiro {target}")

        # 3. Viajar organicamente ate o chat
        print("\n3. Movimento organico (Bezier)...")
        move_to_coord(center[0], center[1], speed=1.0)
        if check_emergency_stop():
            return
        move_to_coord(target[0], target[1], speed=1.0)

        if check_emergency_stop():
            return

        # 4. Clique de ola
        print("\n4. Clique de ola no campo de digitacao...")
        click_at(target[0], target[1], button="left")

        # 5. Captura de visao (opcional)
        if not check_emergency_stop():
            print("\n5. Capturando visao (screenshot)...")
            out = take_vision(output_path=ROOT / "temp" / "first_step_vision.png")
            print(f"   Salvo em: {out}")

        print("\n" + "=" * 50)
        print("First Step concluido!")
        print("=" * 50)

    except KeyboardInterrupt:
        print("\n[Interrompido] Ctrl+C")
        trigger_emergency_stop()
    except Exception as e:
        print(f"\n[ERRO] {e}")
        raise


if __name__ == "__main__":
    run_first_step()
