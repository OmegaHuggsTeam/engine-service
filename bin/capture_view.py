#!/usr/bin/env python3
"""
Módulo de Visão: Captura de Screenshots
Permite que o Claude "enxergue" o monitor através de capturas de tela.

Uso:
    python bin/capture_view.py                    # Captura tela inteira
    python bin/capture_view.py --region 0 0 800 600  # Captura região específica
    python bin/capture_view.py --window "Kiro"    # Captura janela específica
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

try:
    import pyautogui
    from PIL import Image
except ImportError as e:
    print(f"❌ Erro: Dependência faltando - {e}")
    print("Execute: pip install pyautogui pillow")
    sys.exit(1)


class VisionCapture:
    """Módulo de captura de screenshots para o Viajante."""
    
    def __init__(self, output_dir: str = "temp/vision"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Desabilitar failsafe do pyautogui para automação
        pyautogui.FAILSAFE = False
    
    def capture_full_screen(self, filename: str = None) -> Path:
        """Captura a tela inteira."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fullscreen_{timestamp}.png"
        
        output_path = self.output_dir / filename
        
        print(f"📸 Capturando tela inteira...")
        screenshot = pyautogui.screenshot()
        screenshot.save(output_path)
        
        size = output_path.stat().st_size
        width, height = screenshot.size
        
        print(f"✓ Screenshot salvo: {output_path}")
        print(f"  Dimensões: {width}x{height}")
        print(f"  Tamanho: {size:,} bytes")
        
        return output_path
    
    def capture_region(self, x: int, y: int, width: int, height: int, filename: str = None) -> Path:
        """Captura uma região específica da tela."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"region_{x}_{y}_{width}x{height}_{timestamp}.png"
        
        output_path = self.output_dir / filename
        
        print(f"📸 Capturando região ({x}, {y}, {width}x{height})...")
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        screenshot.save(output_path)
        
        size = output_path.stat().st_size
        
        print(f"✓ Screenshot salvo: {output_path}")
        print(f"  Dimensões: {width}x{height}")
        print(f"  Tamanho: {size:,} bytes")
        
        return output_path
    
    def get_screen_size(self) -> tuple:
        """Retorna as dimensões da tela."""
        size = pyautogui.size()
        return size.width, size.height
    
    def capture_with_metadata(self, filename: str = None, **kwargs) -> dict:
        """Captura screenshot e retorna metadados completos."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"capture_{timestamp}.png"
        
        # Capturar
        if 'region' in kwargs:
            x, y, w, h = kwargs['region']
            output_path = self.capture_region(x, y, w, h, filename)
        else:
            output_path = self.capture_full_screen(filename)
        
        # Coletar metadados
        screen_width, screen_height = self.get_screen_size()
        mouse_x, mouse_y = pyautogui.position()
        
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "file_path": str(output_path.absolute()),
            "file_size_bytes": output_path.stat().st_size,
            "screen_dimensions": {
                "width": screen_width,
                "height": screen_height
            },
            "mouse_position": {
                "x": mouse_x,
                "y": mouse_y
            }
        }
        
        # Salvar metadados
        metadata_path = output_path.with_suffix('.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✓ Metadados salvos: {metadata_path}")
        
        return metadata


def main():
    parser = argparse.ArgumentParser(
        description="Módulo de Visão: Captura screenshots para o Viajante"
    )
    parser.add_argument(
        '--region', '-r',
        nargs=4,
        type=int,
        metavar=('X', 'Y', 'WIDTH', 'HEIGHT'),
        help='Capturar região específica (x y width height)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Nome do arquivo de saída (padrão: timestamp automático)'
    )
    parser.add_argument(
        '--dir', '-d',
        type=str,
        default='temp/vision',
        help='Diretório de saída (padrão: temp/vision)'
    )
    parser.add_argument(
        '--metadata', '-m',
        action='store_true',
        help='Salvar metadados em JSON'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Mostrar informações da tela e sair'
    )
    
    args = parser.parse_args()
    
    # Criar capturador
    capture = VisionCapture(output_dir=args.dir)
    
    # Modo info
    if args.info:
        width, height = capture.get_screen_size()
        mouse_x, mouse_y = pyautogui.position()
        print(f"📊 Informações da Tela:")
        print(f"  Dimensões: {width}x{height}")
        print(f"  Posição do Mouse: ({mouse_x}, {mouse_y})")
        return 0
    
    # Capturar
    try:
        if args.metadata:
            metadata = capture.capture_with_metadata(filename=args.output)
            print(f"\n📋 Metadados:")
            print(json.dumps(metadata, indent=2))
        elif args.region:
            x, y, w, h = args.region
            capture.capture_region(x, y, w, h, filename=args.output)
        else:
            capture.capture_full_screen(filename=args.output)
        
        return 0
        
    except Exception as e:
        print(f"❌ Erro ao capturar: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
