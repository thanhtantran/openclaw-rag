# index.py
# Load chunks.json → Embed → Upsert vào ChromaDB

import os
import json
import time
import argparse
import chromadb

from dotenv import load_dotenv
load_dotenv()

import config
config.validate()

# ── Config ────────────────────────────────────────────────────────────────────
CHUNKS_FILE     = "chunks/chunks.json"
BATCH_SIZE      = 100    # số chunks gửi mỗi batch
SLEEP_BETWEEN   = 0.5    # giây chờ giữa các batch (tránh rate limit)

# ── Embedding ─────────────────────────────────────────────────────────────────

def load_embed_model():
    """Load local sentence-transformers model (chỉ gọi 1 lần)."""
    from sentence_transformers import SentenceTransformer
    print(f"[index] Loading local model: {config.EMBED_MODEL_LOCAL} ...")
    model = SentenceTransformer(config.EMBED_MODEL_LOCAL)
    print(f"[index] Local model loaded.")
    return model


def embed_texts(texts: list[str], api_key: str = "", local_model=None) -> list[list[float]]:
    """Embed danh sách texts theo provider đã chọn trong config."""

    if config.EMBED_PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.embeddings.create(
            model=config.EMBED_MODEL_OPENAI,
            input=texts,
        )
        vectors = sorted(response.data, key=lambda x: x.index)
        return [v.embedding for v in vectors]

    elif config.EMBED_PROVIDER == "local":
        vectors = local_model.encode(texts, show_progress_bar=False)
        return vectors.tolist()


# ── Core ──────────────────────────────────────────────────────────────────────

def index(api_key: str = "", force: bool = False):

    # ── Load chunks ──
    if not os.path.exists(CHUNKS_FILE):
        print(f"[error] File not found: {CHUNKS_FILE}")
        print("        Run chunk.py first.")
        exit(1)

    with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"[index] Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    # ── Init ChromaDB ──
    chroma_client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    collection    = chroma_client.get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # ── Filter chunks chưa index (nếu không force) ──
    if not force:
        existing_ids = set(collection.get(include=[])["ids"])
        chunks = [c for c in chunks if c["id"] not in existing_ids]
        print(f"[index] {len(chunks)} new chunks to index (skipping existing)")
    else:
        print(f"[index] Force mode: re-indexing all {len(chunks)} chunks")

    if not chunks:
        print("[index] Nothing to index. Done.")
        return

    # ── Load local model 1 lần nếu dùng local ──
    local_model = None
    if config.EMBED_PROVIDER == "local":
        local_model = load_embed_model()

    # ── Batch embed & upsert ──
    total   = len(chunks)
    indexed = 0

    for i in range(0, total, BATCH_SIZE):
        batch  = chunks[i : i + BATCH_SIZE]
        texts  = [c["text"] for c in batch]
        ids    = [c["id"]   for c in batch]
        metas  = [c["metadata"] for c in batch]

        # Embed
        vectors = embed_texts(texts, api_key=api_key, local_model=local_model)

        # Upsert vào ChromaDB
        collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=texts,
            metadatas=metas,
        )

        indexed += len(batch)
        print(f"[index] {indexed}/{total} chunks indexed...")

        # Tránh rate limit khi dùng OpenAI
        if config.EMBED_PROVIDER == "openai" and i + BATCH_SIZE < total:
            time.sleep(SLEEP_BETWEEN)

    print(f"\n[index] ✓ Done! {indexed} chunks indexed into '{config.COLLECTION_NAME}'")
    print(f"[index] ✓ ChromaDB saved at: ./{config.CHROMA_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index chunks into ChromaDB")
    parser.add_argument(
        "--openai-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key (required if EMBED_PROVIDER=openai)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all chunks, including already indexed ones",
    )
    args = parser.parse_args()

    # Validate API key nếu dùng OpenAI embedding
    if config.EMBED_PROVIDER == "openai" and not args.openai_key:
        print("[error] OpenAI API key is required when EMBED_PROVIDER=openai")
        print("        Set env: export OPENAI_API_KEY=your_key")
        print("        Or pass:  --openai-key your_key")
        exit(1)

    index(api_key=args.openai_key, force=args.force)
