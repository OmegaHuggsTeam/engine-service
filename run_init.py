"""
Self-Bootstrap - Chunk Generator (Lab Intelligence)
Unico comando para configurar TUDO do zero. Nao requer imports externos no inicio.

Flags: --hard-reset  Forca recriacao do .venv do zero
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import warnings
from pathlib import Path

# Suprime UserWarning do Pydantic (compatibilidade Python 3.14 / ChromaDB)
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic_core")

# Apenas stdlib - sem dotenv ou outras libs externas
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
REQUIREMENTS_CORE = PROJECT_ROOT / "requirements-core.txt"
ENV_PATH = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"
STATE_FILE = PROJECT_ROOT / ".run_init_state"
VENV_DIR = PROJECT_ROOT / ".venv"

# Cores ANSI (fallback Windows)
GREEN = "\033[92m" if sys.platform != "win32" else ""
YELLOW = "\033[93m" if sys.platform != "win32" else ""
RED = "\033[91m" if sys.platform != "win32" else ""
RESET = "\033[0m" if sys.platform != "win32" else ""


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}[AVISO]{RESET} {msg}")


def err(msg: str) -> None:
    print(f"  {RED}[ERRO]{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {title}")
    print("=" * 50)


def _in_venv() -> bool:
    """Verifica se esta rodando dentro de um ambiente virtual."""
    return (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
        or os.getenv("VIRTUAL_ENV")
    )


def _parse_env(path: Path) -> dict[str, str]:
    """Le .env sem depender de python-dotenv."""
    env = {}
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
    return env


def _create_env_with_comment() -> None:
    """Cria .env com comentario amigavel."""
    content = (
        "# Chunk Generator - Groq como LLM padrao\n"
        "# Adicione sua GROQ_API_KEY abaixo (obtenha em console.groq.com)\n\n"
        "GROQ_API_KEY=\n"
    )
    ENV_PATH.write_text(content, encoding="utf-8")
    ok(".env criado (adicione GROQ_API_KEY)")


def _save_env_key(key: str, value: str) -> None:
    """Adiciona ou atualiza chave no .env."""
    lines = []
    found = False
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip().startswith(f"{key}="):
                lines.append(f"{key}={value}")
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f"{key}={value}")
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _venv_python() -> Path | None:
    """Caminho do python dentro do .venv."""
    if sys.platform == "win32":
        exe = VENV_DIR / "Scripts" / "python.exe"
    else:
        exe = VENV_DIR / "bin" / "python"
    return exe if exe.exists() else None


def _check_python_314_warning() -> None:
    """Exibe aviso se rodando em Python 3.14 (experimental)."""
    vi = sys.version_info
    if vi.major == 3 and vi.minor == 14:
        warn("Rodando em Python 3.14 (Experimental). Algumas bibliotecas podem exigir reinstalacao constante.")


def _parse_version(v: str) -> tuple[int, ...]:
    """Converte string de versao em tupla para comparacao (ex: '1.2.3' -> (1, 2, 3))."""
    parts = []
    for x in v.strip().replace("-", ".").split("."):
        try:
            parts.append(int("".join(c for c in x if c.isdigit()) or "0"))
        except ValueError:
            parts.append(0)
    return tuple(parts) if parts else (0,)


def _version_satisfies(installed: str, spec: str) -> bool:
    """Verifica se versao instalada satisfaz o especificador (>=, ==, etc)."""
    inst = _parse_version(installed)
    spec = spec.strip()
    if ">=" in spec:
        _, req = spec.split(">=", 1)
        req_t = _parse_version(req.strip())
        return inst >= req_t
    if "==" in spec:
        _, req = spec.split("==", 1)
        req_t = _parse_version(req.strip())
        return inst == req_t
    if "~=" in spec:
        _, req = spec.split("~=", 1)
        req_t = _parse_version(req.strip())
        return inst >= req_t and (len(req_t) < 2 or inst[:2] == req_t[:2])
    return True


def _get_installed_packages() -> dict[str, str]:
    """Retorna dict {nome_normalizado: versao} do pip freeze."""
    result = {}
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
        )
        if r.returncode != 0:
            return {}
        for line in (r.stdout or "").splitlines():
            line = line.strip()
            if "==" in line:
                name, ver = line.split("==", 1)
                result[name.strip().lower().replace("-", "_")] = ver.strip()
    except (subprocess.TimeoutExpired, Exception):
        pass
    return result


def _parse_requirements(path: Path) -> list[tuple[str, str]]:
    """Retorna lista de (nome_pacote, especificador) do requirements.txt."""
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip().split("#")[0].strip()  # remove comentarios inline
        if not line:
            continue
        if "==" in line:
            name, spec = line.split("==", 1)
            out.append((name.strip().lower().replace("-", "_"), f"=={spec.strip()}"))
        elif ">=" in line:
            name, spec = line.split(">=", 1)
            out.append((name.strip().lower().replace("-", "_"), f">={spec.strip()}"))
        elif "~=" in line:
            name, spec = line.split("~=", 1)
            out.append((name.strip().lower().replace("-", "_"), f"~={spec.strip()}"))
        else:
            name = line.split()[0] if line.split() else line
            out.append((name.strip().lower().replace("-", "_"), ""))
    return out


def _requirements_already_satisfied() -> bool:
    """Compara pip freeze com requirements.txt. True se versoes batem."""
    installed = _get_installed_packages()
    reqs = _parse_requirements(REQUIREMENTS)
    for name, spec in reqs:
        norm = name.lower().replace("-", "_")
        if norm not in installed:
            return False
        if spec and not _version_satisfies(installed[norm], spec):
            return False
    return len(reqs) > 0


def _requirements_hash() -> str:
    """Hash do requirements.txt para detectar mudancas."""
    if not REQUIREMENTS.exists():
        return ""
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()[:16]


def _requirements_hash_changed() -> bool:
    """True se requirements.txt mudou desde ultima execucao."""
    current = _requirements_hash()
    if not current:
        return False
    if not STATE_FILE.exists():
        return False  # Primeira execucao - nao sugerir reset
    try:
        saved = STATE_FILE.read_text().strip()
        return saved != current
    except OSError:
        return True


def _save_requirements_hash() -> None:
    """Salva hash atual do requirements.txt."""
    h = _requirements_hash()
    if h:
        STATE_FILE.write_text(h, encoding="utf-8")


def _find_best_python() -> str:
    """Prioriza Python 3.12 > 3.11 > padrao."""
    candidates = []
    # py launcher (Windows)
    try:
        for ver in ["3.12", "3.11"]:
            r = subprocess.run(
                ["py", f"-{ver}", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                candidates.append((ver, r.stdout.strip()))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # python3.12, python3.11 no PATH
    for name in ["python3.12", "python3.11", "python312", "python311"]:
        try:
            r = subprocess.run(
                [name, "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout.strip():
                ver = "3.12" if "312" in name or "3.12" in name else "3.11"
                candidates.append((ver, r.stdout.strip()))
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    # Ordena: 3.12 primeiro, depois 3.11
    candidates.sort(key=lambda x: (0 if x[0] == "3.12" else 1 if x[0] == "3.11" else 2, x[1]))
    if candidates:
        return candidates[0][1]
    return sys.executable


def _kill_venv_processes() -> None:
    """Tenta encerrar processos que usam o .venv (Windows)."""
    if sys.platform != "win32":
        return
    venv_str = str(VENV_DIR).lower()
    try:
        r = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'", "get", "executablepath"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if r.returncode == 0 and venv_str in (r.stdout or "").lower():
            subprocess.run(["taskkill", "/F", "/IM", "python.exe"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _hard_reset_venv(force: bool = False) -> bool:
    """
    Recria .venv do zero. Prioriza Python 3.12.
    Instala wheel primeiro, depois requirements.
    """
    if not force:
        print("\n  Ambiente instavel detectado. Deseja recriar o .venv do zero? [Y/n]: ", end="")
        try:
            r = input().strip().lower()
            if r in ("n", "nao", "no"):
                return False
        except (EOFError, KeyboardInterrupt):
            return False

    section("Hard Reset - Recriando .venv")
    ok("Encerrando processos que usam .venv...")
    _kill_venv_processes()
    time.sleep(1)

    if VENV_DIR.exists():
        ok("Removendo .venv antigo...")
        try:
            shutil.rmtree(VENV_DIR)
            ok(".venv removido")
        except OSError as e:
            if sys.platform == "win32":
                ok("Tentando rmdir /s /q (fallback Windows)...")
                subprocess.run(
                    ["cmd", "/c", "rmdir", "/s", "/q", str(VENV_DIR)],
                    capture_output=True,
                    timeout=15,
                )
            if VENV_DIR.exists():
                err(f"Nao foi possivel remover: {e}")
                print("  Feche o Cursor e terminais. Depois: python run_init.py --hard-reset")
                return False
            ok(".venv removido")

    python_exe = _find_best_python()
    ok(f"Usando Python: {python_exe}")

    ok("Criando novo .venv...")
    try:
        subprocess.run(
            [python_exe, "-m", "venv", str(VENV_DIR)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        err(f"Falha ao criar venv: {e}")
        return False

    venv_py = _venv_python()
    if not venv_py:
        err("Python do venv nao encontrado")
        return False

    ok("Instalando wheel (evita erros de compilacao)...")
    subprocess.run(
        [str(venv_py), "-m", "pip", "install", "--upgrade", "pip", "wheel", "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        timeout=120,
    )

    req_file = REQUIREMENTS_CORE if REQUIREMENTS_CORE.exists() else REQUIREMENTS
    ok(f"Instalando dependencias ({req_file.name})...")
    r = subprocess.run(
        [str(venv_py), "-m", "pip", "install", "-r", str(req_file), "-q"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if r.returncode != 0:
        warn("Falha no requirements completo. Tentando requirements-core.txt...")
        if REQUIREMENTS_CORE.exists() and req_file != REQUIREMENTS_CORE:
            r = subprocess.run(
                [str(venv_py), "-m", "pip", "install", "-r", str(REQUIREMENTS_CORE), "-q"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=180,
            )
        if r.returncode != 0:
            err(r.stderr or r.stdout or "pip falhou")
            return False

    ok("Dependencias instaladas")
    _save_requirements_hash()
    return True


def _print_cpp_fallback_help() -> None:
    """Mensagem quando C++ Build Tools / pyroaring / pyiceberg falham."""
    print()
    warn("pyroaring/pyiceberg exigem Microsoft Visual C++ Build Tools para compilar.")
    print("  Baixe em: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
    print("  Alternativa: use requirements-core.txt (sem ChromaDB) ou Python 3.11/3.12.")


def _install_requirements_core() -> bool:
    """Instala requirements-core.txt no ambiente atual (sem recriar venv)."""
    if not REQUIREMENTS_CORE.exists():
        return False
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_CORE), "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, Exception):
        return False


def _is_unstable_error(stderr: str, stdout: str) -> bool:
    """Detecta erros de compilacao ou Python incompativel."""
    combined = (stderr or "") + (stdout or "")
    lower = combined.lower()
    return any(
        x in lower
        for x in [
            "microsoft visual c++",
            "c++ build tools",
            "pyroaring",
            "pyiceberg",
            "error: failed building wheel",
            "python 3.14",
            "incompatible with python",
        ]
    )


def step1_venv() -> bool:
    """Verifica ambiente virtual. Oferece criacao automatica."""
    section("1. Ambiente Virtual")
    if _in_venv():
        ok("Rodando dentro de venv")
        return True

    warn("Nao esta em ambiente virtual (Python global)")
    print("\n  Rodar no Python global pode afetar outros projetos.")
    print("  Deseja criar um ambiente isolado (.venv) agora?")
    try:
        r = input("\n  Criar .venv automaticamente? [S/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        r = "n"

    if r in ("n", "nao", "no"):
        try:
            cont = input("  Continuar no Python global? [s/N]: ").strip().lower()
            return cont in ("s", "sim", "y", "yes")
        except (EOFError, KeyboardInterrupt):
            return False

    # Criar venv
    ok("Criando .venv...")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(VENV_DIR)],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
        )
        ok(".venv criado")
    except subprocess.CalledProcessError as e:
        err(f"Falha ao criar venv: {e}")
        return False
    except Exception as e:
        err(str(e))
        return False

    # Instalar deps dentro do venv
    venv_py = _venv_python()
    if not venv_py:
        err("Python do venv nao encontrado")
        return False

    ok("Instalando dependencias no .venv...")
    try:
        r = subprocess.run(
            [str(venv_py), "-m", "pip", "install", "-r", str(REQUIREMENTS), "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if r.returncode != 0:
            err(r.stderr or r.stdout or "pip falhou")
        else:
            ok("Dependencias instaladas no .venv")
    except subprocess.TimeoutExpired:
        err("Timeout - pip demorou demais")
    except Exception as e:
        err(str(e))

    # Garantir .env com comentario
    if not ENV_PATH.exists():
        _create_env_with_comment()

    section("Proximo Passo")
    print()
    print("  " + "=" * 46)
    print("  Ambiente criado!")
    print()
    if sys.platform == "win32":
        print("  Ative com:  .venv\\Scripts\\activate")
    else:
        print("  Ative com:  source .venv/bin/activate")
    print()
    print("  Depois rode:  python run_init.py")
    print("  " + "=" * 46)
    print()
    sys.exit(0)  # Sucesso - usuario deve ativar e rodar novamente


def step2_install_deps() -> bool:
    """Instala dependencias via pip (sem importar nada externo)."""
    section("2. Dependencias")
    if not REQUIREMENTS.exists():
        err(f"requirements.txt nao encontrado em {PROJECT_ROOT}")
        return False

    _check_python_314_warning()

    # Primeiro: pip freeze vs requirements.txt - se bater, pula instalacao
    if _requirements_already_satisfied():
        ok("Dependencias ja satisfeitas (pip freeze == requirements.txt) - pulando instalacao")
        return True

    ok("Instalando dependencias (pip install -r requirements.txt)...")
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS), "-q"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if r.returncode != 0:
            err(r.stderr or r.stdout or "pip falhou")
            if _is_unstable_error(r.stderr or "", r.stdout or ""):
                _print_cpp_fallback_help()
                print("\n  Opcoes:")
                print("  1. Recriar .venv com requirements-core.txt (sem ChromaDB) [Y]")
                print("  2. Instalar requirements-core.txt no ambiente atual [c]")
                print("  3. Sair e instalar C++ Build Tools manualmente [n]")
                try:
                    r_choice = input("\n  Escolha [Y/c/n]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    r_choice = "n"
                if r_choice in ("", "y", "s", "sim", "yes"):
                    if _hard_reset_venv(force=False):
                        print("\n  Ambiente recriado. Ative o .venv e rode: python run_init.py")
                        sys.exit(0)
                elif r_choice == "c":
                    if _install_requirements_core():
                        ok("requirements-core instalado - ChromaDB desabilitado")
                        return True
            return False
        ok("Dependencias instaladas")
        _save_requirements_hash()
        return True
    except subprocess.TimeoutExpired:
        err("Timeout - pip demorou demais")
        return False
    except Exception as e:
        err(str(e))
        return False


def step3_groq_key() -> bool:
    """Valida GROQ_API_KEY. Pede e salva se faltar."""
    section("3. Configuracao Groq")

    # Cria .env com comentario amigavel se nao existir
    if not ENV_PATH.exists():
        if ENV_EXAMPLE.exists():
            content = ENV_EXAMPLE.read_text(encoding="utf-8")
            if "# Adicione sua GROQ_API_KEY" not in content:
                content = "# Adicione sua GROQ_API_KEY abaixo (console.groq.com)\n\n" + content
            ENV_PATH.write_text(content, encoding="utf-8")
        else:
            _create_env_with_comment()

    env = _parse_env(ENV_PATH)

    key = env.get("GROQ_API_KEY", "").strip()
    if key and key.startswith("gsk_"):
        ok("GROQ_API_KEY configurada")
        os.environ["GROQ_API_KEY"] = key
        return True

    if key:
        warn("GROQ_API_KEY parece invalida (deve comecar com gsk_)")

    print("\n  Obtenha sua chave em: https://console.groq.com")
    print("  Cole a GROQ_API_KEY abaixo (ou Enter para pular):")
    try:
        pasted = input("  > ").strip()
    except (EOFError, KeyboardInterrupt):
        pasted = ""

    if pasted and pasted.startswith("gsk_"):
        _save_env_key("GROQ_API_KEY", pasted)
        os.environ["GROQ_API_KEY"] = pasted
        ok("Chave salva em .env")
        return True

    if not pasted:
        warn("Pulando - configure GROQ_API_KEY no .env depois")
        return True
    warn("Chave invalida - configure manualmente no .env")
    return False


def step4_setup_folders() -> bool:
    """Executa setup_project.py."""
    section("4. Estrutura de Pastas")
    try:
        import setup_project  # noqa: F401
        setup_project.create_folder_structure()
        ok("Pastas criadas")
        return True
    except Exception as e:
        err(str(e))
        return False


def step5_chromadb() -> bool:
    """Warm-up ChromaDB."""
    section("5. ChromaDB")
    try:
        from src.utils.vector_db import count, add_chunks
    except ImportError as e:
        err(f"Import: {e}")
        if "pyroaring" in str(e).lower() or "chromadb" in str(e).lower():
            warn("ChromaDB/pyroaring falhou (C++ Build Tools no Windows).")
            print("  Tente: pip install chromadb --no-build-isolation")
            print("  Ou use Python 3.11/3.12 para melhor compatibilidade.")
            if _hard_reset_venv(force=False):
                print("\n  Ambiente recriado. Ative o .venv e rode: python run_init.py")
                sys.exit(0)
        return False

    chunks_dir = PROJECT_ROOT / "data" / "chunks"
    try:
        n = count()
        if n > 0:
            ok(f"ChromaDB: {n} chunks")
            return True
    except Exception as e:
        warn(str(e))
        if "pyroaring" in str(e).lower():
            print("  Contorno: pip install chromadb --no-build-isolation")

    if not chunks_dir.exists():
        warn("data/chunks vazia - execute o pipeline no dashboard")
        return True

    json_files = list(chunks_dir.glob("*.json"))
    if not json_files:
        warn("Nenhum JSON em data/chunks")
        return True

    ok(f"Migrando {len(json_files)} JSON(s)...")
    total = 0
    for jf in json_files:
        try:
            raw = jf.read_text(encoding="utf-8", errors="replace")
            data = json.loads(raw)
            chunks = list(data) if isinstance(data, list) else [dict(data)]
            # Normaliza chunks para compatibilidade Python 3.14 / ChromaDB / Pydantic
            normalized = []
            for c in chunks:
                if not isinstance(c, dict):
                    continue
                norm = {}
                for k, v in c.items():
                    k = str(k)
                    if v is None:
                        norm[k] = ""
                    elif isinstance(v, (str, int, float, bool)):
                        norm[k] = v
                    else:
                        norm[k] = str(v)
                normalized.append(norm)
            total += add_chunks(normalized)
        except json.JSONDecodeError as e:
            err(f"{jf.name}: JSON invalido - {e}")
        except Exception as e:
            err(f"{jf.name}: {e}")
    ok(f"{total} chunks no ChromaDB")
    return True


def step6_test_groq() -> bool:
    """Testa se Groq responde."""
    section("6. Teste Groq API")
    if not os.getenv("GROQ_API_KEY"):
        env = _parse_env(ENV_PATH)
        if env.get("GROQ_API_KEY"):
            os.environ["GROQ_API_KEY"] = env["GROQ_API_KEY"]
    if not os.getenv("GROQ_API_KEY"):
        warn("GROQ_API_KEY nao configurada - pule esta etapa")
        return True
    try:
        from groq import Groq
        client = Groq()
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Diga apenas: OK"}],
            max_tokens=5,
        )
        ok("Groq respondendo")
        return True
    except Exception as e:
        err(str(e))
        return False


def main() -> int:
    hard_reset = "--hard-reset" in sys.argv

    print("\n" + "=" * 50)
    print("  CHUNK GENERATOR - Self-Bootstrap")
    print("  Lab Intelligence | Configuracao do Zero")
    print("=" * 50)

    _check_python_314_warning()

    if hard_reset:
        if _hard_reset_venv(force=True):
            print("\n  " + "=" * 46)
            print("  Ambiente recriado com sucesso!")
            if sys.platform == "win32":
                print("  Ative com:  .venv\\Scripts\\activate")
            else:
                print("  Ative com:  source .venv/bin/activate")
            print("  Depois rode:  python run_init.py")
            print("  " + "=" * 46)
            return 0
        return 1

    if _requirements_hash_changed():
        warn("requirements.txt mudou desde a ultima execucao.")
        print("  Deseja recriar o .venv para garantir dependencias atualizadas? [y/N]: ", end="")
        try:
            r = input().strip().lower()
            if r in ("s", "sim", "y", "yes"):
                if _hard_reset_venv(force=True):
                    print("\n  Ative o .venv e rode: python run_init.py")
                    return 0
        except (EOFError, KeyboardInterrupt):
            pass

    steps = [
        ("Venv", step1_venv),
        ("Dependencias", step2_install_deps),
        ("Groq", step3_groq_key),
        ("Pastas", step4_setup_folders),
        ("ChromaDB", step5_chromadb),
        ("Groq API", step6_test_groq),
    ]

    results = []
    for name, fn in steps:
        try:
            results.append((name, fn()))
        except Exception as e:
            err(f"Excecao: {e}")
            results.append((name, False))

    section("Resumo")
    all_ok = all(r[1] for r in results)
    for name, status in results:
        if status:
            ok(f"{name}")
        else:
            err(f"{name}")

    if not all_ok:
        print("\n  Corrija os itens acima e execute novamente: python run_init.py")
        return 1

    print("\n" + "-" * 50)
    try:
        resp = input("  Iniciar dashboard? [S/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        resp = "n"

    if resp in ("", "s", "sim", "y", "yes"):
        section("Streamlit")
        ok("Abra http://localhost:8501 no navegador")
        print()
        try:
            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", "dashboard.py"],
                cwd=PROJECT_ROOT,
            )
        except KeyboardInterrupt:
            print("\n  Encerrado.")
    else:
        print("\n  Para iniciar: streamlit run dashboard.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
