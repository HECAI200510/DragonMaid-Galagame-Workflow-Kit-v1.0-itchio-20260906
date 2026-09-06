from __future__ import annotations

import argparse
import array
import hashlib
import json
import os
import math
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path


GAME_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = GAME_ROOT.parents[2]
VOICE_STUDIO = WORKSPACE_ROOT / "voice_studio"
sys.path.insert(0, str(VOICE_STUDIO))

from dragonmaid_voice_nodes.voice_core import synthesize_role  # noqa: E402


FFMPEG = Path(os.environ.get("FFMPEG_EXE", "ffmpeg"))
OUTPUT_ROOT = GAME_ROOT / "assets" / "audio" / "voice_emotion"
WORKING_ROOT = GAME_ROOT.parent / "_v2.1_emotion_generation"
ROLE_MAP = {
    "guanjia": "管家",
    "xiahei": "小黑",
    "xiaolv": "小绿",
    "xiaofen": "小粉",
    "xiaohong": "小红",
}

# All characters in this game are treated as adult fictional performers.
# Text is deliberately limited to nonverbal Japanese reactions so it can sit
# under any of the three subtitle languages without replacing formal dialogue.
CUES = [
    {"id": "soft_breath_01", "label": "轻柔喘息 1", "category": "breath_soft", "text": "はぁ……ん……", "emotion": "温柔", "strength": 1.15, "speed": 0.88, "min": 0.70, "max": 2.80, "instruction": "A soft audible exhale followed by a restrained adult feminine breath. Nonverbal only, intimate and emotionally present, no spoken words."},
    {"id": "soft_breath_02", "label": "轻柔喘息 2", "category": "breath_soft", "text": "ふぅ……んっ……", "emotion": "害羞", "strength": 1.20, "speed": 0.90, "min": 0.70, "max": 2.80, "instruction": "A shy, breathy exhale with a tiny catch in the throat. Adult feminine nonverbal reaction, clear emotion, no words."},
    {"id": "shy_gasp_01", "label": "害羞吸气 1", "category": "shy_gasp", "text": "んっ……あっ……", "emotion": "害羞", "strength": 1.45, "speed": 0.96, "min": 0.65, "max": 2.70, "instruction": "A sudden shy gasp that turns into a small embarrassed moan. Adult fictional performer, nonverbal only, clearly flustered."},
    {"id": "shy_gasp_02", "label": "羞怯颤声 2", "category": "shy_gasp", "text": "あっ……んん……", "emotion": "害羞", "strength": 1.50, "speed": 0.94, "min": 0.70, "max": 2.90, "instruction": "A startled adult feminine gasp followed by a trembling restrained hum. Nonverbal only, bashful and vulnerable."},
    {"id": "restrained_moan_01", "label": "压抑呻吟 1", "category": "moan_restrained", "text": "ん……んぅ……", "emotion": "害羞", "strength": 1.50, "speed": 0.88, "min": 0.80, "max": 3.10, "instruction": "A controlled low adult feminine moan held back with visible embarrassment in the voice. Nonverbal only; build gently instead of reading the kana flatly."},
    {"id": "restrained_moan_02", "label": "克制呻吟 2", "category": "moan_restrained", "text": "んっ……はぁ……", "emotion": "温柔", "strength": 1.50, "speed": 0.88, "min": 0.80, "max": 3.20, "instruction": "A restrained moan breaking into an audible warm breath. Adult feminine performance, nonverbal only, emotional rather than neutral."},
    {"id": "heavy_pant_01", "label": "急促喘气 1", "category": "breath_heavy", "text": "はぁっ……はぁっ……", "emotion": "惊讶", "strength": 1.65, "speed": 1.08, "min": 0.95, "max": 3.40, "instruction": "Two urgent adult feminine pants with uneven breath and rising strain. Nonverbal only, energetic and clearly audible, not calm narration."},
    {"id": "heavy_pant_02", "label": "凌乱喘气 2", "category": "breath_heavy", "text": "んっ……はぁ、はぁ……", "emotion": "惊讶", "strength": 1.70, "speed": 1.05, "min": 1.00, "max": 3.60, "instruction": "An adult feminine caught breath followed by two ragged pants. Nonverbal only, increasingly overwhelmed, no extra words."},
    {"id": "rising_moan_01", "label": "上扬娇喘 1", "category": "moan_rising", "text": "んぁ……あっ……", "emotion": "惊讶", "strength": 1.70, "speed": 1.00, "min": 0.75, "max": 3.10, "instruction": "An adult feminine moan that rises in pitch into a short involuntary cry. Nonverbal only, expressive and breath-supported."},
    {"id": "rising_moan_02", "label": "失控娇喘 2", "category": "moan_rising", "text": "あっ……んんっ……", "emotion": "惊讶", "strength": 1.75, "speed": 1.02, "min": 0.75, "max": 3.10, "instruction": "A sharp adult feminine cry followed by a trembling, poorly suppressed moan. Nonverbal only, clearly losing composure."},
    {"id": "climax_cry_01", "label": "高强度尖叫", "category": "cry_peak", "text": "あっ……ああっ！", "emotion": "惊讶", "strength": 1.75, "speed": 1.08, "min": 0.75, "max": 3.20, "instruction": "A sudden high-energy adult feminine peak cry with an emotional climb. Nonverbal only; strong but clean, no clipping, no extra speech."},
    {"id": "shame_sob_01", "label": "羞愧低泣", "category": "sob_shame", "text": "うぅ……ひっ……んっ……", "emotion": "难过", "strength": 1.55, "speed": 0.86, "min": 1.10, "max": 3.90, "instruction": "A quiet adult feminine shame-filled sob with one small hitching breath. Nonverbal only, tearful and embarrassed, still audible."},
    {"id": "bashful_cry_01", "label": "娇羞哭腔", "category": "cry_bashful", "text": "んっ……うぅ……ふぅ……", "emotion": "害羞", "strength": 1.65, "speed": 0.87, "min": 1.10, "max": 4.00, "instruction": "A bashful adult feminine near-cry: trembling moan, tiny tearful whimper, then an unsteady breath. Nonverbal only, shy rather than distressed."},
]


def wav_metrics(path: Path) -> dict:
    with wave.open(str(path), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        frames = reader.getnframes()
        samples = array.array("h", reader.readframes(frames))
    if sys.byteorder != "little":
        samples.byteswap()
    peak = max((abs(value) for value in samples), default=0)
    rms = math.sqrt(sum(float(value) ** 2 for value in samples) / len(samples)) if samples else 0
    return {
        "channels": channels,
        "sampleWidth": sample_width,
        "sampleRate": sample_rate,
        "durationSeconds": round(frames / sample_rate, 3),
        "peakDbFS": round(20 * math.log10(peak / 32768), 2) if peak else float("-inf"),
        "rmsDbFS": round(20 * math.log10(rms / 32768), 2) if rms else float("-inf"),
    }


def resample(source: Path, destination: Path, maximum_seconds: float) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not FFMPEG.is_file():
        raise RuntimeError(f"FFmpeg 不存在：{FFMPEG}")
    fade_start = max(0.2, maximum_seconds - 0.12)
    audio_filter = f"atrim=0:{maximum_seconds:.3f},afade=t=out:st={fade_start:.3f}:d=0.12"
    command = [
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
        "-af", audio_filter, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(destination),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout)[-1200:])


def normalize_quiet_file(path: Path) -> None:
    before = wav_metrics(path)
    gain_db = max(0.0, min(-24.0 - before["rmsDbFS"], -2.0 - before["peakDbFS"]))
    if gain_db <= 0.05:
        return
    temporary = path.with_suffix(".normalized.tmp.wav")
    command = [
        str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-af", f"volume={gain_db:.2f}dB", "-ar", "48000", "-ac", "1",
        "-c:a", "pcm_s16le", str(temporary),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    if completed.returncode != 0:
        temporary.unlink(missing_ok=True)
        raise RuntimeError((completed.stderr or completed.stdout)[-1200:])
    temporary.replace(path)


def valid_existing(path: Path, cue: dict) -> bool:
    try:
        metrics = wav_metrics(path)
        return (
            metrics["sampleRate"] == 48_000
            and metrics["channels"] == 1
            and metrics["sampleWidth"] == 2
            and metrics["durationSeconds"] >= cue["min"] * 0.70
            and metrics["rmsDbFS"] > -45
        )
    except (OSError, wave.Error, ValueError):
        return False


def write_catalog(records: list[dict]) -> None:
    catalog = {
        "schemaVersion": 1,
        "version": "2.1",
        "language": "ja",
        "characters": len(ROLE_MAP),
        "cueTypesPerCharacter": len(CUES),
        "count": len(records),
        "adultFictionalCharacters": True,
        "sounds": records,
    }
    manifest_path = OUTPUT_ROOT / "emotion_voice_manifest.json"
    manifest_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (GAME_ROOT / "data" / "emotion_voice_catalog.js").write_text(
        "// Generated by tools/generate_emotion_vocals.py\n"
        f"window.DRAGON_MAID_EMOTION_CATALOG = Object.freeze({json.dumps(catalog, ensure_ascii=False, indent=2)});\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate role-specific Japanese nonverbal emotion vocals for H5 v2.1.")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    jobs = [(character_id, role, cue) for character_id, role in ROLE_MAP.items() for cue in CUES]
    if args.limit > 0:
        jobs = jobs[: args.limit]
    records: list[dict] = []
    failures: list[str] = []
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    for index, (character_id, role, cue) in enumerate(jobs, 1):
        sound_id = f"ev_{character_id}_{cue['id']}"
        destination = OUTPUT_ROOT / character_id / f"{sound_id}.wav"
        if args.force:
            destination.unlink(missing_ok=True)
            destination.with_suffix(".json").unlink(missing_ok=True)
        print(f"[{index}/{len(jobs)}] {character_id} {cue['label']}", flush=True)
        try:
            if not valid_existing(destination, cue):
                result = None
                attempt_errors = []
                for attempt in range(3):
                    try:
                        result = synthesize_role(
                            text=cue["text"], role=role, language="日语", emotion=cue["emotion"],
                            speed=cue["speed"], emotion_strength=cue["strength"], target_lufs=-18.0,
                            seed=2026090300 + index * 101 + attempt * 7919, use_rvc=False,
                            output_root=WORKING_ROOT, filename_prefix=f"{sound_id}_try{attempt + 1}",
                            delivery_instruction=(
                                "The performer is an adult fictional woman. This is a short standalone emotional vocal "
                                f"for a visual novel, ideally {cue['min']:.2f} to {cue['max']:.2f} seconds. "
                                f"{cue['instruction']} End naturally and do not repeat the whole reaction."
                            ),
                            max_new_tokens=64,
                        )
                        source_metrics = wav_metrics(result.output_path)
                        if source_metrics["durationSeconds"] >= cue["min"] * 0.70 and source_metrics["rmsDbFS"] > -45:
                            break
                        attempt_errors.append(f"try{attempt + 1}: duration={source_metrics['durationSeconds']} rms={source_metrics['rmsDbFS']}")
                        result = None
                    except Exception as error:
                        attempt_errors.append(f"try{attempt + 1}: {error}")
                        result = None
                if result is None:
                    raise RuntimeError("; ".join(attempt_errors))
                resample(result.output_path, destination, cue["max"])
                source_metadata = result.metadata
            else:
                source_metadata = json.loads(destination.with_suffix(".json").read_text(encoding="utf-8")) if destination.with_suffix(".json").is_file() else {}
            metrics = wav_metrics(destination)
            if metrics["rmsDbFS"] < -32:
                normalize_quiet_file(destination)
                metrics = wav_metrics(destination)
            metadata = {
                "schemaVersion": 1,
                "id": sound_id,
                "characterId": character_id,
                "role": role,
                "label": cue["label"],
                "category": cue["category"],
                "text": cue["text"],
                "emotion": cue["emotion"],
                "emotionStrength": cue["strength"],
                "path": f"assets/audio/voice_emotion/{character_id}/{sound_id}.wav",
                "metrics": metrics,
                "engine": "Qwen3-TTS-12Hz-1.7B-CustomVoice",
                "speaker": source_metadata.get("speaker"),
                "technicalStatus": "pass",
                "subjectiveListeningStatus": "pending-human-review",
            }
            destination.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            records.append({
                "id": sound_id, "characterId": character_id, "label": cue["label"], "category": cue["category"],
                "text": cue["text"], "path": metadata["path"], **metrics,
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest().upper(),
            })
            write_catalog(records)
        except Exception as error:
            failures.append(f"{sound_id}: {error}")
            print(f"FAIL {failures[-1]}", file=sys.stderr, flush=True)
    elapsed = time.monotonic() - started
    summary = {"requested": len(jobs), "generatedOrExisting": len(records), "failures": failures, "elapsedSeconds": round(elapsed, 1)}
    (OUTPUT_ROOT / "generation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
