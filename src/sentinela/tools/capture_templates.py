"""
Visual Calibration Tool - Capture anchor templates from Dashboard.

This tool helps users create accurate templates for the Sentinela visual system.

Usage:
    python -m src.sentinela.tools.capture_templates

Features:
- Interactive template capture
- Automatic anchor extraction
- Visual preview of captured regions
- Validation of template quality
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import Tuple, Optional, List
import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.sentinela.screenshot_analyzer import ScreenshotAnalyzer
from src.sentinela.exceptions import CatarataError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class TemplateCaptureSession:
    """Interactive session for capturing visual templates."""
    
    def __init__(self, output_dir: str = "./templates"):
        """
        Initialize capture session.
        
        Args:
            output_dir: Directory to save captured templates
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.analyzer = ScreenshotAnalyzer()
        self.captured_templates = []
    
    def wait_for_user_confirmation(self, message: str, timeout: int = 30) -> bool:
        """
        Wait for user to confirm they're ready.
        
        Args:
            message: Message to display
            timeout: Seconds to wait for confirmation
            
        Returns:
            True if user confirmed, False if timeout
        """
        print(f"\n{'='*70}")
        print(message)
        print(f"{'='*70}")
        print(f"\nPressione ENTER quando estiver pronto (timeout em {timeout}s)...")
        
        # Simple input with timeout would require threading
        # For now, just wait for input
        try:
            input()
            return True
        except KeyboardInterrupt:
            print("\n✗ Cancelado pelo usuário")
            return False
    
    def capture_full_screenshot(self) -> Optional[np.ndarray]:
        """
        Capture full screenshot of current screen.
        
        Returns:
            Screenshot array or None if failed
        """
        try:
            screenshot = self.analyzer.capture_screenshot()
            logger.info(f"Screenshot capturado: {screenshot.shape}")
            return screenshot
        except CatarataError as e:
            logger.error(f"Catarata detectada: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao capturar screenshot: {e}")
            return None
    
    def select_region_interactive(
        self,
        screenshot: np.ndarray,
        region_name: str,
        suggested_coords: Optional[Tuple[int, int, int, int]] = None
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        Let user select a region from screenshot.
        
        Args:
            screenshot: Full screenshot
            region_name: Name of region being selected
            suggested_coords: Optional (x, y, width, height) suggestion
            
        Returns:
            (x, y, width, height) or None if cancelled
        """
        print(f"\n--- Selecionando região: {region_name} ---")
        
        if suggested_coords:
            x, y, w, h = suggested_coords
            print(f"Região sugerida: x={x}, y={y}, width={w}, height={h}")
            print("Pressione ENTER para aceitar ou digite novas coordenadas")
            print("Formato: x,y,width,height (ex: 10,10,100,50)")
            
            user_input = input("> ").strip()
            
            if not user_input:
                # Accept suggestion
                return suggested_coords
            
            try:
                parts = user_input.split(',')
                if len(parts) == 4:
                    return tuple(int(p.strip()) for p in parts)
            except ValueError:
                logger.warning("Coordenadas inválidas, usando sugestão")
                return suggested_coords
        else:
            print("Digite as coordenadas da região:")
            print("Formato: x,y,width,height (ex: 10,10,100,50)")
            
            user_input = input("> ").strip()
            
            if not user_input:
                logger.warning("Nenhuma coordenada fornecida")
                return None
            
            try:
                parts = user_input.split(',')
                if len(parts) == 4:
                    return tuple(int(p.strip()) for p in parts)
            except ValueError:
                logger.error("Formato inválido")
                return None
        
        return suggested_coords
    
    def extract_region(
        self,
        screenshot: np.ndarray,
        coords: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """
        Extract region from screenshot.
        
        Args:
            screenshot: Full screenshot
            coords: (x, y, width, height)
            
        Returns:
            Extracted region
        """
        x, y, w, h = coords
        
        # Ensure coordinates are within bounds
        x = max(0, min(x, screenshot.shape[1] - 1))
        y = max(0, min(y, screenshot.shape[0] - 1))
        w = max(1, min(w, screenshot.shape[1] - x))
        h = max(1, min(h, screenshot.shape[0] - y))
        
        region = screenshot[y:y+h, x:x+w]
        return region
    
    def save_template(
        self,
        template: np.ndarray,
        name: str,
        show_preview: bool = True
    ) -> bool:
        """
        Save template to disk.
        
        Args:
            template: Template image
            name: Template name (without extension)
            show_preview: Whether to show preview
            
        Returns:
            True if saved successfully
        """
        output_path = self.output_dir / f"{name}.png"
        
        try:
            # Convert RGB to BGR for OpenCV
            template_bgr = cv2.cvtColor(template, cv2.COLOR_RGB2BGR)
            
            # Save
            cv2.imwrite(str(output_path), template_bgr)
            
            logger.info(f"✓ Template salvo: {output_path}")
            
            # Show preview if requested
            if show_preview:
                print(f"\nPreview do template '{name}':")
                print(f"  Dimensões: {template.shape[1]}x{template.shape[0]}")
                print(f"  Tamanho: {os.path.getsize(output_path)} bytes")
            
            self.captured_templates.append(name)
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar template: {e}")
            return False
    
    def capture_anchor_templates(self) -> bool:
        """
        Capture all 3 anchor templates interactively.
        
        Returns:
            True if all anchors captured successfully
        """
        print("\n" + "="*70)
        print("SENTINELA VISUAL CALIBRATION TOOL")
        print("Captura de Templates de Ancoragem")
        print("="*70)
        
        # Step 1: Wait for Dashboard to be ready
        if not self.wait_for_user_confirmation(
            "PASSO 1: Abra o Dashboard no navegador\n"
            "Certifique-se de que:\n"
            "  - Dashboard está completamente carregado\n"
            "  - Nenhuma notificação está cobrindo a tela\n"
            "  - Janela está em foco e maximizada"
        ):
            return False
        
        # Step 2: Capture full screenshot
        print("\n📸 Capturando screenshot do Dashboard...")
        time.sleep(1)  # Give user time to focus
        
        screenshot = self.capture_full_screenshot()
        if screenshot is None:
            logger.error("Falha ao capturar screenshot")
            return False
        
        # Save full screenshot for reference
        reference_path = self.output_dir / "_reference_screenshot.png"
        cv2.imwrite(str(reference_path), cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR))
        logger.info(f"Screenshot de referência salvo: {reference_path}")
        
        # Step 3: Capture each anchor
        anchors = [
            {
                "name": "dashboard_logo",
                "description": "Logo do projeto (geralmente canto superior esquerdo)",
                "suggested": (10, 10, 150, 80)  # x, y, width, height
            },
            {
                "name": "refresh_button",
                "description": "Botão de Refresh/Atualizar",
                "suggested": (screenshot.shape[1] - 200, 10, 120, 60)
            },
            {
                "name": "status_icon",
                "description": "Ícone de Status do sistema",
                "suggested": (screenshot.shape[1] - 100, screenshot.shape[0] - 100, 80, 80)
            },
        ]
        
        for anchor in anchors:
            print(f"\n{'='*70}")
            print(f"Capturando: {anchor['name']}")
            print(f"Descrição: {anchor['description']}")
            print(f"{'='*70}")
            
            # Get region coordinates
            coords = self.select_region_interactive(
                screenshot,
                anchor['name'],
                suggested_coords=anchor['suggested']
            )
            
            if coords is None:
                logger.warning(f"Pulando {anchor['name']}")
                continue
            
            # Extract region
            template = self.extract_region(screenshot, coords)
            
            # Validate template size
            if template.shape[0] < 20 or template.shape[1] < 20:
                logger.warning(f"Template muito pequeno: {template.shape}")
                print("Recomendação: Use template maior (mínimo 30x30 pixels)")
                continue
            
            if template.shape[0] > 300 or template.shape[1] > 300:
                logger.warning(f"Template muito grande: {template.shape}")
                print("Recomendação: Use template menor (máximo 200x200 pixels)")
            
            # Save template
            if self.save_template(template, anchor['name']):
                print(f"✓ {anchor['name']} capturado com sucesso!")
            else:
                logger.error(f"Falha ao salvar {anchor['name']}")
        
        # Summary
        print(f"\n{'='*70}")
        print("RESUMO DA CAPTURA")
        print(f"{'='*70}")
        print(f"Templates capturados: {len(self.captured_templates)}/3")
        for name in self.captured_templates:
            print(f"  ✓ {name}")
        
        if len(self.captured_templates) == 3:
            print(f"\n🎉 Todos os anchors capturados com sucesso!")
            print(f"\nPróximos passos:")
            print(f"  1. Teste os templates: python examples/sentinela_visual_demo.py")
            print(f"  2. Ajuste confidence_threshold se necessário")
            print(f"  3. Capture templates de alerta se necessário")
            return True
        else:
            print(f"\n⚠ Alguns anchors não foram capturados")
            print(f"Execute novamente para capturar os faltantes")
            return False


def main():
    """Run template capture tool."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Sentinela Visual Calibration Tool - Capture anchor templates"
    )
    parser.add_argument(
        "--output-dir",
        default="./templates",
        help="Output directory for templates (default: ./templates)"
    )
    
    args = parser.parse_args()
    
    # Create session
    session = TemplateCaptureSession(output_dir=args.output_dir)
    
    # Run capture
    success = session.capture_anchor_templates()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
