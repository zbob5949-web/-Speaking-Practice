# SpeakMate backend v2

Run from `app/backend`:

```bash
python -m pip install -r requirements-enhanced.txt
uvicorn app.enhanced_main_v2:app --reload --host 0.0.0.0 --port 8000
```

The mobile-ready entry point composes the original API and replaces only
`POST /api/sessions/turn`. It adds six curated scenarios, twelve deterministic
grammar rules, local LangChain-compatible RAG citations, deduplicated round
reports, bounded dynamic difficulty, durable weakness memory, and targeted
exercises. The fake provider works without an API key. ASR/TTS remain separate
so the future Android shell can replace those adapters without changing the
learning API.
