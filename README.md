# WebBot — Intelligent Web Scraping Chatbot

Scrape websites → build a knowledge base → chat with your data.

## Architecture

```
project/
├── app/
│   ├── main.py               # FastAPI app entry point
│   ├── cache.py              # URL ingestion cache (JSON-based)
│   ├── routers/
│   │   ├── scrape.py         # POST /scrape/start, GET /scrape/status/:id
│   │   ├── chat.py           # POST /chat/ask
│   │   └── knowledge.py      # GET /knowledge/summary, /faqs, /export/markdown
│   └── services/
│       ├── ingestion.py      # Markdown → ChromaDB vector store + LLM summarization
│       └── chatbot.py        # RetrievalQA chain with Claude
├── scraping/                 # Scrapy project (from your teammates)
│   └── scraping/
│       ├── spiders/__init__.py  # URLScraper spider
│       ├── pipelines.py         # MarkdownConversionPipeline
│       ├── items.py
│       └── settings.py
├── frontend/
│   └── src/App.jsx           # React UI (3 tabs: Scrape, Chat, Knowledge)
├── requirements.txt
└── .env.example
```

## Setup

### 1. Clone / arrange files

```
project/
├── app/
├── scraping/     ← your teammates' Scrapy project goes here
├── frontend/
└── requirements.txt
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set API key

Get a **free** Groq API key at https://console.groq.com (no credit card required).

```bash
cp .env.example .env
# Edit .env and add your Groq API key:
# GROQ_API_KEY=gsk_...
```

### 5. Load environment variables

```bash
export $(cat .env | xargs)      # Linux/macOS
# Windows PowerShell:
# Get-Content .env | ForEach-Object { $k,$v = $_ -split '='; [System.Environment]::SetEnvironmentVariable($k,$v) }
```

## Running the Backend

```bash
# From the project root
uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

## Running the Frontend

The React component in `frontend/src/App.jsx` can be used in any React app
or rendered via Claude's artifact viewer. It connects to `http://localhost:8000`.

For a quick standalone setup with Vite:

```bash
cd frontend
npm create vite@latest . -- --template react
# Replace src/App.jsx with the provided file
npm install
npm run dev
```

## API Reference

### Scraping

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/scrape/start` | Start scraping URLs (runs in background) |
| GET | `/scrape/status/{job_id}` | Poll job status |
| GET | `/scrape/ingested` | List all ingested URLs |
| DELETE | `/scrape/ingested/{url}` | Remove URL from cache |

**POST /scrape/start body:**
```json
{
  "urls": ["https://example.com", "https://docs.example.com"],
  "force": false
}
```

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/ask` | Ask a question about ingested content |

**POST /chat/ask body:**
```json
{
  "query": "What is this website about?",
  "language": "en"
}
```

### Knowledge

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/knowledge/summary` | AI-generated summary of scraped content |
| GET | `/knowledge/faqs` | Auto-generated FAQ list (JSON) |
| GET | `/knowledge/export/markdown` | Download summary + FAQs as Markdown |
| GET | `/knowledge/raw` | Raw KnowledgeBase.md content (first 5000 chars) |
| POST | `/knowledge/reingest` | Re-run ingestion from existing KnowledgeBase.md |

## How It Works

1. **Scrape**: You submit URLs → FastAPI runs Scrapy in a background task → spider crawls pages (depth 2, max 50 pages), extracts clean text → writes to `KnowledgeBase.md`

2. **Ingest**: The markdown is split into 800-character chunks → each chunk is embedded using `sentence-transformers/all-MiniLM-L6-v2` (runs locally, no API key) → stored in ChromaDB on disk

3. **Chat**: Your query is embedded → top 4 similar chunks are retrieved → Claude (via LangChain) uses those chunks as context to answer your question

4. **Knowledge**: Claude reads the KnowledgeBase and generates summaries and FAQ pairs

## Features Implemented

### Compulsory
- [x] Accept one or more URLs
- [x] Extract and clean text (Scrapy with deduplication, noise filtering)
- [x] Summarize content using Claude
- [x] Generate vector embeddings (sentence-transformers) + store in ChromaDB
- [x] Chatbot interface for Q&A (FastAPI backend + React frontend)

### Additional
- [x] Auto-detect and follow internal links (Scrapy LinkExtractor)
- [x] Generate FAQs from scraped data
- [x] Export summaries as Markdown

### Bonus
- [x] Multi-lingual chat responses (pass `language` param)
- [ ] Live website update (can be added with a scheduled job)
- [ ] Admin dashboard (basic management via API + UI)

## Notes

- The scraper respects `robots.txt` and uses a 1-second download delay by default
- ChromaDB persists to `./chroma_db/` — delete this folder to reset the vector store
- URL ingestion status is cached in `./ingested_urls.json`
- KnowledgeBase is written to `./KnowledgeBase.md` in the project root
- Scraping is limited to 50 pages and depth 2 per run (configurable in spider settings)
