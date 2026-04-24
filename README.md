# LUMI v2 - AI-Powered Knowledge Assistant with RAG

A production-grade backend for an intelligent document retrieval and chat system powered by Retrieval-Augmented Generation (RAG).

## 📋 Project Status

**Completed Modules (1-6.5):**
- ✅ **Module 1**: FastAPI setup, health/status endpoints, core infrastructure
- ✅ **Module 2**: Supabase JWT authentication (signup, login, user validation)
- ✅ **Module 3**: Qdrant vector database integration, LlamaIndex setup, payload indexing
- ✅ **Module 4**: Multi-format file upload (PDF/DOCX/TXT), text extraction, chunking, embedding
- ✅ **Module 5**: LlamaIndex-powered retrieval, Groq LLM generation, source citations
- ✅ **Module 6**: Document management (list, delete, reprocess)
- ✅ **Module 6 Hardening**: Pagination, soft-delete, reprocess job tracking
- ✅ **Module 6.5**: Raw file storage to Supabase Storage, storage_path persistence

**Planned Modules:**
- ⏳ YouTube URL ingestion
- ⏳ Website URL ingestion
- ⏳ Chat history persistence
- ⏳ OCR support
- ⏳ Advanced analytics

## 🏗️ Architecture

```
Backend (FastAPI)
├── Auth Service (Supabase JWT)
├── File Ingestion Service
│   ├── Text extraction (PDF, DOCX, TXT)
│   ├── Chunk generation (1000 chars, 150 overlap)
│   ├── Embedding (HuggingFace all-MiniLM)
│   └── Storage (Qdrant + Supabase)
├── RAG Service
│   ├── Vector retrieval (Qdrant filtered by user_id)
│   ├── LLM generation (Groq llama-3.1-8b)
│   └── Source attribution
└── Document Management
    ├── Pagination (page, page_size, total, has_next)
    ├── Soft-delete (is_deleted, deleted_at)
    └── Reprocess pipeline
```

## 🚀 Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | 0.115.6 |
| Server | Uvicorn | 0.32.1 |
| Vector DB | Qdrant | 1.12.1 |
| RAG Framework | LlamaIndex | 0.12.5 |
| LLM | Groq (llama-3.1-8b) | latest |
| Embeddings | HuggingFace (all-MiniLM-L6-v2) | 384-dim |
| Auth | Supabase | 2.11.0 |
| File Storage | Supabase Storage | included |
| Validation | Pydantic | 2.10.4 |
| Logging | Loguru | latest |

## 📦 Installation

### Prerequisites
- Python 3.12+
- Supabase project (auth + storage)
- Qdrant instance (cloud or local)
- Groq API key

### Setup

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/lumi-v2.git
   cd lumi-v2/lumi-v2-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-anon-key
   QDRANT_URL=https://your-qdrant-instance.qdrant.io
   QDRANT_API_KEY=your-api-key
   GROQ_API_KEY=your-groq-key
   ```

5. **Start server**
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```

6. **Access API**
   - Docs: http://127.0.0.1:8000/docs
   - Health: http://127.0.0.1:8000/health

## 📚 API Endpoints

### Authentication
- `POST /api/v1/auth/signup` - Register new user
- `POST /api/v1/auth/login` - Login user
- `GET /api/v1/auth/me` - Get current user (Bearer token required)

### Document Upload
- `POST /api/v1/upload/file` - Upload PDF/DOCX/TXT (multipart, Bearer token required)

### Chat/RAG
- `POST /api/v1/chat/ask` - Query with RAG retrieval + LLM generation (Bearer token required)

### Document Management
- `GET /api/v1/documents/` - List user documents (paginated, Bearer token required)
  - Query params: `page=1`, `page_size=10`, `include_deleted=false`
- `DELETE /api/v1/documents/{document_id}` - Soft-delete document (Bearer token required)
- `POST /api/v1/documents/{document_id}/reprocess` - Reprocess document (Bearer token required)

## 🧪 Testing

### Quick Test Flow
```bash
# 1. Signup
curl -X POST http://127.0.0.1:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'

# 2. Login (get token)
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass123"}'

# 3. Upload file
curl -X POST http://127.0.0.1:8000/api/v1/upload/file \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"

# 4. Ask question
curl -X POST http://127.0.0.1:8000/api/v1/chat/ask \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is in my document?"}'

# 5. List documents
curl -X GET "http://127.0.0.1:8000/api/v1/documents/?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🔧 Configuration

All settings controlled via `.env` file (see `app/core/config.py`):
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR
- `CHUNK_SIZE_CHARS`: Text chunk size (default: 1000)
- `CHUNK_OVERLAP_CHARS`: Chunk overlap (default: 150)
- `RETRIEVAL_TOP_K`: Max chunks to retrieve (default: 5)
- `UPLOAD_MAX_FILE_SIZE_MB`: Max file size (default: 20 MB)

## 📝 Project Structure

```
lumi-v2-backend/
├── app/
│   ├── main.py                 # FastAPI app, startup hooks
│   ├── core/
│   │   ├── config.py          # Settings (pydantic-settings)
│   │   ├── logger.py          # Loguru configuration
│   │   └── security.py        # JWT validation, HTTPBearer
│   ├── api/
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── upload.py          # File upload endpoint
│   │   ├── chat.py            # Chat/RAG endpoint
│   │   ├── documents.py       # Document management
│   │   ├── youtube.py         # YouTube ingestion (scaffolded)
│   │   └── website.py         # Website ingestion (scaffolded)
│   ├── services/
│   │   ├── auth_service.py    # Supabase auth logic
│   │   ├── ingestion_service.py # File parsing, embedding, storage
│   │   └── rag_service.py     # LlamaIndex retrieval + Groq generation
│   ├── schemas/
│   │   ├── auth.py            # Auth request/response models
│   │   ├── upload.py          # Upload response model
│   │   ├── chat.py            # Chat request/response models
│   │   └── documents.py       # Document models, pagination
│   └── integrations/
│       ├── supabase.py        # Supabase client, storage
│       ├── qdrant.py          # Qdrant operations, collection bootstrap
│       ├── llamaindex.py      # LlamaIndex context, embeddings
│       └── groq.py            # Groq client
├── requirements.txt            # Pinned dependencies
├── .env.example               # Environment template
└── uvicorn.out.log           # Server logs

```

## 🔐 Security

- ✅ JWT Bearer token authentication on all user endpoints
- ✅ User ID isolation in Qdrant payloads (filters prevent cross-user data access)
- ✅ Soft-delete model (no data loss, audit trail ready)
- ✅ Supabase RLS policies (future: enforce at database level)
- ✅ File upload size limits (default: 20 MB)
- ✅ Supported file types only (PDF, DOCX, TXT)

## 🐛 Known Limitations

- Supabase Storage bucket creation requires elevated permissions (non-critical startup warning)
- No chat history persistence yet (Module 7+)
- YouTube/website ingestion scaffolded but not implemented
- OCR support planned for Module 8+

## 📈 Performance Metrics

- Embedding generation: ~1-2s per 1000-char chunk (HuggingFace all-MiniLM)
- Vector search: <100ms (Qdrant optimized filters)
- LLM generation: ~2-5s (Groq llama-3.1-8b via API)
- Pagination: O(log n) on Qdrant scroll
- File parse to storage: <5s for typical PDF (tested with 5MB files)

## 🚢 Deployment

### Railway / Render
```bash
git push heroku main  # or railway/render equivalent
```

### Docker (future)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 📋 Next Steps (Module 7+)

1. **YouTube ingestion** - Parse transcripts, chunk, embed, store
2. **Website crawling** - Extract content, chunk, embed
3. **Chat history** - Persist conversations in Supabase
4. **Advanced search** - Hybrid BM25 + vector search
5. **OCR** - Scanned document support

## 🤝 Contributing

TBD - Internal development mode

## 📄 License

TBD

---

**Last Updated**: April 24, 2026  
**Version**: 0.1.0 (Pre-release)  
**Maintainer**: Nehal Mishra
