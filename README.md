# STT Groq

Minimal speech-to-text web app powered by [Groq](https://groq.com) Whisper API — free, real-time, open source.

- **Backend:** FastAPI + Groq SDK (`whisper-large-v3`)
- **Frontend:** Vanilla JS/HTML/CSS, single file, zero dependencies
- **Record → Transcribe → Correct → Copy**

## Features

- Real-time audio recording via browser `MediaRecorder`
- Transcription via Groq Whisper `whisper-large-v3`
- Language auto-detection or explicit selection
- Optional password protection (`APP_PASSWORD`) with session tokens
- Custom LLM text correction via MiniMax (`MiniMax-M2.7`) with user-defined prompts
- Persistent prompt management (create / delete) stored in `prompts.json`
- Keyboard shortcuts: `Space` to toggle recording, `C` to copy (layout-independent)
- One-click copy to clipboard

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your keys
uvicorn main:app --reload
```

Open http://localhost:8000

Get a free Groq API key at [console.groq.com](https://console.groq.com).

## Environment

Create `.env` in the project root:

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | yes | Groq API key for Whisper transcriptions |
| `MINIMAX_API_KEY` | no | MiniMax API key for LLM text correction |
| `APP_PASSWORD` | no | If set, protects transcribe and correct endpoints |

## How It Works

1. **Record** — browser captures audio via `MediaRecorder`
2. **Stop** — audio sent to `POST /api/transcribe`
3. Groq Whisper returns text → displayed in textarea
4. **Correct** — optional LLM post-processing via custom prompts (`POST /api/correct`)
5. **Copy** — copies to clipboard

## License

MIT
