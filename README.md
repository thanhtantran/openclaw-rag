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
                                      └─► query.py (OpenAI LLM)
                                            └─► Answer ✓
```

---

## Yêu cầu hệ thống

- Python **3.10+**
- OpenAI API key → [platform.openai.com](https://platform.openai.com)
- Firecrawl API key → [firecrawl.dev](https://firecrawl.dev)

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
pip install firecrawl-py openai chromadb
```

### 4. Set API keys

```bash
# Linux / macOS
export FIRECRAWL_API_KEY=your_firecrawl_key
export OPENAI_API_KEY=your_openai_key

# Windows (Command Prompt)
set FIRECRAWL_API_KEY=your_firecrawl_key
set OPENAI_API_KEY=your_openai_key
```

> 💡 Hoặc tạo file `.env` và load bằng `python-dotenv` (xem phần Optional bên dưới)

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

# Re-index toàn bộ
python index.py --force
```

**Output:** Vector database tại `./chroma_db/`

---

### Bước 4 — Query & nhận câu trả lời

```bash
# Hỏi 1 câu
python query.py "Sản phẩm của bạn có những loại nào?"

# Hỏi với verbose (xem chunks được retrieve)
python query.py "Sản phẩm của bạn có những loại nào?" --verbose

# Interactive mode — chat liên tục
python query.py
```

**Tùy chọn:**

| Flag | Mô tả | Default |
|------|-------|---------|
| `--top-k` | Số chunks retrieve | `5` |
| `--verbose` | Hiển thị chunks + score | `false` |
| `--api-key` | OpenAI API key | env var |

---

## Chạy toàn bộ pipeline (1 lần)

```bash
# Set keys
export FIRECRAWL_API_KEY=your_firecrawl_key
export OPENAI_API_KEY=your_openai_key

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

## Chi phí ước tính (OpenAI)

> Model: `text-embedding-3-small` + `gpt-4o-mini`

| Website size | Số trang | Chunks ước tính | Chi phí index | Chi phí/query |
|---|---|---|---|---|
| Nhỏ | ~50 | ~500 | ~$0.01 | ~$0.001 |
| Vừa | ~200 | ~2,000 | ~$0.04 | ~$0.002 |
| Lớn | ~500 | ~5,000 | ~$0.10 | ~$0.003 |

> 💡 `text-embedding-3-small` = $0.02 / 1M tokens  
> 💡 `gpt-4o-mini` = $0.15 / 1M input tokens

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

### ❌ Câu trả lời không chính xác
```
Giảm CHUNK_SIZE xuống 800
Tăng --top-k lên 7
Kiểm tra data/ có đủ nội dung không
```

---

## Tech Stack

| Component | Tool | Version |
|---|---|---|
| Crawling | Firecrawl | latest |
| Embedding | OpenAI text-embedding-3-small | - |
| Vector DB | ChromaDB | latest |
| LLM | OpenAI gpt-4o-mini | - |
| Language | Python | 3.10+ |

---

## License

MIT License — Free to use and modify.

---

*Built for OpenClaw AI Agent — Website Knowledge RAG*
