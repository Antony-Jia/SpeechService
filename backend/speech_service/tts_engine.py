from __future__ import annotations

import threading
import uuid
from pathlib import Path

from speech_service.config import Settings

_engine_lock = threading.Lock()
_engine = None

_DEFAULT_EMO_VECTOR = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]  # calm=1.0
_INFER_KWARGS = dict(
    do_sample=True,
    top_p=0.8,
    top_k=30,
    temperature=0.8,
    num_beams=3,
    repetition_penalty=10.0,
    max_mel_tokens=1500,
)


def _get_engine(settings: Settings):
    global _engine
    with _engine_lock:
        if _engine is None:
            from indextts.infer_v2 import IndexTTS2
            _engine = IndexTTS2(
                cfg_path=str(settings.cfg_path()),
                model_dir=str(settings.model_dir()),
                use_fp16=settings.use_fp16,
                device=settings.device,
                use_cuda_kernel=settings.use_cuda_kernel,
                use_torch_compile=settings.use_torch_compile,
            )
        return _engine


_synth_lock_map: dict[str, threading.Semaphore] = {}
_synth_lock_map_lock = threading.Lock()


def _get_synth_lock(settings: Settings) -> threading.Semaphore:
    key = str(settings.checkpoints_dir)
    with _synth_lock_map_lock:
        if key not in _synth_lock_map:
            _synth_lock_map[key] = threading.Semaphore(max(1, settings.max_concurrent_synthesis))
        return _synth_lock_map[key]


def synthesize(text: str, voice_path: Path, output_path: Path, settings: Settings) -> None:
    engine = _get_engine(settings)
    sem = _get_synth_lock(settings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sem:
        engine.infer(
            spk_audio_prompt=str(voice_path),
            text=text,
            output_path=str(output_path),
            emo_alpha=1.0,
            emo_vector=_DEFAULT_EMO_VECTOR,
            emo_audio_prompt=None,
            use_emo_text=False,
            emo_text=None,
            use_random=False,
            interval_silence=200,
            max_text_tokens_per_segment=120,
            **_INFER_KWARGS,
        )


def list_voices(settings: Settings) -> list[dict]:
    voices_dir = settings.voices_dir
    if not voices_dir.is_dir():
        return []
    result = []
    for wav in sorted(voices_dir.glob("*.wav")):
        result.append({"id": wav.stem, "name": wav.stem, "file_url": f"/voices/{wav.name}"})
    return result


def resolve_voice(voice_id: str | None, settings: Settings) -> Path | None:
    voices_dir = settings.voices_dir
    if not voices_dir.is_dir():
        return None
    wavs = sorted(voices_dir.glob("*.wav"))
    if not wavs:
        return None
    if voice_id:
        for wav in wavs:
            if wav.stem == voice_id:
                return wav
        return None
    return wavs[0]
