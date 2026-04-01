# OpenClaw Website Knowledge RAG -- Basic Implementation Guide

## Mục tiêu

Cho OpenClaw AI Agent có thể trả lời mọi nội dung từ website bằng cách:
Crawl → Chunk → Embedding → Vector DB → Query

Thiết kế này tối giản, dễ triển khai, ít dependency.

------------------------------------------------------------------------

# Overall Flow

Website → Firecrawl (crawl HTML) → Markdown files → Chunk text → Create
embeddings → Store in ChromaDB → OpenClaw query → LLM answer

------------------------------------------------------------------------

# Tech stack sử dụng (đơn giản nhất)

## Crawl

Firecrawl

## Processing

Python

## Embedding

OpenAI text-embedding-3-small

## Vector Database

ChromaDB

## Agent layer

OpenClaw

------------------------------------------------------------------------

# Folder structure đề xuất

project/

data/ page1.md page2.md

crawl.py chunk.py index.py query.py

------------------------------------------------------------------------

# Step 1 -- Crawl website

## Install

pip install firecrawl-py

## Basic crawl

Firecrawl crawl website và convert sang markdown.

Config nên dùng:

formats = markdown onlyMainContent = true limit = 500

## Output mong muốn

/data

page1.md page2.md

------------------------------------------------------------------------

# Step 2 -- Chunk markdown

## Mục tiêu

Chia text lớn thành đoạn nhỏ để embedding chính xác.

## Recommended config

chunk size: 800--1200 characters overlap: 100--200

## Rule quan trọng

Không chunk quá lớn. Không chunk quá nhỏ.

Optimal: \~1000 characters

## Simple chunk logic

Sliding window:

start → size → overlap back → next chunk

------------------------------------------------------------------------

# Step 3 -- Create embeddings

## Install

pip install openai

## Model nên dùng

text-embedding-3-small

Lý do:

Rẻ Nhanh Đủ tốt cho RAG basic

## Data cần lưu:

embedding vector chunk text source file

------------------------------------------------------------------------

# Step 4 -- Store in Vector DB

## Install Chroma

pip install chromadb

## Lưu:

embedding document text metadata

Metadata nên có:

source file url (nếu có) title (optional)

------------------------------------------------------------------------

# Step 5 -- Query flow

User question → embed question → vector search top 3--5 → build context
→ send to LLM → answer

------------------------------------------------------------------------

# Query strategy đơn giản

top_k = 3 hoặc 5

Không cần reranker.

Không cần hybrid search.

------------------------------------------------------------------------

# Minimal working pipeline

## Ingestion pipeline

crawl.py

Firecrawl crawl → save markdown

chunk.py

Read markdown → split chunks

index.py

Embedding → store Chroma

## Serving pipeline

query.py

Embed question → vector search → send context to LLM

------------------------------------------------------------------------

# Important notes

## Không embed raw HTML

Luôn convert markdown trước.

## Không lưu chunk quá lớn

Sai:

5000+ characters

Đúng:

\~1000

## Không cần JSON trung gian

Có thể lưu thẳng vector DB.

JSON chỉ để debug.

## Context size

Top 3--5 chunks đủ.

Không cần nhiều.

## Re-index khi website update

Chỉ crawl lại pages thay đổi.

Không cần reindex toàn bộ.

------------------------------------------------------------------------

# Performance tips

## Chunk quality quan trọng hơn model

Chunk đúng → RAG tốt.

## Context clean

Firecrawl onlyMainContent = true.

## Metadata

Luôn lưu source.

Để trace answer.

------------------------------------------------------------------------

# Final architecture

Firecrawl → Markdown → Chunk → Embedding → ChromaDB → OpenClaw retrieval
→ LLM answer

------------------------------------------------------------------------

# Kết luận

Đây là RAG basic production starter.

Ưu điểm:

Dễ build Ít code Ít infra Scale được

Đủ cho:

Website knowledge bot Product assistant Internal docs AI
