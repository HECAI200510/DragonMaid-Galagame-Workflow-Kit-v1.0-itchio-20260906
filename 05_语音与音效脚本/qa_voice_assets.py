from __future__ import annotations

import argparse
import array
import csv
import json
import math
import re
import subprocess
import wave
from pathlib import Path


I_PATTERN = re.compile(r"I:\s+(-?inf|-?\d+(?:\.\d+)?)\s+LUFS")
PEAK_PATTERN = re.compile(r"Peak:\s+(-?inf|-?\d+(?:\.\d+)?)\s+dBFS")


def wave_metrics(path: Path) -> dict:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_rate = wav.getframerate()
        sample_width = wav.getsampwidth()
        frames = wav.getnframes()
        raw = wav.readframes(frames)
    peak_dbfs = None
    if sample_width == 2 and raw:
        samples = array.array("h")
        samples.frombytes(raw)
        peak = max(abs(value) for value in samples) if samples else 0
        peak_dbfs = 20 * math.log10(peak / 32767) if peak else float("-inf")
    return {
        "channels": channels,
        "sample_rate": sample_rate,
        "sample_width": sample_width,
        "duration": frames / max(sample_rate, 1),
        "sample_peak_dbfs": peak_dbfs,
    }


def loudness_metrics(ffmpeg: Path, path: Path) -> dict:
    process = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-nostats", "-i", str(path), "-filter_complex", "ebur128=peak=true", "-f", "null", "NUL"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    text = process.stderr
    integrated = I_PATTERN.findall(text)
    peaks = PEAK_PATTERN.findall(text)
    return {
        "integrated_lufs": float(integrated[-1]) if integrated and integrated[-1] not in {"inf", "-inf"} else None,
        "true_peak_dbfs": float(peaks[-1]) if peaks and peaks[-1] not in {"inf", "-inf"} else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("voice_dir")
    parser.add_argument("report_dir")
    parser.add_argument("--ffmpeg", required=True)
    args = parser.parse_args()

    voice_dir = Path(args.voice_dir)
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = Path(args.ffmpeg)
    results = []
    for path in sorted(voice_dir.glob("*.wav")):
        item = {"file": path.name, **wave_metrics(path), **loudness_metrics(ffmpeg, path)}
        reasons = []
        if item["sample_rate"] != 48000:
            reasons.append("采样率不是48kHz")
        if item["channels"] != 1:
            reasons.append("不是单声道")
        if item["sample_width"] not in {2, 3}:
            reasons.append("位深不是16/24-bit")
        if item["duration"] < 0.15:
            reasons.append("时长过短")
        if item["sample_peak_dbfs"] is not None and item["sample_peak_dbfs"] > -2.8:
            reasons.append("峰值高于约-3dBFS")
        if item["integrated_lufs"] is not None and not (-20.5 <= item["integrated_lufs"] <= -15.5):
            reasons.append("整体响度偏离目标")
        item["technical_status"] = "通过" if not reasons else "需返修"
        item["reasons"] = "；".join(reasons)
        results.append(item)

    summary = {
        "total": len(results),
        "passed": sum(item["technical_status"] == "通过" for item in results),
        "failed": sum(item["technical_status"] != "通过" for item in results),
        "sample_rate_48000": sum(item["sample_rate"] == 48000 for item in results),
        "mono": sum(item["channels"] == 1 for item in results),
        "pcm_16_or_24": sum(item["sample_width"] in {2, 3} for item in results),
    }
    (report_dir / "qa_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "qa_details.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    if results:
        with (report_dir / "qa_details.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(results[0]))
            writer.writeheader()
            writer.writerows(results)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
