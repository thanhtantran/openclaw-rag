# query.py
# Embed user question → Vector search ChromaDB → Send context to LLM → Answer

import os
import argparse
import chromadb

from dotenv import load_dotenv
load_dotenv()

import config
config.validate()

# ── Embedding ─────────────────────────────────────────────────────────────────

_local_embed_model = None  # cache model, chỉ load 1 lần

def get_local_embed_model():
    """Load và cache local embedding model."""
    global _local_embed_model
    if _local_embed_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"[query] Loading local model: {config.EMBED_MODEL_LOCAL} ...")
        _local_embed_model = SentenceTransformer(config.EMBED_MODEL_LOCAL)
        print(f"[query] Local model loaded.")
    return _local_embed_model


def embed_question(question: str, openai_api_key: str = "") -> list[float]:
    """Embed câu hỏi theo provider đã chọn trong config."""

    if config.EMBED_PROVIDER == "openai":
        from openai import OpenAI
        client = OpenAI(api_key=openai_api_key)
        response = client.embeddings.create(
            model=config.EMBED_MODEL_OPENAI,
            input=[question],
        )
        return response.data[0].embedding

    elif config.EMBED_PROVIDER == "local":
        model  = get_local_embed_model()
        vector = model.encode([question])
        return vector[0].tolist()


# ── LLM Client ────────────────────────────────────────────────────────────────

def init_llm_client(llm_api_key: str):
    """Khởi tạo LLM client theo provider đã chọn trong config."""

    if config.LLM_PROVIDER == "openai":
        from openai import OpenAI
        return OpenAI(api_key=llm_api_key)

    elif config.LLM_PROVIDER == "deepseek":
        from openai import OpenAI
        return OpenAI(
            api_key=llm_api_key,
            base_url="https://api.deepseek.com",
        )

    elif config.LLM_PROVIDER == "anthropic":
        try:
            import anthropic
        except ImportError:
            print("[error] Anthropic SDK not installed.")
            print("        Run: pip install anthropic")
            exit(1)
        return anthropic.Anthropic(api_key=llm_api_key)


# ── Helpers ───────────────────────────────────────────────────────────────────

def search_chunks(collection, vector: list[float]) -> list[dict]:
    """Query ChromaDB cho top K chunks liên quan nhất."""
    results = collection.query(
        query_embeddings=[vector],
        n_results=config.TOP_K,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id"      : results["ids"][0][i],
            "text"    : results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score"   : 1 - results["distances"][0][i],
        })
    return chunks


def build_context(chunks: list[dict]) -> str:
    """Format chunks thành context string cho LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        url    = chunk["metadata"].get("url", "")
        title  = chunk["metadata"].get("title", "")
        header = f"[Source {i}]"
        if title:
            header += f" {title}"
        if url:
            header += f" ({url})"
        parts.append(f"{header}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def ask_llm(llm_client, question: str, context: str) -> str:
    """Gửi question + context tới LLM và nhận câu trả lời."""
    user_message = f"""Context:
{context}

Question: {question}"""

    # ── Anthropic API format ──
    if config.LLM_PROVIDER == "anthropic":
        response = llm_client.messages.create(
            model=config.LLM_MODEL,
            max_tokens=config.MAX_TOKENS,
            system=config.SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message},
            ],
        )
        return response.content[0].text.strip()

    # ── OpenAI / DeepSeek API format ──
    response = llm_client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[
            {"role": "system", "content": config.SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=config.MAX_TOKENS,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


# ── Core ──────────────────────────────────────────────────────────────────────

def query(
    question: str,
    openai_api_key: str = "",
    llm_api_key: str = "",
    verbose: bool = False,
):
    # ── Init clients ──
    llm_client    = init_llm_client(llm_api_key)
    chroma_client = chromadb.PersistentClient(path=config.CHROMA_DIR)

    try:
        collection = chroma_client.get_collection(name=config.COLLECTION_NAME)
    except Exception:
        print(f"[error] Collection '{config.COLLECTION_NAME}' not found.")
        print("        Run index.py first.")
        exit(1)

    print(f"[query] Question : {question}")
    print(f"[query] Searching top {config.TOP_K} chunks...\n")

    # ── Step 1: Embed question ──
    vector = embed_question(question, openai_api_key)

    # ── Step 2: Vector search ──
    chunks = search_chunks(collection, vector)

    if not chunks:
        print("[query] No relevant chunks found.")
        return

    # ── Verbose: show retrieved chunks ──
    if verbose:
        print("─" * 60)
        print(f"[verbose] Retrieved {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks, 1):
            score   = chunk["score"]
            url     = chunk["metadata"].get("url", "")
            title   = chunk["metadata"].get("title", "")
            preview = chunk["text"][:200].replace("\n", " ")
            print(f"  [{i}] score={score:.4f} | {title}")
            print(f"       url: {url}")
            print(f"       preview: {preview}...")
            print()
        print("─" * 60 + "\n")

    # ── Step 3: Build context ──
    context = build_context(chunks)

    # ── Step 4: Ask LLM ──
    print(f"[query] Generating answer via {config.LLM_PROVIDER} / {config.LLM_MODEL}...\n")
    answer = ask_llm(llm_client, question, context)

    print("=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(answer)
    print("=" * 60)

    return answer


# ── Interactive mode ──────────────────────────────────────────────────────────

def interactive_mode(openai_api_key: str, llm_api_key: str, verbose: bool):
    """Chạy vòng lặp Q&A liên tục trong terminal."""
    print("\n" + "=" * 60)
    print(f"  OpenClaw RAG - Interactive Mode")
    print(f"  Embed : {config.EMBED_PROVIDER} / "
          f"{config.EMBED_MODEL_OPENAI if config.EMBED_PROVIDER == 'openai' else config.EMBED_MODEL_LOCAL}")
    print(f"  LLM   : {config.LLM_PROVIDER} / {config.LLM_MODEL}")
    print("  Type 'exit' or 'quit' to stop")
    print("=" * 60 + "\n")

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[query] Bye!")
            break

        if not question:
            continue

        if question.lower() in ("exit", "quit", "bye"):
            print("[query] Bye!")
            break

        query(question, openai_api_key, llm_api_key, verbose)
        print()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the RAG knowledge base")
    parser.add_argument(
        "question",
        nargs="?",
        default=None,
        help="Question to ask (omit for interactive mode)",
    )
    parser.add_argument(
        "--openai-key",
        default=os.getenv("OPENAI_API_KEY", ""),
        help="OpenAI API key (required if EMBED_PROVIDER=openai)",
    )
    parser.add_argument(
        "--llm-key",
        default=os.getenv("LLM_API_KEY", ""),
        help="LLM provider API key",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show retrieved chunks before answer",
    )
    args = parser.parse_args()

    # ── Validate keys ──
    if config.EMBED_PROVIDER == "openai" and not args.openai_key:
        print("[error] OpenAI API key is required when EMBED_PROVIDER=openai")
        print("        Set env: export OPENAI_API_KEY=your_key")
        print("        Or pass:  --openai-key your_key")
        exit(1)

    # Nếu LLM cũng là OpenAI thì dùng chung key
    llm_key = args.llm_key or args.openai_key

    if not llm_key:
        print(f"[error] LLM API key is required for {config.LLM_PROVIDER}")
        print(f"        Set env: export LLM_API_KEY=your_{config.LLM_PROVIDER}_key")
        print(f"        Or pass:  --llm-key your_key")
        exit(1)

    if args.question:
        query(args.question, args.openai_key, llm_key, args.verbose)
    else:
        interactive_mode(args.openai_key, llm_key, args.verbose)
