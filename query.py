# query.py
# Embed user question → Vector search ChromaDB → Send context to LLM → Answer
# Supported LLM providers: OpenAI, DeepSeek, Anthropic

import os
import argparse
import chromadb
from openai import OpenAI

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_DIR      = "chroma_db"
COLLECTION_NAME = "website_knowledge"
EMBED_MODEL     = "text-embedding-3-small"
TOP_K           = 5      # số chunks lấy từ vector search
MAX_TOKENS      = 1024   # max tokens cho LLM response

# ── Chọn LLM Provider ─────────────────────────────────────────────────────────
# Uncomment provider muốn dùng, comment các provider còn lại

LLM_PROVIDER = "openai"
LLM_MODEL    = "gpt-4o-mini"

# LLM_PROVIDER = "deepseek"
# LLM_MODEL    = "deepseek-chat"

# LLM_PROVIDER = "anthropic"
# LLM_MODEL    = "claude-3-5-haiku-20241022"

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful assistant that answers questions based strictly on the provided context.

Rules:
- Answer ONLY based on the context below.
- If the answer is not in the context, say: "I don't have information about that."
- Be concise and clear.
- If relevant, mention the source URL.
- Respond in the same language as the user's question.
"""

# ── Init LLM Client ───────────────────────────────────────────────────────────

def init_llm_client(api_key: str):
    """Initialize LLM client based on selected provider."""
    if LLM_PROVIDER == "openai":
        return OpenAI(api_key=api_key)

    elif LLM_PROVIDER == "deepseek":
        return OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    elif LLM_PROVIDER == "anthropic":
        try:
            import anthropic
        except ImportError:
            print("[error] Anthropic SDK not installed.")
            print("        Run: pip install anthropic")
            exit(1)
        return anthropic.Anthropic(api_key=api_key)

    else:
        print(f"[error] Unknown LLM provider: '{LLM_PROVIDER}'")
        print("        Valid options: openai | deepseek | anthropic")
        exit(1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def embed_question(question: str, openai_api_key: str) -> list[float]:
    """Embed the user question using OpenAI embedding model."""
    client = OpenAI(api_key=openai_api_key)
    response = client.embeddings.create(
        model=EMBED_MODEL,
        input=[question],
    )
    return response.data[0].embedding


def search_chunks(collection, vector: list[float], top_k: int = TOP_K) -> list[dict]:
    """Query ChromaDB for most relevant chunks."""
    results = collection.query(
        query_embeddings=[vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        chunks.append({
            "id"      : results["ids"][0][i],
            "text"    : results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "score"   : 1 - results["distances"][0][i],  # cosine similarity
        })

    return chunks


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for LLM."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        url   = chunk["metadata"].get("url", "")
        title = chunk["metadata"].get("title", "")
        header = f"[Source {i}]"
        if title:
            header += f" {title}"
        if url:
            header += f" ({url})"
        parts.append(f"{header}\n{chunk['text']}")

    return "\n\n---\n\n".join(parts)


def ask_llm(llm_client, question: str, context: str) -> str:
    """Send question + context to LLM and return answer."""
    user_message = f"""Context:
{context}

Question: {question}"""

    # ── Anthropic API format ──
    if LLM_PROVIDER == "anthropic":
        response = llm_client.messages.create(
            model=LLM_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message},
            ],
        )
        return response.content[0].text.strip()

    # ── OpenAI / DeepSeek API format (compatible) ──
    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


# ── Core ──────────────────────────────────────────────────────────────────────

def query(
    question: str,
    openai_api_key: str,
    llm_api_key: str,
    top_k: int = TOP_K,
    verbose: bool = False,
):
    # ── Init clients ──
    llm_client    = init_llm_client(llm_api_key)
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception:
        print(f"[error] Collection '{COLLECTION_NAME}' not found.")
        print("        Run index.py first.")
        exit(1)

    print(f"[query] Provider : {LLM_PROVIDER} / {LLM_MODEL}")
    print(f"[query] Question : {question}")
    print(f"[query] Searching top {top_k} chunks...\n")

    # ── Step 1: Embed question ──
    vector = embed_question(question, openai_api_key)

    # ── Step 2: Vector search ──
    chunks = search_chunks(collection, vector, top_k)

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
    print(f"[query] Generating answer via {LLM_PROVIDER}...\n")
    answer = ask_llm(llm_client, question, context)

    print("=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(answer)
    print("=" * 60)

    return answer


# ── Interactive mode ──────────────────────────────────────────────────────────

def interactive_mode(openai_api_key: str, llm_api_key: str, top_k: int, verbose: bool):
    """Run continuous Q&A loop in terminal."""
    print("\n" + "=" * 60)
    print(f"  OpenClaw RAG - Interactive Mode")
    print(f"  LLM: {LLM_PROVIDER} / {LLM_MODEL}")
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

        query(question, openai_api_key, llm_api_key, top_k, verbose)
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
        help="OpenAI API key for embedding (or set OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--llm-key",
        default=os.getenv("LLM_API_KEY", ""),
        help="LLM provider API key (or set LLM_API_KEY env var)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K,
        help=f"Number of chunks to retrieve (default: {TOP_K})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show retrieved chunks before answer",
    )
    args = parser.parse_args()

    # ── Validate API keys ──
    if not args.openai_key:
        print("[error] OpenAI API key is required for embedding.")
        print("        Set env: export OPENAI_API_KEY=your_key")
        print("        Or pass:  --openai-key your_key")
        exit(1)

    # Nếu cùng provider là OpenAI thì dùng chung 1 key
    llm_key = args.llm_key or args.openai_key

    if not llm_key:
        print(f"[error] LLM API key is required for {LLM_PROVIDER}.")
        print(f"        Set env: export LLM_API_KEY=your_{LLM_PROVIDER}_key")
        print(f"        Or pass:  --llm-key your_key")
        exit(1)

    if args.question:
        # Single question mode
        query(args.question, args.openai_key, llm_key, args.top_k, args.verbose)
    else:
        # Interactive mode
        interactive_mode(args.openai_key, llm_key, args.top_k, args.verbose)
