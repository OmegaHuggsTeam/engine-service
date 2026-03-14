"""
Script de setup inicial do mcp-engine-service.
Cria a estrutura de pastas e arquivos .gitkeep conforme o Blueprint.
"""

from pathlib import Path

# Diretório raiz do projeto
PROJECT_ROOT = Path(__file__).parent.resolve()

# Estrutura de pastas conforme Blueprint
FOLDER_STRUCTURE = [
    "data/raw",  # Arquivos brutos (MP4, PDF, TXT)
    "data/processed",  # Transcrições e textos limpos
    "data/chunks",  # Arquivos JSON/Parquet prontos para o Vector DB
    "db/chroma",  # ChromaDB persistente (Vector Database)
    "src/extractors",  # Scripts para converter PDF e Áudio em Texto
    "src/processors",  # Lógica de limpeza e segmentação (Chunking)
    "src/utils",  # Helpers para conexão com APIs (OpenAI Whisper, LangChain)
]


def create_folder_structure():
    """Cria todas as pastas e adiciona .gitkeep para versionamento."""
    for folder in FOLDER_STRUCTURE:
        folder_path = PROJECT_ROOT / folder
        folder_path.mkdir(parents=True, exist_ok=True)

        gitkeep_path = folder_path / ".gitkeep"
        gitkeep_path.touch()

        print(f"[OK] Criado: {folder}/")


def main():
    print("Setup do mcp-engine-service - Lab Intelligence\n")
    create_folder_structure()
    print("\n[OK] Estrutura de pastas criada com sucesso!")


if __name__ == "__main__":
    main()
