from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
import time
import wave
from pathlib import Path

import requests


def audio_info(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        return {
            "channels": wav.getnchannels(),
            "sample_rate": wav.getframerate(),
            "sample_width": wav.getsampwidth(),
            "frames": wav.getnframes(),
            "duration": wav.getnframes() / max(wav.getframerate(), 1),
        }


INTEGRATED_PATTERN = re.compile(r"I:\s+(-?inf|-?\d+(?:\.\d+)?)\s+LUFS")


def post_process(ffmpeg: Path, raw: Path, output: Path, speed: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    filters = []
    if abs(speed - 1.0) > 0.001:
        filters.append(f"atempo={max(0.75, min(1.35, speed)):.4f}")
    filters.append("silenceremove=start_periods=1:start_silence=0.08:start_threshold=-50dB:stop_periods=-1:stop_silence=0.12:stop_threshold=-50dB")
    with tempfile.TemporaryDirectory(prefix="dragonmaid_post_") as temp_dir:
        prepared = Path(temp_dir) / "prepared.wav"
        subprocess.run(
            [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw),
             "-af", ",".join(filters), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(prepared)],
            check=True, capture_output=True, timeout=300,
        )
        analysis = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-nostats", "-i", str(prepared),
             "-filter_complex", "ebur128=peak=true", "-f", "null", "NUL"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
        )
        measured_values = INTEGRATED_PATTERN.findall(analysis.stderr)
        if not measured_values or measured_values[-1] in {"inf", "-inf"}:
            raise RuntimeError("Unable to measure integrated loudness")
        measured_lufs = float(measured_values[-1])
        gain_db = -18.0 - measured_lufs
        normalization = f"volume={gain_db:.3f}dB,alimiter=limit=0.707946:attack=5:release=50:level=0"
        subprocess.run(
            [str(ffmpeg), "-y", "-hide_banner", "-loglevel", "error", "-i", str(prepared),
             "-af", normalization, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(output)],
            check=True, capture_output=True, timeout=300,
        )


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("output_root")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9881/synthesize")
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--voice-id", action="append", default=[])
    parser.add_argument("--retry", type=int, default=2)
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    ffmpeg = Path(args.ffmpeg)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected = [row for row in data["rows"] if row.get("production_status") == "待生成"]
    if args.voice_id:
        wanted = set(args.voice_id)
        selected = [row for row in selected if row["voice_id"] in wanted]
    if args.limit > 0:
        selected = selected[:args.limit]

    log_path = output_root / "generation_log.jsonl"
    completed = 0
    failed = 0
    skipped = 0
    started = time.time()

    for index, row in enumerate(selected, 1):
        output = output_root / row["output_file"]
        if output.is_file():
            try:
                info = audio_info(output)
                if info["sample_rate"] == 48000 and info["channels"] == 1 and info["sample_width"] == 2 and info["duration"] > 0.15:
                    skipped += 1
                    continue
            except Exception:
                pass

        payload = {
            "text": row["text"],
            "language": "zh",
            "speaker": row["speaker_model"],
            "instruct": row["instruction"],
            "seed": int(row["voice_seed"]),
            "top_p": float(row["top_p"]),
            "temperature": float(row["temperature"]),
            "repetition_penalty": float(row["repetition_penalty"]),
        }
        error = None
        for attempt in range(1, args.retry + 2):
            try:
                response = requests.post(args.endpoint, json=payload, timeout=900)
                response.raise_for_status()
                with tempfile.TemporaryDirectory(prefix="dragonmaid_voice_") as temp_dir:
                    raw = Path(temp_dir) / "raw.wav"
                    raw.write_bytes(response.content)
                    post_process(ffmpeg, raw, output, float(row["speed"]))
                info = audio_info(output)
                if info["sample_rate"] != 48000 or info["channels"] != 1 or info["sample_width"] != 2:
                    raise RuntimeError(f"Unexpected output format: {info}")
                completed += 1
                append_jsonl(log_path, {
                    "voice_id": row["voice_id"], "status": "已生成", "attempt": attempt,
                    "file": str(output), "audio": info, "seed": row["voice_seed"],
                    "speaker": row["speaker_model"], "model": row["model"],
                })
                error = None
                break
            except Exception as exc:
                error = str(exc)
                if attempt <= args.retry:
                    time.sleep(min(3 * attempt, 10))
        if error is not None:
            failed += 1
            append_jsonl(log_path, {
                "voice_id": row["voice_id"], "status": "生成失败", "error": error,
                "seed": row["voice_seed"], "speaker": row.get("speaker_model", ""),
            })
        if index == 1 or index % 5 == 0 or index == len(selected):
            elapsed = time.time() - started
            print(json.dumps({
                "current": index, "total": len(selected), "completed": completed,
                "skipped": skipped, "failed": failed, "elapsed_seconds": round(elapsed, 1),
                "last_voice_id": row["voice_id"],
            }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
