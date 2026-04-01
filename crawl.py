# crawl.py
# Crawl website → Convert to Markdown → Save to ./data/

import os
import re
import time
import json
import argparse
import requests

from dotenv import load_dotenv
load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = "data"
MAX_PAGES  = 500
API_BASE   = "https://api.firecrawl.dev"

# ── Helpers ───────────────────────────────────────────────────────────────────

def sanitize_filename(url: str) -> str:
    """Convert URL to safe filename."""
    # Remove protocol and domain
    name = re.sub(r'^https?://(www\.)?', '', url)
    # Remove query string and fragment
    name = re.sub(r'[?#].*$', '', name)
    # Replace special chars with underscore
    name = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    # Trim trailing slashes
    name = name.rstrip('/')
    # Add .md extension
    if not name:
        name = "index"
    return f"{name}.md"


def save_markdown(url: str, title: str, content: str) -> str:
    """Save markdown content to file."""
    # Create output dir if not exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Create filename from URL
    filename = sanitize_filename(url)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Add metadata
    metadata = f"---\nurl: {url}\ntitle: {title}\n---\n\n"
    
    # Write to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(metadata + content)
    
    return filepath


def save_debug_info(data, filename="debug_response.json"):
    """Save debug info to file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"[debug] Saved debug info to {filename}")


def extract_title_from_markdown(markdown):
    """Extract title from markdown content."""
    # Try to find a heading in the markdown
    heading_match = re.search(r'^#+\s+(.+)$', markdown, re.MULTILINE)
    if heading_match:
        return heading_match.group(1)
    
    # Try to find the first link text
    link_match = re.search(r'\[([^\]]+)\]', markdown)
    if link_match:
        return link_match.group(1)
    
    return "Untitled Page"


# ── Core ──────────────────────────────────────────────────────────────────────

def crawl(url: str, api_key: str = "", limit: int = MAX_PAGES, debug: bool = False):
    """Crawl website and save pages as markdown."""
    print(f"[crawl] Starting crawl: {url}")
    print(f"[crawl] Limit: {limit} pages")
    
    # Sử dụng /v2/crawl endpoint theo tài liệu mới
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Cấu hình crawl mở rộng
    payload = {
        "url": url,
        "limit": limit,
        "crawlEntireDomain": True,  # Cho phép crawl toàn bộ domain
        "allowSubdomains": True,    # Cho phép crawl subdomain
        "maxDiscoveryDepth": 3,     # Độ sâu tối đa
        "scrapeOptions": {
            "formats": ["markdown", "links"],  # Lấy cả links để debug
            "onlyMainContent": True
        }
    }
    
    # Bắt đầu crawl job
    try:
        print(f"[crawl] Sending request to {API_BASE}/v2/crawl")
        print(f"[crawl] Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(f"{API_BASE}/v2/crawl", 
                                headers=headers, 
                                json=payload)
        
        if debug:
            print(f"[debug] Response status: {response.status_code}")
            print(f"[debug] Response headers: {response.headers}")
            
        response.raise_for_status()
        job = response.json()
        
        if debug:
            save_debug_info(job, "debug_job_start.json")
            
        job_id = job.get("id")
        
        if not job_id:
            print(f"[error] Failed to start crawl job: {job}")
            return
            
        print(f"[crawl] Started job: {job_id}")
        print(f"[crawl] Status: {job.get('status', 'unknown')}")
        
        # Poll cho kết quả
        result_url = f"{API_BASE}/v2/crawl/{job_id}"
        done = False
        
        while not done:
            print("[crawl] Checking job status...")
            response = requests.get(result_url, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if debug:
                save_debug_info(result, "debug_job_status.json")
                
            status = result.get("status")
            print(f"[crawl] Status: {status}")
            
            # Hiển thị thêm thông tin về tiến độ nếu có
            if "progress" in result:
                progress = result["progress"]
                print(f"[crawl] Progress: {progress.get('current', 0)}/{progress.get('total', 0)} pages")
            
            # Hiển thị số lượng trang đã hoàn thành
            completed = result.get("completed", 0)
            total = result.get("total", 0)
            if completed > 0:
                print(f"[crawl] Completed: {completed}/{total} pages")
            
            if status == "completed":
                done = True
            elif status in ["failed", "canceled"]:
                print(f"[error] Job {status}: {result.get('error', 'Unknown error')}")
                return
            else:
                # Chờ 5 giây trước khi kiểm tra lại
                print("[crawl] Waiting 5 seconds...")
                time.sleep(5)
        
        # Lấy kết quả
        print("[crawl] Job completed, getting results...")
        
        # Kiểm tra cấu trúc kết quả
        if debug:
            print(f"[debug] Result keys: {list(result.keys())}")
        
        # Xử lý cấu trúc dữ liệu mới - data là một mảng
        pages = []
        if "data" in result and isinstance(result["data"], list):
            pages = result["data"]
        elif "pages" in result:
            pages = result["pages"]
        elif "result" in result and "pages" in result["result"]:
            pages = result["result"]["pages"]
            
        print(f"[crawl] Crawled {len(pages)} pages")
        
        if len(pages) == 0:
            print("[warning] No pages were crawled. This might be because:")
            print("  1. The website blocks crawlers")
            print("  2. The URL is invalid or inaccessible")
            print("  3. The website has no content that matches the crawl criteria")
            
            if debug:
                print("[debug] Full API response:")
                print(json.dumps(result, indent=2))
            return
        
        # Save each page
        saved = 0
        for page in pages:
            # Xử lý trường hợp page là string (markdown content)
            if isinstance(page, str):
                # Không có URL, sử dụng index
                url_path = f"page_{saved}"
                title = extract_title_from_markdown(page)
                content = page
            else:
                # Trường hợp page là object
                url_path = page.get("url", f"page_{saved}")
                
                # Tìm nội dung markdown theo nhiều cấu trúc có thể có
                content = ""
                if "markdown" in page:
                    content = page["markdown"]
                elif "formats" in page and "markdown" in page["formats"]:
                    content = page["formats"]["markdown"]
                elif "content" in page:
                    content = page["content"]
                
                # Tìm tiêu đề
                title = page.get("title", "")
                if not title:
                    title = extract_title_from_markdown(content)
            
            if not content:
                print(f"[warning] Skipping page with missing content: {url_path}")
                continue
            
            filepath = save_markdown(url_path, title, content)
            saved += 1
            
            print(f"[crawl] Saved: {filepath}")
            
            # Small delay to avoid hammering filesystem
            time.sleep(0.01)
        
        print(f"\n[crawl] ✓ Done! {saved}/{len(pages)} pages saved to ./{OUTPUT_DIR}/")
        
    except requests.exceptions.RequestException as e:
        print(f"[error] API request failed: {e}")
        if debug and hasattr(e, 'response') and e.response:
            print(f"[debug] Response status: {e.response.status_code}")
            print(f"[debug] Response body: {e.response.text}")
        return
    except Exception as e:
        print(f"[error] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl website to markdown")
    parser.add_argument(
        "url",
        help="Website URL to crawl",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("FIRECRAWL_API_KEY", ""),
        help="Firecrawl API key (or set FIRECRAWL_API_KEY env var)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=MAX_PAGES,
        help=f"Max pages to crawl (default: {MAX_PAGES})",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    args = parser.parse_args()
    
    # Validate API key
    if not args.api_key:
        print("[error] Firecrawl API key is required.")
        print("        Set env: export FIRECRAWL_API_KEY=your_key")
        print("        Or pass:  --api-key your_key")
        exit(1)
    
    crawl(args.url, args.api_key, args.limit, args.debug)
