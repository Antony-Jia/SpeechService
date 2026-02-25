from __future__ import annotations

import base64
import tempfile
import threading
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask

from speech_service.config import Settings, get_settings

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SpeechTTSRequest(BaseModel):
    text: str
    voice: str | None = None


class STTRequest(BaseModel):
    audioBase64: str
    mimeType: str
    language: str | None = None


class STTResponse(BaseModel):
    text: str


# ---------------------------------------------------------------------------
# STT helpers
# ---------------------------------------------------------------------------

_stt_lock = threading.Lock()
_stt_model = None
_stt_model_name: str | None = None
_stt_model_device: str | None = None


def _normalize_mime(mime: str) -> str:
    return mime.split(";", 1)[0].strip().lower()


_MIME_SUFFIX = {
    "audio/webm": ".webm",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
}


def _mime_to_suffix(mime: str) -> str:
    return _MIME_SUFFIX.get(mime, ".audio")


def _strip_data_url(value: str) -> str:
    if value.startswith("data:") and "," in value:
        return value.split(",", 1)[1]
    return value


def _get_stt_model(settings: Settings):
    global _stt_model, _stt_model_name, _stt_model_device
    with _stt_lock:
        if _stt_model is None or _stt_model_name != settings.whisper_model_name:
            import whisper
            device = settings.device if settings.device else None
            _stt_model = whisper.load_model(
                settings.whisper_model_name,
                device=device,
                download_root=str(settings.whisper_model_dir),
            )
            _stt_model_name = settings.whisper_model_name
            _stt_model_device = settings.device
    return _stt_model


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="Speech Service")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve voice WAV files for preview
    voices_dir = settings.voices_dir
    voices_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/voices", StaticFiles(directory=str(voices_dir)), name="voices")

    # Temp dir for TTS output files
    _speech_dir = Path(tempfile.gettempdir()) / "speech_service_tts"
    _speech_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # TTS endpoint  POST /api/speech/tts
    # ------------------------------------------------------------------

    @app.post("/api/speech/tts")
    def speech_tts(
        req: SpeechTTSRequest,
        s: Settings = Depends(get_settings),
    ):
        text = (req.text or "").strip()
        if not text:
            return PlainTextResponse("text is required", status_code=400)

        from speech_service.tts_engine import list_voices, resolve_voice, synthesize

        voices = list_voices(s)
        if not voices:
            return PlainTextResponse(
                "No voice files found. Please add .wav files to the voices/ directory.",
                status_code=404,
            )

        voice_path = resolve_voice(req.voice, s)
        if voice_path is None:
            if req.voice:
                return PlainTextResponse(f"voice not found: {req.voice}", status_code=404)
            return PlainTextResponse("No voice files available", status_code=404)

        out_path = _speech_dir / f"{uuid.uuid4().hex}.wav"

        try:
            synthesize(text=text, voice_path=voice_path, output_path=out_path, settings=s)
        except Exception as exc:
            out_path.unlink(missing_ok=True)
            return PlainTextResponse(str(exc), status_code=500)

        return FileResponse(
            path=str(out_path),
            media_type="audio/wav",
            filename="tts.wav",
            background=BackgroundTask(lambda p: p.unlink(missing_ok=True), out_path),
        )

    # ------------------------------------------------------------------
    # Voices list  GET /api/voices
    # ------------------------------------------------------------------

    @app.get("/api/voices")
    def api_voices(s: Settings = Depends(get_settings)):
        from speech_service.tts_engine import list_voices
        return list_voices(s)

    # ------------------------------------------------------------------
    # STT endpoint  POST /stt
    # ------------------------------------------------------------------

    @app.post("/stt", response_model=STTResponse)
    def stt(req: STTRequest, s: Settings = Depends(get_settings)):
        audio_base64 = (req.audioBase64 or "").strip()
        if not audio_base64:
            return PlainTextResponse("audioBase64 is required", status_code=400)
        if not req.mimeType:
            return PlainTextResponse("mimeType is required", status_code=400)

        mime = _normalize_mime(req.mimeType)
        suffix = _mime_to_suffix(mime)

        try:
            raw = base64.b64decode(_strip_data_url(audio_base64), validate=False)
        except Exception as exc:
            return PlainTextResponse(f"invalid audioBase64: {exc}", status_code=400)

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
                tf.write(raw)
                temp_path = Path(tf.name)

            model = _get_stt_model(s)
            result = model.transcribe(str(temp_path), language=req.language or None)
            text = (result.get("text") or "").strip()
            return STTResponse(text=text)
        except Exception as exc:
            return PlainTextResponse(str(exc), status_code=500)
        finally:
            if temp_path:
                temp_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    s = get_settings()
    uvicorn.run(app, host=s.host, port=s.port)
