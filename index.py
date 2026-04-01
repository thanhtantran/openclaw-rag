# index.py
# Create vector index from chunks

import os
import json
import time
import argparse
import numpy as np
from tqdm import tqdm
from pathlib import Path
import sys
import importlib.util

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Load configuration
import config
config.validate()

# ── Helpers ───────────────────────────────────────────────────────────────────

def check_package_installed(package_name):
    """Check if a package is installed and can be imported."""
    spec = importlib.util.find_spec(package_name)
    return spec is not None

def get_embeddings_local(texts, batch_size=32):
    """Get embeddings using local SentenceTransformers."""
    # Check if sentence_transformers is installed
    if not check_package_installed("sentence_transformers"):
        print("[error] SentenceTransformers not installed.")
        print("        Run: pip install -U sentence-transformers")
        print("        Make sure you're in the correct virtual environment.")
        exit(1)
    
    try:
        # Try importing with more detailed error handling
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            print(f"[error] Import error: {e}")
            print("        Python path: ", sys.path)
            print("        Try reinstalling with: pip install -U sentence-transformers")
            exit(1)
        
        # Try loading the model with error handling
        try:
            print(f"[index] Loading model: {config.EMBED_MODEL_LOCAL}")
            model = SentenceTransformer(config.EMBED_MODEL_LOCAL)
        except Exception as e:
            print(f"[error] Failed to load model: {e}")
            print("        Try a different model or check internet connection")
            exit(1)
        
        # Process in batches to avoid OOM
        all_embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch = texts[i:i+batch_size]
            embeddings = model.encode(batch)
            all_embeddings.extend(embeddings.tolist())
        
        return all_embeddings
    except Exception as e:
        print(f"[error] Unexpected error in embedding process: {e}")
        import traceback
        traceback.print_exc()
        exit(1)


def get_embeddings_openai(texts, batch_size=32):
    """Get embeddings using OpenAI API."""
    try:
        import openai
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("[error] OPENAI_API_KEY not found in environment variables")
            exit(1)
            
        openai.api_key = openai_api_key
        
        all_embeddings = []
        for i in tqdm(range(0, len(texts), batch_size), desc="Embedding batches"):
            batch = texts[i:i+batch_size]
            response = openai.Embedding.create(input=batch, model=config.EMBED_MODEL_OPENAI)
            batch_embeddings = [item["embedding"] for item in response["data"]]
            all_embeddings.extend(batch_embeddings)
            time.sleep(0.5)  # Avoid rate limits
            
        return all_embeddings
    except ImportError:
        print("[error] OpenAI not installed. Run: pip install openai")
        exit(1)


# ── Core ──────────────────────────────────────────────────────────────────────

def index(force=False):
    """Create vector index from chunks."""
    # Ensure output dir exists
    os.makedirs(os.path.dirname(config.INDEX_FILE), exist_ok=True)
    
    # Load chunks
    try:
        with open(config.CHUNKS_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        print(f"[index] Loaded {len(chunks)} chunks from {config.CHUNKS_FILE}")
    except FileNotFoundError:
        print(f"[error] Chunks file not found: {config.CHUNKS_FILE}")
        print("        Run chunking first: python chunk.py")
        exit(1)
    
    # Check if index exists and handle accordingly
    if os.path.exists(config.INDEX_FILE) and not force:
        try:
            with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
                index_data = json.load(f)
                existing_chunks = index_data.get("chunks", [])
            
            # Assign IDs to chunks if they don't have them
            for i, chunk in enumerate(chunks):
                if "id" not in chunk:
                    chunk["id"] = f"chunk_{i}"
            
            # Get IDs of existing chunks
            existing_ids = set()
            for chunk in existing_chunks:
                if "id" in chunk:
                    existing_ids.add(chunk["id"])
                elif "text" in chunk:
                    # Use text as fallback ID
                    existing_ids.add(chunk["text"])
            
            # Filter out chunks that are already in the index
            new_chunks = []
            for chunk in chunks:
                chunk_id = chunk.get("id")
                if chunk_id and chunk_id in existing_ids:
                    continue
                if "text" in chunk and chunk["text"] in existing_ids:
                    continue
                new_chunks.append(chunk)
            
            if not new_chunks:
                print("[index] No new chunks to index.")
                return
            
            print(f"[index] Found {len(new_chunks)} new chunks to add to existing index")
            chunks = new_chunks
            append_mode = True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[warning] Existing index is invalid, rebuilding: {e}")
            append_mode = False
    else:
        append_mode = False
    
    # Extract texts for embedding
    texts = []
    for i, chunk in enumerate(chunks):
        # Assign ID if not present
        if "id" not in chunk:
            chunk["id"] = f"chunk_{i}"
            
        # Extract text for embedding
        if "text" in chunk:
            texts.append(chunk["text"])
        else:
            # If no text field, use the first string value found
            for key, value in chunk.items():
                if isinstance(value, str) and value.strip():
                    texts.append(value)
                    chunk["text"] = value  # Ensure there's a text field
                    break
            else:
                print(f"[warning] Skipping chunk with no text content: {chunk}")
                texts.append("")  # Add empty placeholder to maintain indices
    
    # Get embeddings based on provider
    if config.EMBED_PROVIDER == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            print("[error] OPENAI_API_KEY required in .env file for OpenAI embeddings")
            exit(1)
        print(f"[index] Getting OpenAI embeddings for {len(texts)} chunks using {config.EMBED_MODEL_OPENAI}")
        embeddings = get_embeddings_openai(texts)
    else:  # local
        print(f"[index] Getting local embeddings for {len(texts)} chunks using {config.EMBED_MODEL_LOCAL}")
        embeddings = get_embeddings_local(texts)
    
    # Assign embeddings to chunks
    for i, embedding in enumerate(embeddings):
        if i < len(chunks):  # Safety check
            chunks[i]["embedding"] = embedding
    
    # Save index
    if append_mode:
        # Append to existing index
        with open(config.INDEX_FILE, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        index_data["chunks"].extend(chunks)
        
        with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False)
        
        print(f"[index] ✓ Added {len(chunks)} chunks to index: {config.INDEX_FILE}")
    else:
        # Create new index
        index_data = {
            "config": {
                "embedding_provider": config.EMBED_PROVIDER,
                "embedding_model": config.EMBED_MODEL_LOCAL if config.EMBED_PROVIDER == "local" else config.EMBED_MODEL_OPENAI,
                "llm_provider": config.LLM_PROVIDER,
                "llm_model": config.LLM_MODEL,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            },
            "chunks": chunks
        }
        
        with open(config.INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False)
        
        print(f"[index] ✓ Created new index with {len(chunks)} chunks: {config.INDEX_FILE}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create vector index from chunks")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild index even if it exists",
    )
    args = parser.parse_args()
    
    # Print Python environment info
    print(f"[debug] Python version: {sys.version}")
    print(f"[debug] Python executable: {sys.executable}")
    print(f"[debug] Working directory: {os.getcwd()}")
    
    index(force=args.force)
