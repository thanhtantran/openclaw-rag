# index.py
# Read chunks.json → Create embeddings via OpenAI → Store in ChromaDB

import os
import json
import time
import argparse
import chromadb
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
CHUNKS_FILE      = "chunks/chunks.json"
CHROMA_DIR       = "chroma_db"
COLLECTION_NAME  = "website_knowledge"
EMBED_MODEL      = "text-embedding-3-small"
BATCH_SIZE       = 100   # số chunks gửi OpenAI mỗi lần (max 2048)
SLEEP_BETWEEN    = 0.5   # giây, tránh rate limit

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_chunks(filepath: str) -> list[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"[index] Loaded {len(chunks)} chunks from {filepath}")
    return chunks


def get_existing_ids(collection) -> set[str]:
    """Lấy tất cả chunk_id đã có trong ChromaDB để skip khi re-index."""
    result = collection.get(include=[])
    return set(result["ids"])


def batch(lst: list, size: int):
    """Yield successive batches from list."""
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Call OpenAI embedding API for a batch of texts."""
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    # Sort by index to ensure order
    vectors = sorted(response.data, key=lambda x: x.index)
    return [v.embedding for v in vectors]


# ── Core ──────────────────────────────────────────────────────────────────────

def index_chunks(api_key: str, force: bool = False):
    # ── Load chunks ──
    if not os.path.exists(CHUNKS_FILE):
        print(f"[error] File not found: {CHUNKS_FILE}")
        print("        Run chunk.py first.")
        exit(1)

    all_chunks = load_chunks(CHUNKS_FILE)

    # ── Init ChromaDB ──
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},  # cosine similarity
    )
    print(f"[index] ChromaDB collection: '{COLLECTION_NAME}' at ./{CHROMA_DIR}/")

    # ── Skip already indexed chunks ──
    if force:
        existing_ids = set()
        print("[index] Force mode: re-indexing all chunks")
    else:
        existing_ids = get_existing_ids(collection)
        print(f"[index] Already indexed: {len(existing_ids)} chunks")

    new_chunks = [c for c in all_chunks if c["chunk_id"] not in existing_ids]

    if not new_chunks:
        print("[index] Nothing new to index. All chunks already exist.")
        print("[index] Use --force to re-index everything.")
        return

    print(f"[index] New chunks to index: {len(new_chunks)}\n")

    # ── Init OpenAI ──
    openai_client = OpenAI(api_key=api_key)

    # ── Process in batches ──
    total_indexed = 0

    for i, chunk_batch in enumerate(batch(new_chunks, BATCH_SIZE)):
        batch_num = i + 1
        total_batches = (len(new_chunks) + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"  [batch {batch_num}/{total_batches}] Embedding {len(chunk_batch)} chunks...", end=" ")

        texts = [c["text"] for c in chunk_batch]

        try:
            vectors = embed_texts(openai_client, texts)
        except Exception as e:
            print(f"\n  [error] Embedding failed: {e}")
            print("  Retrying after 5s...")
            time.sleep(5)
            vectors = embed_texts(openai_client, texts)

        # ── Prepare data for ChromaDB ──
        ids        = [c["chunk_id"]   for c in chunk_batch]
        documents  = [c["text"]       for c in chunk_batch]
        metadatas  = [
            {
                "source"      : c["source"],
                "url"         : c["url"],
                "title"       : c["title"],
                "chunk_index" : c["chunk_index"],
                "total_chunks": c["total_chunks"],
                "char_count"  : c["char_count"],
            }
            for c in chunk_batch
        ]

        # ── Upsert vào ChromaDB ──
        collection.upsert(
            ids        = ids,
            embeddings = vectors,
            documents  = documents,
            metadatas  = metadatas,
        )

        total_indexed += len(chunk_batch)
        print(f"done ✓  (total: {total_indexed}/{len(new_chunks)})")

        if i < total_batches - 1:
            time.sleep(SLEEP_BETWEEN)

    print(f"\n[index] Indexing complete!")
    print(f"[index] Total indexed this run : {total_indexed}")
    print(f"[index] Total in collection    : {collection.count()}")
    print(f"[index] ChromaDB saved at      : ./{CHROMA_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed chunks and store in ChromaDB")
    parser.add_argument(
        "--api-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-index all chunks even if already exist",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("[error] OpenAI API key is required.")
        print("        Set env: export OPENAI_API_KEY=your_key")
        print("        Or pass:  --api-key your_key")
        exit(1)

    index_chunks(args.api_key, args.force)
