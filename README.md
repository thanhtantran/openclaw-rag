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
                          └─► index.py (Embedding + ChromaDB)
                                └─► /chroma_db/
                                      └─► query.py (OpenAI / DeepSeek / Anthropic)
                                            └─► Answer ✓
```

---

## Yêu cầu hệ thống

- Python **3.10+**
- Firecrawl API key → [firecrawl.dev](https://firecrawl.dev)
- Tuỳ chọn theo cấu hình trong `config.py`:

| Thành phần | Provider | API Key cần thiết |
|---|---|---|
| **Embedding** | OpenAI | ✅ Bắt buộc |
| **Embedding** | Local (sentence-transformers) | ❌ Không cần |
| **LLM** | OpenAI | ✅ Bắt buộc |
| **LLM** | DeepSeek | ✅ Bắt buộc |
| **LLM** | Anthropic | ✅ Bắt buộc |

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
pip install firecrawl-py chromadb

# Nếu dùng OpenAI embedding hoặc LLM
pip install openai

# Nếu dùng Local embedding (sentence-transformers)
pip install sentence-transformers

# Nếu dùng Anthropic LLM
pip install anthropic
```

### 4. Set API keys

```bash
# Linux / macOS

# Crawl (bắt buộc)
export FIRECRAWL_API_KEY=your_firecrawl_key

# Embedding — chỉ cần nếu EMBED_PROVIDER=openai trong config.py
export OPENAI_API_KEY=your_openai_key

# LLM — chọn 1 trong 3 tuỳ theo LLM_PROVIDER trong config.py
export LLM_API_KEY=your_openai_key      # OpenAI
export LLM_API_KEY=your_deepseek_key    # DeepSeek
export LLM_API_KEY=your_anthropic_key   # Anthropic
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
├── config.py         # ⚙️  Cấu hình trung tâm — chỉnh tại đây
├── crawl.py          # Bước 1: Crawl website → Markdown
├── chunk.py          # Bước 2: Chunk markdown → JSON
├── index.py          # Bước 3: Embedding → ChromaDB
├── query.py          # Bước 4: Query → LLM Answer
│
├── data/             # Auto-generated: markdown files từ crawl
├── chunks/           # Auto-generated: chunks JSON
├── chroma_db/        # Auto-generated: vector database
│
└── README.md
```

---

## Cấu hình hệ thống (`config.py`)

> **Tất cả cấu hình đều nằm trong `config.py`** — không cần sửa các file khác.

### Chọn Embedding provider

```python
# Dùng OpenAI (chất lượng cao, cần API key)
EMBED_PROVIDER = "openai"

# Dùng local model (miễn phí, offline, không cần API key)
# EMBED_PROVIDER = "local"
```

| Provider | Model | API Key | Chất lượng | Offline |
|---|---|---|---|---|
| `openai` | text-embedding-3-small | ✅ Cần | Rất cao | ❌ |
| `local` | paraphrase-multilingual-MiniLM-L12-v2 | ❌ Không cần | Tốt | ✅ |

### Chọn LLM provider

```python
LLM_PROVIDER = "openai"
# LLM_PROVIDER = "deepseek"
# LLM_PROVIDER = "anthropic"
```

| Provider | Model | Giá/1M tokens | Tiếng Việt |
|---|---|---|---|
| `openai` | gpt-4o-mini | ~$0.15 | Tốt |
| `deepseek` | deepseek-chat | ~$0.07 | Tốt |
| `anthropic` | claude-3-5-haiku | ~$0.25 | Rất tốt |

> ⚠️ **Quan trọng:** `EMBED_PROVIDER` phải giống nhau khi chạy `index.py` và `query.py`.  
> Nếu index bằng `local` thì query cũng phải dùng `local`, không được trộn lẫn.

---

## Hướng dẫn sử dụng

### Bước 1 — Crawl website

```bash
python crawl.py https://your-website.com
```

| Flag | Mô tả | Default |
|------|-------|---------|
| `--limit` | Số trang tối đa | `500` |
| `--api-key` | Firecrawl API key | env var |

**Output:** Các file `.md` trong `./data/`

---

### Bước 2 — Chunk markdown

```bash
python chunk.py
```

Tự động đọc toàn bộ `./data/*.md`. Cấu hình `CHUNK_SIZE` và `OVERLAP` trong `config.py`.

**Output:** `./chunks/chunks.json`

---

### Bước 3 — Index vào ChromaDB

```bash
# Chỉ index chunks mới
python index.py

# Force re-index toàn bộ
python index.py --force

# Truyền API key trực tiếp
python index.py --openai-key your_key
```

**Output:** Vector database tại `./chroma_db/`

---

### Bước 4 — Query & nhận câu trả lời

```bash
# Hỏi 1 câu
python query.py "Sản phẩm của bạn có những loại nào?"

# Xem chunks được retrieve
python query.py "Sản phẩm của bạn có những loại nào?" --verbose

# Interactive mode — chat liên tục
python query.py

# Truyền API key trực tiếp
python query.py "..." --openai-key your_key --llm-key your_llm_key
```

| Flag | Mô tả | Default |
|------|-------|---------|
| `--openai-key` | OpenAI API key (embedding) | `OPENAI_API_KEY` env |
| `--llm-key` | LLM provider API key | `LLM_API_KEY` env |
| `--verbose` | Hiển thị chunks + score | `false` |

---

## Kịch bản triển khai

### Kịch bản 1 — Dùng hoàn toàn OpenAI

```bash
export OPENAI_API_KEY=your_openai_key
export FIRECRAWL_API_KEY=your_firecrawl_key
```

```python
# config.py
EMBED_PROVIDER = "openai"
LLM_PROVIDER   = "openai"
```

---

### Kịch bản 2 — Embedding local + DeepSeek LLM (tiết kiệm nhất)

```bash
export FIRECRAWL_API_KEY=your_firecrawl_key
export LLM_API_KEY=your_deepseek_key
# Không cần OPENAI_API_KEY
```

```python
# config.py
EMBED_PROVIDER = "local"
LLM_PROVIDER   = "deepseek"
```

```bash
pip install sentence-transformers
```

---

### Kịch bản 3 — Embedding local + Anthropic LLM (tiếng Việt tốt nhất)

```bash
export FIRECRAWL_API_KEY=your_firecrawl_key
export LLM_API_KEY=your_anthropic_key
# Không cần OPENAI_API_KEY
```

```python
# config.py
EMBED_PROVIDER = "local"
LLM_PROVIDER   = "anthropic"
```

```bash
pip install sentence-transformers anthropic
```

---

## Chạy toàn bộ pipeline

```bash
python crawl.py https://your-website.com --limit 200
python chunk.py
python index.py
python query.py "Câu hỏi của bạn"
```

---

## Cập nhật khi website thay đổi

```bash
# Crawl lại → chunk lại → chỉ index chunks mới
python crawl.py https://your-website.com
python chunk.py
python index.py
```

---

## Optional: Dùng file `.env`

```bash
pip install python-dotenv
```

```env
FIRECRAWL_API_KEY=your_firecrawl_key
OPENAI_API_KEY=your_openai_key
LLM_API_KEY=your_llm_key
```

```python
# Thêm vào đầu mỗi file .py
from dotenv import load_dotenv
load_dotenv()
```

```bash
echo ".env" >> .gitignore
```

---

## Chi phí ước tính

### Embedding — chạy 1 lần khi index

| Provider | Model | Chi phí |
|---|---|---|
| OpenAI | text-embedding-3-small | ~$0.02/1M tokens |
| Local | sentence-transformers | Miễn phí |

### LLM — mỗi câu hỏi

| Provider | Model | Chi phí/query |
|---|---|---|
| OpenAI | gpt-4o-mini | ~$0.002 |
| DeepSeek | deepseek-chat | ~$0.001 |
| Anthropic | claude-3-5-haiku | ~$0.003 |

---

## Troubleshooting

### ❌ `Collection not found`
```
Chạy index.py trước khi chạy query.py
```

### ❌ `No markdown files found`
```
Chạy crawl.py trước khi chạy chunk.py
```

### ❌ `OpenAI API key is required`
```
Set EMBED_PROVIDER = "local" trong config.py
Hoặc export OPENAI_API_KEY=your_key
```

### ❌ `Module sentence_transformers not found`
```
pip install sentence-transformers
```

### ❌ `Module anthropic not found`
```
pip install anthropic
```

### ❌ `Rate limit error` (OpenAI)
```
Giảm BATCH_SIZE trong index.py xuống 50
Tăng SLEEP_BETWEEN lên 1.0
```

### ❌ Câu trả lời không chính xác
```
Giảm CHUNK_SIZE xuống 800 trong config.py
Tăng TOP_K lên 7 trong config.py
Kiểm tra data/ có đủ nội dung không
```

---

## Tech Stack

| Component | Tool |
|---|---|
| Crawling | Firecrawl |
| Embedding | OpenAI text-embedding-3-small / sentence-transformers (local) |
| Vector DB | ChromaDB |
| LLM | OpenAI gpt-4o-mini / DeepSeek deepseek-chat / Anthropic claude-3-5-haiku |
| Language | Python 3.10+ |

---

## License

MIT License — Free to use and modify.

---

*Built for OpenClaw AI Agent — Website Knowledge RAG*
