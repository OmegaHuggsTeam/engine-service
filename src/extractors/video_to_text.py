"""
Extrator de transcrição de vídeos MP4.
Usa Groq API (whisper-large-v3) para transcrição ultra-rápida.
FFmpeg comprime para mp3 mono 32kbps antes do upload (< 25MB).
"""

import subprocess
import tempfile
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic_core")

# Diretórios do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Groq: whisper-large-v3 (API)
WHISPER_MODEL = "whisper-large-v3"


def _compress_audio_ffmpeg(input_path: Path, output_path: Path) -> Path:
    """
    Comprime áudio para mp3 mono 32kbps (upload rápido, < 25MB Groq).
    Requer FFmpeg no PATH.
    """
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", "16000", "-ac", "1",
        "-b:a", "32k",
        "-map", "0:a",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr or result.stdout or "FFmpeg falhou"
        if "ffmpeg" in err.lower() or "WinError 2" in str(result):
            raise RuntimeError(
                "FFmpeg não encontrado. Instale e adicione ao PATH do Windows:\n"
                "1) Baixe em https://ffmpeg.org/download.html\n"
                "2) Extraia e adicione a pasta 'bin' ao PATH."
            ) from None
        raise RuntimeError(f"FFmpeg: {err[:200]}")
    return output_path


def extract_audio_from_video(video_path: Path, output_path: Path) -> Path:
    """
    Extrai apenas o áudio de um arquivo MP4 usando moviepy.
    
    Args:
        video_path: Caminho do vídeo
        output_path: Caminho para salvar o áudio (mp3)
    
    Returns:
        Caminho do arquivo de áudio gerado
    """
    from moviepy import VideoFileClip

    try:
        with VideoFileClip(str(video_path)) as video:
            video.audio.write_audiofile(str(output_path))
    except (FileNotFoundError, OSError) as e:
        err_msg = str(e)
        if "FFmpeg" in err_msg or "ffmpeg" in err_msg or "WinError 2" in err_msg or getattr(e, "winerror", None) == 2:
            raise RuntimeError(
                "FFmpeg não encontrado. Instale o FFmpeg e adicione ao PATH do Windows:\n"
                "1) Baixe em https://ffmpeg.org/download.html (ou https://www.gyan.dev/ffmpeg/builds/)\n"
                "2) Extraia e adicione a pasta 'bin' ao PATH do sistema (Configurações > Sistema > Variáveis de ambiente)."
            ) from e
        raise

    return output_path


def transcribe_audio(audio_path: Path, model_name: str = WHISPER_MODEL) -> str:
    """
    Transcreve áudio via Groq API (whisper-large-v3).
    Ultra-rápido, usa KeyManager para rotação de chaves.
    """
    from src.utils.llm_client import transcribe_audio_groq

    t0 = time.perf_counter()
    text = transcribe_audio_groq(audio_path, model=model_name, language="pt")
    elapsed = time.perf_counter() - t0
    print(f"[TIMER] Transcrição concluída em {elapsed:.1f}s")
    return text


def process_video(
    video_path: Path,
    output_dir: Path = PROCESSED_DIR,
    model_name: str = WHISPER_MODEL,
    keep_audio: bool = False,
    raw_dir: Path = RAW_DIR,
    progress_callback=None,
) -> Path:
    """
    Processa um vídeo MP4: extrai áudio, transcreve e salva em .txt.
    Preserva a estrutura de subpastas (ex: IA_Basica/aula_01.mp4 -> processed/IA_Basica/aula_01.txt).

    Args:
        video_path: Caminho do vídeo
        output_dir: Pasta base para salvar transcrições
        model_name: Modelo Whisper
        keep_audio: Se True, mantém o arquivo de áudio extraído
        raw_dir: Pasta base raw (para calcular subpath relativo)

    Returns:
        Caminho do arquivo .txt gerado
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

    if video_path.suffix.lower() != ".mp4":
        raise ValueError(f"Esperado arquivo .mp4, recebido: {video_path.suffix}")

    try:
        rel = video_path.parent.relative_to(raw_dir)
        subpath = rel / video_path.stem
    except ValueError:
        subpath = Path(video_path.stem)

    output_dir = Path(output_dir) / subpath.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    output_txt = output_dir / f"{video_path.stem}.txt"
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        audio_path = Path(tmp.name)

    print("Verificando FFmpeg no sistema...")
    try:
        print(f"Processando {video_path.name}...")

        if progress_callback:
            progress_callback(1, 4, "Step 1/4: Extraindo Áudio (MoviePy)...")
        print("  -> Extraindo áudio...")
        extract_audio_from_video(video_path, audio_path)

        compressed_path = audio_path.with_suffix(".compressed.mp3")
        if progress_callback:
            progress_callback(2, 4, "Step 2/4: Comprimindo (FFmpeg 32kbps mono)...")
        print("  -> Comprimindo para mp3 32kbps mono (upload rápido)...")
        _compress_audio_ffmpeg(audio_path, compressed_path)
        if not keep_audio and audio_path.exists():
            audio_path.unlink()
        audio_path = compressed_path

        if progress_callback:
            progress_callback(2, 4, "Step 2/4: Transcrevendo (Groq whisper-large-v3)...")
        print("  -> Transcrevendo via Groq API (whisper-large-v3)...")
        text = transcribe_audio(audio_path, model_name)
        
        output_txt.write_text(text, encoding="utf-8")
        print(f"  -> [OK] Transcrição salva em: {output_txt}")
        
        if keep_audio:
            final_audio = output_dir / f"{video_path.stem}.mp3"
            audio_path.rename(final_audio)
            print(f"  -> Áudio salvo em: {final_audio}")
        
        return output_txt
    except (FileNotFoundError, OSError, RuntimeError) as e:
        if "FFmpeg" in str(e):
            raise
        raise RuntimeError(str(e)) from e
    finally:
        if not keep_audio and audio_path.exists():
            try:
                audio_path.unlink()
            except OSError:
                pass


def main():
    """Processa todos os arquivos .mp4 em data/raw (busca recursiva)."""
    if not RAW_DIR.exists():
        print(f"Pasta {RAW_DIR} não existe. Execute setup_project.py primeiro.")
        return

    mp4_files = sorted(RAW_DIR.rglob("*.mp4"))

    if not mp4_files:
        print(f"Nenhum arquivo .mp4 encontrado em {RAW_DIR}")
        print("Adicione vídeos na pasta data/raw para processar.")
        return

    print(f"Encontrados {len(mp4_files)} vídeo(s) para processar.\n")

    for video_path in mp4_files:
        try:
            process_video(video_path)
        except Exception as e:
            print(f"  -> [ERRO] {e}")

        print()


if __name__ == "__main__":
    main()
