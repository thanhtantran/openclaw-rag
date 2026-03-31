# crawl.py
# Crawl website using Firecrawl and save as markdown files

import os
import re
import json
import argparse
from firecrawl import FirecrawlApp

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "data"
DEFAULT_LIMIT = 500

# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_filename(url: str) -> str:
    """Convert URL to a safe filename."""
    name = re.sub(r"https?://", "", url)
    name = re.sub(r"[^\w\-]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name[:120]  # limit length


def save_markdown(filename: str, content: str, metadata: dict) -> str:
    """Save markdown content with front-matter metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, f"{filename}.md")

    front_matter = "---\n"
    for k, v in metadata.items():
        front_matter += f"{k}: {json.dumps(v, ensure_ascii=False)}\n"
    front_matter += "---\n\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(front_matter + content)

    return filepath


# ── Main ──────────────────────────────────────────────────────────────────────

def crawl(url: str, api_key: str, limit: int = DEFAULT_LIMIT):
    print(f"[crawl] Starting crawl: {url}")
    print(f"[crawl] Limit: {limit} pages")

    app = FirecrawlApp(api_key=api_key)

    result = app.crawl_url(
        url,
        params={
            "limit": limit,
            "scrapeOptions": {
                "formats": ["markdown"],
                "onlyMainContent": True,
            },
        },
        poll_interval=5,
    )

    pages = result.get("data", [])
    print(f"[crawl] Total pages crawled: {len(pages)}")

    saved = 0
    skipped = 0

    for page in pages:
        markdown = page.get("markdown", "").strip()
        source_url = page.get("metadata", {}).get("sourceURL", "")
        title = page.get("metadata", {}).get("title", "")
        description = page.get("metadata", {}).get("description", "")

        if not markdown:
            print(f"  [skip] Empty content: {source_url}")
            skipped += 1
            continue

        filename = sanitize_filename(source_url)
        metadata = {
            "url": source_url,
            "title": title,
            "description": description,
        }

        filepath = save_markdown(filename, markdown, metadata)
        print(f"  [saved] {filepath}  ({len(markdown)} chars)")
        saved += 1

    print(f"\n[crawl] Done. Saved: {saved} | Skipped: {skipped}")
    print(f"[crawl] Output directory: ./{OUTPUT_DIR}/")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl website to markdown files")
    parser.add_argument("url", help="Target website URL (e.g. https://example.com)")
    parser.add_argument(
        "--api-key",
        default=os.getenv("FIRECRAWL_API_KEY", ""),
        help="Firecrawl API key (or set FIRECRAWL_API_KEY env var)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Max pages to crawl (default: {DEFAULT_LIMIT})",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("[error] Firecrawl API key is required.")
        print("        Set env: export FIRECRAWL_API_KEY=your_key")
        print("        Or pass:  --api-key your_key")
        exit(1)

    crawl(args.url, args.api_key, args.limit)
