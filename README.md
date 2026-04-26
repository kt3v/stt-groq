# STT Groq

Minimal speech-to-text web app powered by [Groq](https://groq.com) Whisper API — free, real-time, open source.

- **Backend:** FastAPI + Groq SDK (`whisper-large-v3`)
- **Frontend:** Vanilla JS/HTML/CSS, ~3 KB, zero dependencies
- **Record → Transcribe → Copy** — that's it

## Quick Start

```bash
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
uvicorn main:app --reload
```

Open http://localhost:8000

Get a free API key at [console.groq.com](https://console.groq.com).

## How It Works

1. **Record** — browser captures audio via `MediaRecorder`
2. **Stop** — audio sent to `POST /api/transcribe`
3. Groq Whisper returns text → displayed in textarea
4. **Copy** — copies to clipboard

## License

MIT