# chunk.py
# Read markdown files from /data → split into chunks → save as JSON

import os
import re
import json

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_DIR  = "data"
OUTPUT_DIR = "chunks"
CHUNK_SIZE = 1000   # characters
OVERLAP    = 150    # characters overlap between chunks

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_front_matter(content: str) -> tuple[dict, str]:
    """Extract YAML front-matter metadata and body text."""
    metadata = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            raw_meta = parts[1].strip()
            body = parts[2].strip()
            for line in raw_meta.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    try:
                        metadata[key.strip()] = json.loads(val.strip())
                    except json.JSONDecodeError:
                        metadata[key.strip()] = val.strip()

    return metadata, body


def clean_text(text: str) -> str:
    """Remove excessive whitespace and blank lines."""
    # Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove trailing spaces per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip()


def split_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = OVERLAP) -> list[str]:
    """
    Sliding window chunking.
    Tries to split at paragraph/sentence boundaries when possible.
    """
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + chunk_size

        if end >= length:
            # Last chunk
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Try to find a good split point (paragraph > newline > space)
        split_at = end
        for boundary in ["\n\n", "\n", ". ", " "]:
            pos = text.rfind(boundary, start, end)
            if pos != -1 and pos > start + overlap:
                split_at = pos + len(boundary)
                break

        chunk = text[start:split_at].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward with overlap
        start = split_at - overlap

    return chunks


# ── Core ──────────────────────────────────────────────────────────────────────

def process_file(filepath: str) -> list[dict]:
    """Read one markdown file and return list of chunk dicts."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    metadata, body = parse_front_matter(raw)
    body = clean_text(body)

    if not body:
        return []

    raw_chunks = split_chunks(body)
    filename = os.path.basename(filepath)

    result = []
    for i, chunk_text in enumerate(raw_chunks):
        result.append({
            "chunk_id"  : f"{filename}__chunk_{i:04d}",
            "source"    : filename,
            "url"       : metadata.get("url", ""),
            "title"     : metadata.get("title", ""),
            "chunk_index": i,
            "total_chunks": len(raw_chunks),
            "text"      : chunk_text,
            "char_count": len(chunk_text),
        })

    return result


def chunk_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    md_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".md")]
    if not md_files:
        print(f"[chunk] No markdown files found in ./{INPUT_DIR}/")
        return

    print(f"[chunk] Found {len(md_files)} markdown files")
    print(f"[chunk] Chunk size: {CHUNK_SIZE} | Overlap: {OVERLAP}\n")

    all_chunks = []
    total_chunks = 0

    for filename in sorted(md_files):
        filepath = os.path.join(INPUT_DIR, filename)
        chunks = process_file(filepath)
        total_chunks += len(chunks)
        all_chunks.extend(chunks)
        print(f"  [ok] {filename:60s} → {len(chunks):3d} chunks")

    # Save all chunks to single JSON file
    out_path = os.path.join(OUTPUT_DIR, "chunks.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n[chunk] Total chunks: {total_chunks}")
    print(f"[chunk] Saved → {out_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    chunk_all()
