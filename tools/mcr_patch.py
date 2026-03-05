"""
Gera macro Jitbit (.mcr) corrigido com Safety Buffers e bloco de sanitização.

Abstrações de Controle:
- Home State: (443, 422) - ponto de idempotência do loop
- Safety Buffers: Margens de segurança de rede (delays mínimos)
- Garbage Collector: Bloco de sanitização injetado no final (On Error -> GoTo Sanitization)

Uso:
  python tools/mcr_patch.py
  python tools/mcr_patch.py --input macro-jitbit-test.mcr --output macro-jitbit-test-patched.mcr
  python tools/mcr_patch.py --dry-run
"""

import argparse
import re
from pathlib import Path
from typing import Optional

# Constantes alinhadas com docs/MACRO_JITBIT_DEBUG.md
HOME_STATE = (443, 422)
DEFAULT_INPUT = Path(__file__).parent.parent / "macro-jitbit-test.mcr"
DEFAULT_OUTPUT = Path(__file__).parent.parent / "macro-jitbit-test-patched.mcr"
SANITIZATION_BLOCK_PATH = Path(__file__).parent.parent / "macro-jitbit-sanitization-block.mcr"

# Mapeamento: (linha 1-based ou padrão, valor_atual) -> valor_novo
# Para substituição exata de DELAY
DELAY_REPLACEMENTS: list[tuple[int | str, int, int]] = [
    (1, 597, 800),           # Início - estabilização UI
    ("927", 927, 1200),      # Antes de (504, 4) - carregamento aba
    ("3321", 3321, 4000),    # Tab -> digitação - formulário dinâmico
    ("234", 234, 400),       # Após Ctrl+V - cola em campo
]

# Delays em tab bar: se DELAY 2-10 precede Mouse com y <= 35, substituir por 100
TAB_BAR_SAFETY_MS = 100
TAB_BAR_Y_THRESHOLD = 35


def _load_sanitization_block(home_x: int, home_y: int) -> str:
    """Carrega bloco de sanitização com Home State parametrizado."""
    if SANITIZATION_BLOCK_PATH.exists():
        block = SANITIZATION_BLOCK_PATH.read_text(encoding="utf-8")
        # Substitui coordenadas fixas (443, 422) por parametrizadas
        block = re.sub(r"Mouse : 443 : 422 :", f"Mouse : {home_x} : {home_y} :", block)
        return block.strip()
    # Fallback inline
    return f"""DELAY : 500
Keyboard : ControlLeft : KeyDown
Keyboard : W : KeyDown
Keyboard : W : KeyUp
Keyboard : ControlLeft : KeyUp
DELAY : 150
Keyboard : ControlLeft : KeyDown
Keyboard : W : KeyDown
Keyboard : W : KeyUp
Keyboard : ControlLeft : KeyUp
DELAY : 150
Keyboard : ControlLeft : KeyDown
Keyboard : W : KeyDown
Keyboard : W : KeyUp
Keyboard : ControlLeft : KeyUp
DELAY : 150
Keyboard : ControlLeft : KeyDown
Keyboard : W : KeyDown
Keyboard : W : KeyUp
Keyboard : ControlLeft : KeyUp
DELAY : 150
Keyboard : ControlLeft : KeyDown
Keyboard : W : KeyDown
Keyboard : W : KeyUp
Keyboard : ControlLeft : KeyUp
DELAY : 300
Mouse : {home_x} : {home_y} : Move : 0 : 0 : 0
DELAY : 100
Mouse : {home_x} : {home_y} : LeftButtonDown : 0 : 0 : 0
DELAY : 50
Mouse : {home_x} : {home_y} : LeftButtonUp : 0 : 0 : 0
DELAY : 200"""


def _parse_mouse_y(line: str) -> Optional[int]:
    """Extrai coordenada Y de linha Mouse. Retorna None se não for Mouse."""
    m = re.match(r"Mouse\s*:\s*\d+\s*:\s*(\d+)\s*:", line)
    return int(m.group(1)) if m else None


def _is_tab_bar_click(line: str) -> bool:
    """True se linha é Mouse com Y na zona da barra de abas."""
    y = _parse_mouse_y(line)
    return y is not None and y <= TAB_BAR_Y_THRESHOLD


def _get_delay_value(line: str) -> Optional[int]:
    """Extrai valor de DELAY. Retorna None se não for DELAY."""
    m = re.match(r"DELAY\s*:\s*(\d+)", line.strip())
    return int(m.group(1)) if m else None


def generate_patched_mcr(
    input_path: Path,
    output_path: Path,
    home_state: tuple[int, int] = HOME_STATE,
    dry_run: bool = False,
) -> dict:
    """
    Gera .mcr corrigido com Safety Buffers e bloco de sanitização.

    Returns:
        Dict com stats: lines_processed, delays_replaced, sanitization_appended
    """
    content = input_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    stats = {"lines_processed": len(lines), "delays_replaced": 0, "sanitization_appended": False}

    # 1. Substituir delays específicos
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("DELAY"):
            continue
        val = _get_delay_value(stripped)
        if val is None:
            continue

        # Substituições exatas por valor
        for key, old_val, new_val in DELAY_REPLACEMENTS:
            if isinstance(key, int):
                if key == i + 1 and val == old_val:
                    lines[i] = re.sub(r"DELAY\s*:\s*\d+", f"DELAY : {new_val}", line)
                    stats["delays_replaced"] += 1
                    break
            else:
                if val == old_val:
                    lines[i] = re.sub(r"DELAY\s*:\s*\d+", f"DELAY : {new_val}", line)
                    stats["delays_replaced"] += 1
                    break

    # 2. Safety buffer em tab bar: DELAY 2-10 antes de clique em barra de abas -> 100
    for i in range(len(lines) - 1):
        stripped = lines[i].strip()
        if not stripped.startswith("DELAY"):
            continue
        val = _get_delay_value(stripped)
        if val is None or val < 2 or val > 10:
            continue
        next_line = lines[i + 1].strip()
        if _is_tab_bar_click(next_line) and "LeftButtonDown" in next_line:
            lines[i] = re.sub(r"DELAY\s*:\s*\d+", f"DELAY : {TAB_BAR_SAFETY_MS}", lines[i])
            stats["delays_replaced"] += 1

    # 3. Remover duplicatas de substituição (evitar contar 2x o mesmo delay)
    # Já aplicado - cada linha é processada uma vez

    # 4. Anexar bloco de sanitização (Garbage Collector)
    sanitization = _load_sanitization_block(home_state[0], home_state[1])
    tail = "\n".join(lines[-60:])
    if "Keyboard : W : KeyDown" in tail and "Keyboard : W : KeyUp" in tail and f"Mouse : {home_state[0]} : {home_state[1]}" in tail:
        pass  # Já possui bloco de sanitização, não duplicar
    else:
        lines.append("")
        lines.append(sanitization)
        stats["sanitization_appended"] = True

    result = "\n".join(lines)

    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")

    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera macro Jitbit corrigido")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Arquivo .mcr de entrada")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Arquivo .mcr de saída")
    parser.add_argument("--home-x", type=int, default=HOME_STATE[0], help="Coordenada X do Home State")
    parser.add_argument("--home-y", type=int, default=HOME_STATE[1], help="Coordenada Y do Home State")
    parser.add_argument("--dry-run", action="store_true", help="Não gravar arquivo, apenas mostrar stats")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Arquivo não encontrado: {args.input}")
        return 1

    stats = generate_patched_mcr(
        args.input,
        args.output,
        home_state=(args.home_x, args.home_y),
        dry_run=args.dry_run,
    )

    print(f"Processadas {stats['lines_processed']} linhas")
    print(f"Delays substituídos: {stats['delays_replaced']}")
    print(f"Sanitização anexada: {stats['sanitization_appended']}")
    if not args.dry_run:
        print(f"Salvo em: {args.output.absolute()}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
