# OpenClaw Website Knowledge RAG

> Hệ thống RAG (Retrieval-Augmented Generation) đơn giản, hiệu quả —  
> Crawl website → Chunk → Embedding → Vector DB → AI Answer

---

## Kiến trúc tổng quan

```
Website
  └─► crawl.py (Firecrawl)
        └─► /data/*.md
              └─► chunk.py
                    └─► /chunks/chunks.json
                          └─► index.py (OpenAI Embedding + ChromaDB)
                                └─► /chroma_db/
                                      └─► query.py (OpenAI / DeepSeek / Anthropic)
                                            └─► Answer ✓
```

---

## Yêu cầu hệ thống

- Python **3.10+**
- OpenAI API key *(bắt buộc — dùng cho embedding)* → [platform.openai.com](https://platform.openai.com)
- Firecrawl API key → [firecrawl.dev](https://firecrawl.dev)
- LLM API key *(chọn 1 trong 3)*:
  - OpenAI → [platform.openai.com](https://platform.openai.com)
  - DeepSeek → [platform.deepseek.com](https://platform.deepseek.com)
  - Anthropic → [console.anthropic.com](https://console.anthropic.com)

---

## Cài đặt

### 1. Clone / tạo project

```bash
mkdir openclaw-rag && cd openclaw-rag
```

### 2. Tạo virtual environment

```bash
python -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Cài dependencies

```bash
# Base (bắt buộc)
pip install firecrawl-py openai chromadb

# Nếu dùng Anthropic (tuỳ chọn)
pip install anthropic
```

### 4. Set API keys

```bash
# Linux / macOS

# Bắt buộc (dùng cho embedding + crawl)
export FIRECRAWL_API_KEY=your_firecrawl_key
export OPENAI_API_KEY=your_openai_key

# LLM key — chọn 1 trong 3:
export LLM_API_KEY=your_openai_key      # nếu dùng OpenAI
export LLM_API_KEY=your_deepseek_key    # nếu dùng DeepSeek
export LLM_API_KEY=your_anthropic_key   # nếu dùng Anthropic
```

```bat
:: Windows (Command Prompt)
set FIRECRAWL_API_KEY=your_firecrawl_key
set OPENAI_API_KEY=your_openai_key
set LLM_API_KEY=your_llm_key
```

> 💡 Nếu dùng OpenAI cho cả embedding lẫn LLM thì chỉ cần set `OPENAI_API_KEY`, không cần set `LLM_API_KEY`

---

## Cấu trúc thư mục

```
openclaw-rag/
│
├── crawl.py          # Bước 1: Crawl website → Markdown
├── chunk.py          # Bước 2: Chunk markdown → JSON
├── index.py          # Bước 3: Embedding → ChromaDB
├── query.py          # Bước 4: Query → LLM Answer
│
├── data/             # Auto-generated: markdown files từ crawl
│   ├── page1.md
│   └── page2.md
│
├── chunks/           # Auto-generated: chunks JSON
│   └── chunks.json
│
├── chroma_db/        # Auto-generated: vector database
│
└── README.md
```

---

## Hướng dẫn sử dụng

### Bước 1 — Crawl website

```bash
python crawl.py https://your-website.com
```

**Tùy chọn:**

| Flag | Mô tả | Default |
|------|-------|---------|
| `--limit` | Số trang tối đa | `500` |
| `--api-key` | Firecrawl API key | env var |

```bash
# Ví dụ giới hạn 100 trang
python crawl.py https://your-website.com --limit 100
```

**Output:** Các file `.md` trong thư mục `./data/`

---

### Bước 2 — Chunk markdown

```bash
python chunk.py
```

Không cần tham số. Tự động đọc toàn bộ `./data/*.md`

**Config trong file** (chỉnh nếu cần):

| Biến | Giá trị mặc định | Mô tả |
|------|-----------------|-------|
| `CHUNK_SIZE` | `1000` | Số ký tự mỗi chunk |
| `OVERLAP` | `150` | Số ký tự overlap |

**Output:** `./chunks/chunks.json`

---

### Bước 3 — Index vào ChromaDB

```bash
python index.py
```

**Tùy chọn:**

| Flag | Mô tả |
|------|-------|
| `--force` | Re-index toàn bộ, kể cả chunks đã có |
| `--api-key` | OpenAI API key |

```bash
# Chỉ index chunks mới (mặc định)
python index.py

# Force re-index toàn bộ
python index.py --force
```

**Output:** Vector database tại `./chroma_db/`

---

### Bước 4 — Query & nhận câu trả lời

#### Chọn LLM provider trong `query.py`

Mở file `query.py`, tìm phần **Config** và uncomment provider muốn dùng:

```python
# Option 1: OpenAI
LLM_PROVIDER = "openai"
LLM_MODEL    = "gpt-4o-mini"

# Option 2: DeepSeek
# LLM_PROVIDER = "deepseek"
# LLM_MODEL    = "deepseek-chat"

# Option 3: Anthropic
# LLM_PROVIDER = "anthropic"
# LLM_MODEL    = "claude-3-5-haiku-20241022"
```

#### Chạy query

```bash
# Hỏi 1 câu
python query.py "Sản phẩm của bạn có những loại nào?"

# Hỏi với verbose (xem chunks được retrieve)
python query.py "Sản phẩm của bạn có những loại nào?" --verbose

# Interactive mode — chat liên tục
python query.py

# Truyền API key trực tiếp
python query.py "..." --openai-key your_key --llm-key your_llm_key
```

**Tùy chọn:**

| Flag | Mô tả | Default |
|------|-------|---------|
| `--openai-key` | OpenAI API key (cho embedding) | `OPENAI_API_KEY` env |
| `--llm-key` | LLM provider API key | `LLM_API_KEY` env |
| `--top-k` | Số chunks retrieve | `5` |
| `--verbose` | Hiển thị chunks + score | `false` |

---

## Chạy toàn bộ pipeline (1 lần)

```bash
# Set keys
export FIRECRAWL_API_KEY=your_firecrawl_key
export OPENAI_API_KEY=your_openai_key
export LLM_API_KEY=your_llm_key        # bỏ qua nếu dùng OpenAI

# Run pipeline
python crawl.py https://your-website.com --limit 200
python chunk.py
python index.py
python query.py "Câu hỏi của bạn ở đây"
```

---

## Cập nhật khi website thay đổi

> Không cần re-index toàn bộ. Chỉ crawl lại → chunk lại → index mới.

```bash
# 1. Crawl lại (ghi đè file .md cũ)
python crawl.py https://your-website.com

# 2. Chunk lại
python chunk.py

# 3. Index chỉ chunks mới (tự động skip chunks đã có)
python index.py
```

---

## Optional: Dùng file `.env`

### Cài thêm

```bash
pip install python-dotenv
```

### Tạo file `.env`

```env
FIRECRAWL_API_KEY=your_firecrawl_key
OPENAI_API_KEY=your_openai_key
LLM_API_KEY=your_llm_key
```

### Thêm vào đầu mỗi file `.py`

```python
from dotenv import load_dotenv
load_dotenv()
```

### Thêm `.env` vào `.gitignore`

```bash
echo ".env" >> .gitignore
```

---

## So sánh LLM provider

| | OpenAI | DeepSeek | Anthropic |
|---|---|---|---|
| **Model** | gpt-4o-mini | deepseek-chat | claude-3-5-haiku |
| **SDK** | `openai` | `openai` (compatible) | `anthropic` |
| **Giá** | ~$0.15/1M tokens | ~$0.07/1M tokens | ~$0.25/1M tokens |
| **Tiếng Việt** | Tốt | Tốt | Rất tốt |
| **Cài thêm** | Không | Không | `pip install anthropic` |

> 💡 **DeepSeek** rẻ nhất, dùng lại OpenAI SDK nên dễ tích hợp nhất.  
> 💡 **Anthropic** mạnh nhất về ngôn ngữ tự nhiên và tiếng Việt.  
> 💡 **Embedding luôn dùng OpenAI** `text-embedding-3-small` bất kể chọn LLM nào.

---

## Chi phí ước tính

### Embedding (OpenAI `text-embedding-3-small`) — chạy 1 lần khi index

| Website size | Số trang | Chunks ước tính | Chi phí index |
|---|---|---|---|
| Nhỏ | ~50 | ~500 | ~$0.01 |
| Vừa | ~200 | ~2,000 | ~$0.04 |
| Lớn | ~500 | ~5,000 | ~$0.10 |

### LLM — chi phí mỗi câu hỏi

| Provider | Model | Chi phí/query |
|---|---|---|
| OpenAI | gpt-4o-mini | ~$0.002 |
| DeepSeek | deepseek-chat | ~$0.001 |
| Anthropic | claude-3-5-haiku | ~$0.003 |

---

## Troubleshooting

### ❌ `Collection not found`
```
Run index.py trước khi chạy query.py
```

### ❌ `No markdown files found`
```
Run crawl.py trước khi chạy chunk.py
```

### ❌ `Rate limit error` (OpenAI)
```
Giảm BATCH_SIZE trong index.py xuống 50
Tăng SLEEP_BETWEEN lên 1.0
```

### ❌ `Firecrawl timeout`
```
Giảm --limit xuống 100
Thử lại sau vài phút
```

### ❌ `Module anthropic not found`
```
pip install anthropic
```

### ❌ Câu trả lời không chính xác
```
Giảm CHUNK_SIZE xuống 800 trong chunk.py
Tăng --top-k lên 7 khi query
Kiểm tra data/ có đủ nội dung không
```

---

## Tech Stack

| Component | Tool |
|---|---|
| Crawling | Firecrawl |
| Embedding | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB |
| LLM | OpenAI gpt-4o-mini / DeepSeek deepseek-chat / Anthropic claude-3-5-haiku |
| Language | Python 3.10+ |

---

## License

MIT License — Free to use and modify.

---

*Built for OpenClaw AI Agent — Website Knowledge RAG*
