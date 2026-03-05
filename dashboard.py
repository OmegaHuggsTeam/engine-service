"""
Dashboard Chunk Generator - Lab Intelligence
Interface web para upload, pipeline e chat com agentes.
"""

import os
import warnings
from pathlib import Path

from dotenv import load_dotenv

# Carrega .env antes de qualquer módulo que use variáveis de ambiente
load_dotenv(Path(__file__).parent / ".env")
warnings.filterwarnings("ignore")

import shutil

import streamlit as st

# Paths
PROJECT_ROOT = Path(__file__).parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"

# Garante que as pastas existam
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
CHUNKS_DIR.mkdir(parents=True, exist_ok=True)


def _raw_source_name(file_path: Path) -> str:
    """Retorna source_file (path relativo sem extensão) para um arquivo em data/raw."""
    try:
        rel = file_path.relative_to(RAW_DIR)
        return str(rel.with_suffix("")).replace("\\", "/")
    except ValueError:
        return file_path.stem


def get_file_tree(path):
    """Escaneia diretório recursivamente. Retorna {subpasta: [arquivos]} com try/except fechado."""
    tree = {}
    try:
        for root, dirs, files in os.walk(path):
            valid_files = [f for f in files if f.lower().endswith((".mp4", ".txt", ".pdf"))]
            if valid_files:
                relative_path = os.path.relpath(root, path)
                tree[relative_path] = sorted(valid_files)
        return dict(sorted(tree.items()))
    except Exception as e:
        st.error(f"Erro ao ler diretório: {e}")
        return {}


def _process_single_file(
    file_path: Path,
    agent_specialty: str = "Uncategorized",
    progress_callback=None,
) -> str | None:
    """
    Processa um único arquivo (MP4 ou TXT).
    progress_callback(step, total, message) opcional para UI (Streamlit).
    """
    if not file_path.exists():
        return "Arquivo não encontrado"

    def _progress(step: int, total: int, msg: str):
        if progress_callback:
            progress_callback(step, total, msg)

    if file_path.suffix.lower() == ".mp4":
        try:
            from src.extractors.video_to_text import process_video
            process_video(file_path, progress_callback=progress_callback)
        except (RuntimeError, FileNotFoundError, OSError) as e:
            err_msg = str(e)
            if "FFmpeg" in err_msg or "ffmpeg" in err_msg.lower():
                return (
                    "**FFmpeg não encontrado.** Instale e adicione ao PATH do Windows:\n\n"
                    "1. Baixe em https://ffmpeg.org/download.html ou https://www.gyan.dev/ffmpeg/builds/\n"
                    "2. Extraia e adicione a pasta `bin` ao PATH (Configurações > Sistema > Variáveis de ambiente)"
                )
            return err_msg
        txt_path = PROCESSED_DIR / file_path.relative_to(RAW_DIR).with_suffix(".txt")
    elif file_path.suffix.lower() == ".txt":
        _progress(1, 4, "Step 1/4: Copiando arquivo para processamento...")
        rel = file_path.relative_to(RAW_DIR)
        dest = PROCESSED_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(file_path, dest)
        txt_path = dest
    else:
        return "Tipo não suportado (use MP4 ou TXT)"

    _progress(3, 4, "Step 3/4: Higienizando Texto (Groq)...")
    from src.processors.cleaner import process_file
    process_file(txt_path)
    clean_path = txt_path.parent / f"{txt_path.stem}_clean.txt"

    _progress(4, 4, "Step 4/4: Indexando na Memória (ChromaDB)...")
    source_name = _raw_source_name(file_path)
    from src.processors.processor import process_txt_file
    process_txt_file(clean_path, source_file=source_name, output_dir=CHUNKS_DIR, agent_specialty=agent_specialty)
    return None


def _refresh_chunk_metrics():
    """Atualiza contador e métricas do ChromaDB (chamado após processamento)."""
    try:
        from src.utils.vector_db import count, get_source_files, get_agent_chunk_counts
        return count(), get_source_files(), get_agent_chunk_counts()
    except Exception:
        return 0, set(), {}


st.set_page_config(
    page_title="Chunk Generator",
    page_icon="📚",
    layout="wide",
)

# Sidebar - Seleção do Agente
st.sidebar.title("Chunk Generator")
st.sidebar.markdown("---")

agent_option = st.sidebar.selectbox(
    "Selecione o Agente",
    ["Marketing", "Social Media", "Analytics", "IA Engineer"],
    index=0,
)

AGENT_MAP = {
    "Marketing": ("marketing_agent", "ask_agent"),
    "Social Media": ("social_media_agent", "ask_agent"),
    "Analytics": ("analytics_agent", "ask_agent"),
    "IA Engineer": ("ai_engineer_agent", "ask_agent"),
}

# Controle de Memória + Filtro por Agente (pastas dominadas)
chunk_count, source_files, agent_counts = _refresh_chunk_metrics()

st.sidebar.metric("Chunks no ChromaDB", chunk_count)
if st.sidebar.button("🔄 Atualizar", help="Recarrega contador após processamento"):
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()
if source_files:
    st.sidebar.caption(f"Conhecimento ativo para **{agent_option}**: {len(source_files)} pasta(s)")
    with st.sidebar.expander("Pastas no banco"):
        for sf in sorted(source_files)[:15]:
            st.caption(f"• {sf}")
        if len(source_files) > 15:
            st.caption(f"... e mais {len(source_files) - 15}")

st.sidebar.markdown("---")
st.sidebar.caption("Groq (llama-3.3-70b) | ChromaDB")

# Tabs principais
tab_upload, tab_biblioteca, tab_pipeline, tab_chat = st.tabs(
    ["Upload", "Biblioteca Local", "Pipeline", "Chat"]
)

# --- TAB UPLOAD ---
with tab_upload:
    st.header("Upload de Arquivos")
    st.markdown("Envie arquivos **MP4** ou **TXT** para a pasta `data/raw`.")

    uploaded = st.file_uploader(
        "Arraste ou selecione arquivos",
        type=["mp4", "txt"],
        accept_multiple_files=True,
    )

    if uploaded:
        for f in uploaded:
            if f.name.lower().endswith((".mp4", ".txt")):
                dest = RAW_DIR / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, "wb") as out:
                    out.write(f.getvalue())
                st.success(f"Salvo: {f.name} em data/raw")
            else:
                st.warning(f"Ignorado (tipo inválido): {f.name}")

# --- TAB BIBLIOTECA LOCAL ---
with tab_biblioteca:
    st.header("📚 Biblioteca Local")
    st.markdown("Arquivos em `data/raw` e status de processamento.")

    col_info, col_refresh = st.columns([1, 1])
    with col_info:
        st.metric("Chunks no ChromaDB", chunk_count)
    with col_refresh:
        if st.button("🔄 Atualizar contador", key="refresh_bib"):
            st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

    # Visão por Agente: tabela e gráfico de barras
    if agent_counts:
        st.subheader("Chunks por Agente")
        rows = [{"Agente": k, "Chunks": v} for k, v in agent_counts.items()]
        col_tbl, col_chart = st.columns(2)
        with col_tbl:
            st.table(rows)
        with col_chart:
            try:
                import pandas as pd
                df = pd.DataFrame(rows)
                st.bar_chart(df.set_index("Agente"))
            except ImportError:
                st.caption("Instale pandas para ver o gráfico de barras.")

    tree = get_file_tree(str(RAW_DIR))
    if not tree:
        st.info("Nenhum arquivo MP4, TXT ou PDF em `data/raw`. Use a aba Upload para adicionar.")
    else:
        for folder, filenames in tree.items():
            folder_label = folder if folder != "." else "(raiz)"
            with st.expander(f"📁 {folder_label}", expanded=True):
                # Botão Processar Pasta (processa todos os arquivos da subpasta)
                folder_path = Path(folder) if folder != "." else Path(".")
                files_to_process = [
                    RAW_DIR / folder_path / name
                    for name in filenames
                    if name.lower().endswith((".mp4", ".txt"))
                ]
                unprocessed = [fp for fp in files_to_process if _raw_source_name(fp) not in source_files]
                if unprocessed and st.button(f"⚡ Processar Pasta", key=f"pasta_{folder.replace(os.sep, '_')}"):
                    progress = st.progress(0)
                    status = st.empty()
                    n = len(unprocessed)
                    status.info(f"Processando {n} arquivo(s) com até 10 workers...")
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    completed = 0
                    with ThreadPoolExecutor(max_workers=min(10, n)) as ex:
                        futures = {ex.submit(_process_single_file, fp, agent_option): fp for fp in unprocessed}
                        for future in as_completed(futures):
                            fp = futures[future]
                            completed += 1
                            try:
                                err = future.result()
                                if err:
                                    st.error(f"{fp.name}: {err}")
                            except Exception as e:
                                st.error(f"{fp.name}: {e}")
                            progress.progress(completed / n)
                            status.info(f"Processando {completed}/{n} arquivos...")
                    progress.empty()
                    st.success("Pasta processada!")
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()

                for name in filenames:
                    if name.lower().endswith(".pdf"):
                        st.caption(f"{name} (PDF: use Pipeline para processar)")
                        continue
                    fp = RAW_DIR / (folder_path / name) if folder != "." else RAW_DIR / name
                    source_name = _raw_source_name(fp)
                    is_processed = source_name in source_files
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.text(name)
                    with col2:
                        if is_processed:
                            st.success("✅ Processado")
                        else:
                            if st.button("⚡ Processar Agora", key=f"proc_{source_name.replace('/', '_').replace('.', '_')}"):
                                progress = st.progress(0)
                                status = st.empty()
                                def _cb(step, total, msg):
                                    progress.progress(step / total if total else 0)
                                    status.info(msg)
                                with st.spinner(f"Processando {name}..."):
                                    err = _process_single_file(fp, agent_specialty=agent_option, progress_callback=_cb)
                                    if err:
                                        status.error(err)
                                        st.error(err)
                                    else:
                                        progress.progress(1.0)
                                        status.success("Concluído!")
                                        st.success("Concluído!")
                                        try:
                                            st.rerun()
                                        except AttributeError:
                                            st.experimental_rerun()

# --- TAB PIPELINE ---
with tab_pipeline:
    st.header("Pipeline de Processamento")
    st.markdown(
        "Executa em sequência: **Transcrição** (MP4) → **Limpeza** (LLM) → **Chunking**"
    )

    if st.button("Processar Tudo", type="primary"):
        progress = st.progress(0)
        status = st.empty()
        errors = []

        try:
            # 1. Transcrição (MP4) - busca recursiva
            from src.extractors.video_to_text import process_video

            mp4_files = list(RAW_DIR.rglob("*.mp4"))
            n_mp4 = max(len(mp4_files), 1)
            for idx, mp4 in enumerate(mp4_files):
                def _pipe_cb(s, t, m, _i=idx):
                    status.info(f"[MP4 {_i+1}/{n_mp4}] {m}" if n_mp4 > 1 else m)
                    progress.progress((_i + s / t) / n_mp4 * 0.33 if t else 0)
                try:
                    status.info(f"Step 1-2/4: Transcrição ({idx+1}/{n_mp4}) - Extraindo e transcrevendo...")
                    process_video(mp4, progress_callback=_pipe_cb)
                except Exception as e:
                    errors.append(f"MP4 {mp4}: {e}")

            # Copiar TXT de raw para processed (preservando subpastas)
            processed_dir = PROJECT_ROOT / "data" / "processed"
            txt_in_raw = list(RAW_DIR.rglob("*.txt"))
            for txt in txt_in_raw:
                try:
                    rel = txt.relative_to(RAW_DIR)
                    dest = processed_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(txt, dest)
                except Exception as e:
                    errors.append(f"Copy {txt}: {e}")

            progress.progress(0.33)

            # 2. Limpeza - paralelo com múltiplas chaves Groq
            status.info("Step 3/4: Higienizando Texto (Groq) - processamento paralelo...")
            from src.processors.cleaner import get_files_to_process, process_files_parallel

            to_clean = get_files_to_process(processed_dir)
            n_clean = len(to_clean)

            def _clean_progress(done, total, fp=None, key_idx=0):
                msg = f"Processando {done}/{total} arquivos com 10 workers (Groq)..."
                if fp and key_idx:
                    msg += f" | Último: {fp.name} → chave {key_idx}"
                status.info(msg)
                progress.progress(0.33 + 0.33 * (done / max(total, 1)))

            if to_clean:
                clean_results = process_files_parallel(
                    to_clean, max_workers=10,
                    progress_callback=_clean_progress,
                )
                for fp, out, err, key_idx in clean_results:
                    if err:
                        errors.append(f"Cleaner {fp.name}: {err}")
                key_table = [{"Arquivo": fp.name, "Chave": f"GROQ_KEY_{key_idx}"} for fp, _, err, key_idx in clean_results if not err]
                if key_table:
                    with st.expander("Chaves usadas por arquivo"):
                        st.table(key_table)

            progress.progress(0.66)

            # 3. Chunking - busca recursiva, source_file com subpath
            status.info("Step 4/4: Indexando na Memória (ChromaDB)...")
            from src.processors.processor import process_txt_file

            clean_files = list(processed_dir.rglob("*_clean.txt"))
            for cf in clean_files:
                try:
                    rel = cf.relative_to(processed_dir)
                    source_name = str(rel.with_suffix("")).replace("_clean", "").replace("\\", "/")
                    process_txt_file(cf, source_file=source_name, output_dir=CHUNKS_DIR, agent_specialty=agent_option)
                except Exception as e:
                    errors.append(f"Chunking {cf.name}: {e}")

            progress.progress(1.0)
            status.success("Pipeline concluído! Clique em 🔄 Atualizar na sidebar para ver o novo total.")

            if errors:
                st.warning("Alguns erros ocorreram:")
                ffmpeg_errors = [e for e in errors if "FFmpeg" in e or "ffmpeg" in e.lower()]
                if ffmpeg_errors:
                    st.error(
                        "**FFmpeg não encontrado.** Instale e adicione ao PATH do Windows:\n\n"
                        "1. Baixe em https://ffmpeg.org/download.html ou https://www.gyan.dev/ffmpeg/builds/\n"
                        "2. Extraia e adicione a pasta `bin` ao PATH (Configurações > Sistema > Variáveis de ambiente)"
                    )
                for e in errors:
                    st.code(e)

        except Exception as e:
            status.error(str(e))
            st.exception(e)

# --- TAB CHAT ---
with tab_chat:
    st.header(f"Chat com Agente: {agent_option}")

    # Inicializa histórico no session_state (mantém últimas 5 mensagens)
    MAX_HISTORY = 5
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Carrega chunks
    @st.cache_resource
    def get_chunks():
        from src.agents.marketing_agent import load_chunks
        return load_chunks()

    chunks = get_chunks()

    if not chunks:
        st.warning(
            "Nenhum chunk encontrado. Execute o pipeline na aba 'Pipeline' primeiro."
        )
    else:
        st.caption(f"{len(chunks)} chunks carregados")

        # Exibe histórico
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input do usuário
        if prompt := st.chat_input("Digite sua pergunta..."):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            # Histórico das últimas 5 mensagens (excluindo a atual) para contexto
            chat_history = st.session_state.messages[:-1][-MAX_HISTORY:]

            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    try:
                        module_name, func_name = AGENT_MAP[agent_option]
                        mod = __import__(
                            f"src.agents.{module_name}",
                            fromlist=[func_name],
                        )
                        ask_fn = getattr(mod, func_name)
                        response = ask_fn(chunks, prompt, chat_history=chat_history)
                        st.markdown(response)
                    except Exception as e:
                        st.error(str(e))
                        response = f"Erro: {e}"

            st.session_state.messages.append(
                {"role": "assistant", "content": response}
            )
            # Mantém apenas as últimas 5 mensagens
            st.session_state.messages = st.session_state.messages[-MAX_HISTORY:]
