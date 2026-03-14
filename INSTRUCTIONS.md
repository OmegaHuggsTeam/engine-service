Com certeza. O seu INSTRUCTIONS.md original era um plano de obra; agora, ele precisa ser o Manual de Operação e Expansão do sistema. Como você adicionou o ChromaDB, o Streamlit, a Recursividade e o Sistema Multi-Agente, o Cursor precisa desse contexto atualizado para não sugerir códigos obsoletos (como buscar em JSONs lentos).

Copie e cole este novo conteúdo no seu arquivo C:\labs\inteligence\mcp-engine-service\INSTRUCTIONS.md:

🧠 Master Blueprint: QG de Inteligência Vertical (v2.0)
Você é o Engenheiro Chefe deste ecossistema de RAG (Retrieval-Augmented Generation). Este projeto transforma cursos (Vídeos/PDFs) em uma base de conhecimento semântica consultada por agentes especialistas.

🛠️ Arquitetura do Sistema
O sistema opera em uma esteira de quatro estágios:

Ingestão (Recursive): Monitora data/raw (incluindo subpastas) para novos arquivos MP4, PDF e TXT.

Refino (LLM Clean): Transcrições brutas são limpas pelo gpt-4o-mini para remover vícios de linguagem e formatar em Markdown técnico.

Memória Vetorial (ChromaDB): Chunks de ~1000 tokens com 15% de overlap são indexados no banco vetorial em db/chroma usando text-embedding-3-small.

Interface (Streamlit): Um dashboard centraliza o upload, o processamento em lote e o chat multi-agente.

📁 Estrutura de Diretórios Absoluta
data/raw/**: Origem de mídia (organizada por pastas de cursos).

data/processed/: Transcrições brutas e versões _clean.txt.

data/chunks/: Backups em JSON dos chunks processados.

db/chroma/: Banco de dados vetorial persistente.

src/extractors/: Lógica de conversão de mídia (Whisper/PDF).

src/processors/: Scripts de limpeza semântica e chunking recursivo.

src/utils/: Conectores de banco (ChromaDB) e helpers.

src/agents/: Scripts individuais de personas (Marketing, Social, Analytics, IA).

🤖 Definições de Agentes (DNA)
Sempre que criar ou editar um agente, siga estas diretrizes:

Marketing: Foco em funil, promessa e mecanismos únicos do curso.

Social Media: Foco em repurposing, scripts de reels e threads virais.

Analytics: Foco em benchmarks, cálculo de ROI e diagnóstico de gargalos.

IA Engineer: Foco em automação (Make/n8n) e engenharia de prompts.

🚀 Regras de Ouro para o Cursor
Busca Semântica Obrigatória: Nunca use busca por palavra-chave se o ChromaDB estiver disponível. Use similaridade de cosseno.

Preservação Técnica: No processamento de IA, nunca traduza termos como "Weights", "Bias" ou "Fine-tuning".

Cache Inteligente: Sempre verifique se um arquivo _clean.txt já existe antes de gastar tokens na API da OpenAI.

Feedback Visual: Scripts de longa duração (como o cleaner) devem ter barras de progresso ou logs claros no Dashboard.

🔧 Comandos Globais
Inicializar: python run_init.py

Interface: streamlit run dashboard.py

Limpar Banco: from src.utils.vector_db import clear; clear()
