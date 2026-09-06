from __future__ import annotations

import io
import os
import threading
from pathlib import Path

import soundfile as sf
import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from qwen_tts import Qwen3TTSModel


MODEL_PATH = Path(os.environ.get("QWEN3_TTS_MODEL_DIR", str(Path.home() / "models" / "Qwen3-TTS-12Hz-1.7B-CustomVoice"))).expanduser()
SUPPORTED_SPEAKERS = {"Vivian", "Serena", "Ono_Anna", "Sohee"}
LANGUAGE_MAP = {"zh": "Chinese", "ja": "Japanese", "en": "English"}
DEFAULT_MAX_NEW_TOKENS = 192
MAX_REQUESTS_PER_PROCESS = 24

app = FastAPI(title="Qwen3-TTS CustomVoice Local Service")
_model: Qwen3TTSModel | None = None
_model_lock = threading.Lock()
_completed_requests = 0


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3000)
    speaker: str
    language: str = "zh"
    instruct: str = "Clean studio recording, clear articulation, no whisper, no reverb."
    seed: int = 20260824
    top_p: float = Field(default=0.85, ge=0.1, le=1.0)
    temperature: float = Field(default=0.72, ge=0.1, le=1.5)
    repetition_penalty: float = Field(default=1.1, ge=1.0, le=1.5)
    max_new_tokens: int = Field(default=DEFAULT_MAX_NEW_TOKENS, ge=16, le=512)


def get_model() -> Qwen3TTSModel:
    global _model
    if _model is None:
        if not MODEL_PATH.is_dir():
            raise RuntimeError(f"Qwen3-TTS model is missing: {MODEL_PATH}")
        _model = Qwen3TTSModel.from_pretrained(
            str(MODEL_PATH),
            device_map="cuda:0",
            dtype=torch.bfloat16,
            attn_implementation="sdpa",
        )
    return _model


@app.get("/health")
def health() -> dict:
    return {
        "ready": MODEL_PATH.is_dir(),
        "loaded": _model is not None,
        "model": str(MODEL_PATH),
        "speakers": sorted(SUPPORTED_SPEAKERS),
        "languages": LANGUAGE_MAP,
        "default_max_new_tokens": DEFAULT_MAX_NEW_TOKENS,
        "completed_requests": _completed_requests,
        "max_requests_per_process": MAX_REQUESTS_PER_PROCESS,
    }


@app.post("/synthesize")
def synthesize(request: SynthesisRequest) -> Response:
    global _completed_requests
    if request.speaker not in SUPPORTED_SPEAKERS:
        raise HTTPException(400, f"Unsupported speaker: {request.speaker}")
    language = LANGUAGE_MAP.get(request.language, request.language)
    try:
        with _model_lock:
            torch.manual_seed(request.seed)
            wavs, sample_rate = get_model().generate_custom_voice(
                text=request.text.strip(),
                language=language,
                speaker=request.speaker,
                instruct=request.instruct.strip(),
                do_sample=True,
                top_p=request.top_p,
                temperature=request.temperature,
                repetition_penalty=request.repetition_penalty,
                max_new_tokens=request.max_new_tokens,
            )
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
    buffer = io.BytesIO()
    sf.write(buffer, wavs[0], sample_rate, format="WAV", subtype="PCM_16")
    _completed_requests += 1
    if _completed_requests >= MAX_REQUESTS_PER_PROCESS:
        # Let the HTTP response leave the socket, then recycle the process to release VRAM fragmentation.
        threading.Timer(1.5, lambda: os._exit(0)).start()
    return Response(
        content=buffer.getvalue(),
        media_type="audio/wav",
        headers={
            "X-Qwen-Speaker": request.speaker,
            "X-Sample-Rate": str(sample_rate),
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9881, log_level="info")
