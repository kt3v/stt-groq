"""STT Groq — FastAPI backend with Groq Whisper and MiniMax LLM correction."""

import json
import os
import re
import secrets
import tempfile
import uuid
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from groq import Groq
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="STT Groq")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY env var is required")

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
_sessions: set[str] = set()

MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = "https://api.minimax.io/v1"
MINIMAX_MODEL = "MiniMax-M2.7"

groq_client = Groq(api_key=GROQ_API_KEY)

STATIC_DIR = Path(__file__).parent / "static"
PROMPTS_FILE = Path(__file__).parent / "prompts.json"


def _load_prompts() -> list:
    if PROMPTS_FILE.exists():
        return json.loads(PROMPTS_FILE.read_text(encoding="utf-8"))
    return []


def _save_prompts(prompts: list) -> None:
    PROMPTS_FILE.write_text(
        json.dumps(prompts, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class AuthRequest(BaseModel):
    password: str


class PromptCreate(BaseModel):
    prompt: str


class CorrectRequest(BaseModel):
    text: str
    prompt: str


async def _require_auth(x_session_token: str = Header(None)) -> None:
    if not APP_PASSWORD:
        return
    if not x_session_token or x_session_token not in _sessions:
        raise HTTPException(401, "Unauthorized")


@app.post("/api/auth")
async def authenticate(body: AuthRequest):
    if not APP_PASSWORD:
        return {"token": ""}
    if body.password != APP_PASSWORD:
        raise HTTPException(401, "Wrong password")
    token = secrets.token_hex(32)
    _sessions.add(token)
    return {"token": token}


@app.get("/api/auth/status")
async def auth_status(x_session_token: str = Header(None)):
    if not APP_PASSWORD:
        return {"ok": True}
    if x_session_token and x_session_token in _sessions:
        return {"ok": True}
    raise HTTPException(401, "Unauthorized")


@app.get("/")
async def index():
    return HTMLResponse((STATIC_DIR / "index.html").read_text())


@app.get("/manifest.json")
async def manifest():
    return FileResponse(STATIC_DIR / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
async def service_worker():
    return FileResponse(STATIC_DIR / "sw.js", media_type="application/javascript")


@app.get("/icon.svg")
async def icon():
    return FileResponse(STATIC_DIR / "icon.svg", media_type="image/svg+xml")


@app.post("/api/transcribe", dependencies=[Depends(_require_auth)])
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
                transcript = groq_client.audio.transcriptions.create(**kwargs)

            return JSONResponse({"text": transcript.text})
        except Exception as e:
            raise HTTPException(500, str(e))
        finally:
            os.unlink(tmp.name)


@app.get("/api/prompts")
async def get_prompts():
    return _load_prompts()


@app.post("/api/prompts")
async def create_prompt(body: PromptCreate):
    prompt_text = body.prompt.strip()
    if not prompt_text:
        raise HTTPException(400, "prompt is required")
    words = prompt_text.split()
    label = words[0] if words else prompt_text
    prompts = _load_prompts()
    item = {"id": str(uuid.uuid4()), "label": label, "prompt": prompt_text}
    prompts.append(item)
    _save_prompts(prompts)
    return item


@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    prompts = [p for p in _load_prompts() if p["id"] != prompt_id]
    _save_prompts(prompts)
    return {"ok": True}


@app.post("/api/correct", dependencies=[Depends(_require_auth)])
async def correct_text(body: CorrectRequest):
    text = body.text.strip()
    prompt_text = body.prompt.strip()
    if not text:
        raise HTTPException(400, "text is required")
    if not prompt_text:
        raise HTTPException(400, "prompt is required")
    if not MINIMAX_API_KEY:
        raise HTTPException(500, "MINIMAX_API_KEY not configured")

    async with httpx.AsyncClient() as http:
        try:
            r = await http.post(
                f"{MINIMAX_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {MINIMAX_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MINIMAX_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a text processing assistant. "
                                "Output ONLY the result of the requested operation — "
                                "no explanations, no preamble, no quotes, no labels like "
                                "'Here is the translation:' or 'Result:'. "
                                "Return the processed text and nothing else."
                            ),
                        },
                        {"role": "user", "content": f"{prompt_text}\n\n{text}"},
                    ],
                },
                timeout=30.0,
            )
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(502, f"MiniMax error: {e.response.text}")
        except Exception as e:
            raise HTTPException(502, str(e))

    result = r.json()
    corrected = result["choices"][0]["message"]["content"]
    corrected = re.sub(r"<think>.*?</think>", "", corrected, flags=re.DOTALL).strip()
    return {"text": corrected}
