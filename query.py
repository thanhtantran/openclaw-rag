# query.py
# Query the vector index with natural language

import os
import json
import time
import argparse
import numpy as np
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Load configuration
import config
config.validate()

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_embedding_local(text):
    """Get embedding for a single text using local model."""
    try:
        from sentence_transformers import SentenceTransformer
        
        print(f"[query] Loading local model: {config.EMBED_MODEL_LOCAL} ...")
        model = SentenceTransformer(config.EMBED_MODEL_LOCAL)
        print("[query] Local model loaded.")
        
        return model.encode(text).tolist()
    except ImportError:
        print("[error] SentenceTransformers not installed. Run: pip install sentence-transformers")
        exit(1)


def get_embedding_openai(text):
    """Get embedding for a single text using OpenAI API."""
    try:
        import openai
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("[error] OPENAI_API_KEY not found in environment variables")
            exit(1)
            
        openai.api_key = openai_api_key
        
        print(f"[query] Getting OpenAI embedding using {config.EMBED_MODEL_OPENAI}...")
        response = openai.Embedding.create(input=text, model=config.EMBED_MODEL_OPENAI)
        return response["data"][0]["embedding"]
    except ImportError:
        print("[error] OpenAI not installed. Run: pip install openai")
        exit(1)


def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def search_chunks(query_embedding, chunks, top_k=5, threshold=0.2):
    """Search for most similar chunks to query embedding."""
    similarities = []
    
    for i, chunk in enumerate(chunks):
        if "embedding" not in chunk:
            print(f"[warning] Chunk {i} has no embedding, skipping")
            continue
            
        similarity = cosine_similarity(query_embedding, chunk["embedding"])
        similarities.append((chunk, similarity))
    
    # Sort by similarity (highest first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Filter by threshold and take top_k
    results = [(chunk, score) for chunk, score in similarities if score > threshold][:top_k]
    
    return results


def query_llm_openai(question, context, model="gpt-4o-mini"):
    """Query OpenAI API with question and context."""
    try:
        import openai
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("[error] OPENAI_API_KEY not found in environment variables")
            exit(1)
            
        openai.api_key = openai_api_key
        
        # Call API
        print(f"[query] Calling OpenAI API ({model})...")
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": config.SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
            temperature=0.1,
            max_tokens=config.MAX_TOKENS
        )
        
        return response.choices[0].message.content.strip()
    except ImportError:
        print("[error] OpenAI not installed. Run: pip install openai")
        exit(1)


def query_llm_deepseek(question, context, model="deepseek-chat"):
    """Query DeepSeek API with question and context."""
    try:
        from deepseek import DeepSeekAPI
        
        deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not deepseek_api_key:
            print("[error] DEEPSEEK_API_KEY not found in environment variables")
            exit(1)
            
        # Khởi tạo API client
        api_client = DeepSeekAPI(api_key=deepseek_api_key)
        
        # Chuẩn bị prompt
        prompt = f"System: {config.SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}"
        
        # Call API
        print(f"[query] Calling DeepSeek API ({model})...")
        response = api_client.chat_completion(
            prompt=prompt,
            model=model,
            temperature=0.1,
            max_tokens=config.MAX_TOKENS
        )
        
        return response
        
    except ImportError:
        print("[error] DeepSeek API not installed. Run: pip install deepseek")
        return "Không thể kết nối với DeepSeek API. Vui lòng cài đặt thư viện: pip install deepseek"
    except Exception as e:
        print(f"[error] DeepSeek API error: {e}")
        return f"Lỗi khi gọi DeepSeek API: {str(e)}"


def query_llm_anthropic(question, context, model="claude-3-5-haiku-20241022"):
    """Query Anthropic API with question and context."""
    try:
        import anthropic
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            print("[error] ANTHROPIC_API_KEY not found in environment variables")
            exit(1)
            
        client = anthropic.Anthropic(api_key=anthropic_api_key)
        
        # Call API
        print(f"[query] Calling Anthropic API ({model})...")
        response = client.messages.create(
            model=model,
            system=config.SYSTEM_PROMPT,
            max_tokens=config.MAX_TOKENS,
            messages=[
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
            ],
            temperature=0.1
        )
        
        return response.content[0].text
    except ImportError:
        print("[error] Anthropic not installed. Run: pip install anthropic")
        exit(1)


# ── Core ──────────────────────────────────────────────────────────────────────

def query(question, top_k=config.TOP_K, debug=False):
    """Query the vector index with natural language."""
    print(f"[query] Question : {question}")
    print(f"[query] Searching top {top_k} chunks...")
    
    # Load index
    try:
        with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
            index_data = json.load(f)
            chunks = index_data.get("chunks", [])
        
        if not chunks:
            print("[error] No chunks found in index")
            return
    except FileNotFoundError:
        print(f"[error] Index file not found: {config.INDEX_FILE}")
        print("        Run indexing first: python index.py")
        return
    
    # Get query embedding
    if config.EMBED_PROVIDER == "openai":
        query_embedding = get_embedding_openai(question)
    else:  # local
        query_embedding = get_embedding_local(question)
    
    # Search for similar chunks
    results = search_chunks(query_embedding, chunks, top_k=top_k, threshold=0.2)
    
    if not results:
        print("[query] No relevant chunks found.")
        
        # Vẫn trả lời ngay cả khi không có chunks phù hợp
        no_info_context = "Không tìm thấy thông tin liên quan trong dữ liệu."
        
        if config.LLM_PROVIDER == "openai":
            answer = query_llm_openai(question, no_info_context, model=config.LLM_MODEL)
        elif config.LLM_PROVIDER == "deepseek":
            answer = query_llm_deepseek(question, no_info_context, model=config.LLM_MODEL)
        elif config.LLM_PROVIDER == "anthropic":
            answer = query_llm_anthropic(question, no_info_context, model=config.LLM_MODEL)
        else:
            answer = "Không tìm thấy thông tin liên quan và không có LLM provider được cấu hình."
        
        print("\n" + "=" * 80)
        print(answer)
        print("=" * 80)
        return
    
    # Debug: print similarity scores
    if debug:
        print("\n[debug] Similarity scores:")
        for i, (chunk, score) in enumerate(results):
            print(f"  {i+1}. Score: {score:.4f} - {chunk.get('text', '')[:100]}...")
    
    # Build context from chunks
    context = ""
    for i, (chunk, score) in enumerate(results):
        text = chunk.get("text", "").strip()
        source = ""
        
        # Try to extract source information
        if "source" in chunk:
            source = f" (Source: {chunk['source']})"
        elif "url" in chunk:
            source = f" (Source: {chunk['url']})"
        elif "file" in chunk:
            source = f" (Source: {chunk['file']})"
        
        context += f"[{i+1}] {text}{source}\n\n"
    
    # Query LLM with context
    if config.LLM_PROVIDER == "openai":
        answer = query_llm_openai(question, context, model=config.LLM_MODEL)
    elif config.LLM_PROVIDER == "deepseek":
        answer = query_llm_deepseek(question, context, model=config.LLM_MODEL)
    elif config.LLM_PROVIDER == "anthropic":
        answer = query_llm_anthropic(question, context, model=config.LLM_MODEL)
    else:
        print(f"[error] Unknown LLM provider: {config.LLM_PROVIDER}")
        return
    
    # Print answer
    print("\n" + "=" * 80)
    print(answer)
    print("=" * 80)
    
    # Debug: print context
    if debug:
        print("\n[debug] Context used:")
        print(context)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query the vector index with natural language")
    parser.add_argument(
        "question",
        help="Question to ask",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=config.TOP_K,
        help=f"Number of chunks to retrieve (default: {config.TOP_K})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output",
    )
    args = parser.parse_args()
    
    query(args.question, top_k=args.top_k, debug=args.debug)
