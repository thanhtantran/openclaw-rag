# config.py
# Cấu hình trung tâm cho toàn bộ hệ thống RAG
# Chỉnh sửa file này để thay đổi provider/model

# ══════════════════════════════════════════════════════════════════
#  EMBEDDING CONFIG
#  Chọn 1 trong 2: "openai" hoặc "local"
# ══════════════════════════════════════════════════════════════════

# EMBED_PROVIDER = "openai"
EMBED_PROVIDER = "local"

# OpenAI embedding model
EMBED_MODEL_OPENAI = "text-embedding-3-small"

# Local embedding model (sentence-transformers, chạy offline, miễn phí)
# Các model phổ biến:
#   "all-MiniLM-L6-v2"        → Nhẹ, nhanh, tiếng Anh tốt
#   "paraphrase-multilingual-MiniLM-L12-v2" → Hỗ trợ đa ngôn ngữ (tiếng Việt)
#   "all-mpnet-base-v2"       → Chất lượng cao hơn, nặng hơn
EMBED_MODEL_LOCAL = "paraphrase-multilingual-MiniLM-L12-v2"


# ══════════════════════════════════════════════════════════════════
#  LLM CONFIG
#  Chọn 1 trong 3: "openai" | "deepseek" | "anthropic"
# ══════════════════════════════════════════════════════════════════

# LLM_PROVIDER = "openai"
LLM_PROVIDER = "deepseek"
# LLM_PROVIDER = "anthropic"

# Model tương ứng theo provider
LLM_MODELS = {
    "openai"   : "gpt-4o-mini",
    "deepseek" : "deepseek-chat",
    "anthropic": "claude-3-5-haiku-20241022",
}

LLM_MODEL = LLM_MODELS[LLM_PROVIDER]


# ══════════════════════════════════════════════════════════════════
#  CHROMADB CONFIG
# ══════════════════════════════════════════════════════════════════

CHROMA_DIR      = "chroma_db"
COLLECTION_NAME = "website_knowledge"
CHUNKS_FILE = "chunks/chunks.json"
INDEX_FILE = "index/index.json"


# ══════════════════════════════════════════════════════════════════
#  CHUNK CONFIG
# ══════════════════════════════════════════════════════════════════

CHUNK_SIZE = 1000   # Số ký tự mỗi chunk
OVERLAP    = 150    # Số ký tự overlap giữa các chunk

# ══════════════════════════════════════════════════════════════════
#  EMBEDED CONFIG
# ══════════════════════════════════════════════════════════════════
EMBED_TYPE = "local"  # "local" or "openai"
EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # SentenceTransformers model
EMBED_BATCH_SIZE = 32


# ══════════════════════════════════════════════════════════════════
#  QUERY CONFIG
# ══════════════════════════════════════════════════════════════════

TOP_K      = 5      # Số chunks retrieve từ vector search
MAX_TOKENS = 1024   # Max tokens cho LLM response


# ══════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Bạn là trợ lý AI hữu ích, trả lời câu hỏi dựa hoàn toàn vào nội dung context được cung cấp.

Quy tắc:
- Chỉ trả lời dựa trên context bên dưới, không suy đoán thêm.
- Nếu câu trả lời không có trong context, hãy nói: "Tôi không có thông tin về vấn đề này."
- Trả lời ngắn gọn, rõ ràng và đầy đủ.
- Nếu liên quan, hãy đề cập URL nguồn.
- Trả lời bằng ngôn ngữ mà người dùng đang sử dụng.
"""


# ══════════════════════════════════════════════════════════════════
#  VALIDATION
# ══════════════════════════════════════════════════════════════════

def validate():
    """Kiểm tra config hợp lệ khi khởi động."""
    valid_embed    = ("openai", "local")
    valid_llm      = ("openai", "deepseek", "anthropic")

    if EMBED_PROVIDER not in valid_embed:
        raise ValueError(f"[config] EMBED_PROVIDER phải là một trong: {valid_embed}")

    if LLM_PROVIDER not in valid_llm:
        raise ValueError(f"[config] LLM_PROVIDER phải là một trong: {valid_llm}")

    print(f"[config] Embedding : {EMBED_PROVIDER} / "
          f"{EMBED_MODEL_OPENAI if EMBED_PROVIDER == 'openai' else EMBED_MODEL_LOCAL}")
    print(f"[config] LLM       : {LLM_PROVIDER} / {LLM_MODEL}")
