"""STT Groq — FastAPI backend with Groq Whisper."""

import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="STT Groq")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY env var is required")

client = Groq(api_key=GROQ_API_KEY)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...), language: str = Form("auto")):
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(400, "Only audio files are accepted")

    suffix = Path(file.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        try:
            tmp.write(await file.read())
            tmp.flush()

            kwargs = dict(model="whisper-large-v3", file=None, response_format="json")
            if language != "auto":
                kwargs["language"] = language

            with open(tmp.name, "rb") as audio:
                kwargs["file"] = audio
                transcript = client.audio.transcriptions.create(**kwargs)

            return JSONResponse({"text": transcript.text})
        except Exception as e:
            raise HTTPException(500, str(e))
        finally:
            os.unlink(tmp.name)