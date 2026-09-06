from __future__ import annotations

import json
import math
import random
import struct
import wave
from pathlib import Path


GAME_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = GAME_ROOT / "assets" / "audio" / "sfx"
SAMPLE_RATE = 48_000
TARGET_PEAK = 0.42


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def envelope(time: float, duration: float, attack: float, release: float) -> float:
    attack_gain = smoothstep(time / max(attack, 1e-6))
    release_gain = smoothstep((duration - time) / max(release, 1e-6))
    return min(attack_gain, release_gain)


def add_tone(
    samples: list[float],
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    end_frequency: float | None = None,
    attack: float = 0.008,
    release: float = 0.08,
    harmonic: float = 0.12,
) -> None:
    start_index = max(0, round(start * SAMPLE_RATE))
    end_index = min(len(samples), round((start + duration) * SAMPLE_RATE))
    phase = 0.0
    for index in range(start_index, end_index):
        local_time = (index - start_index) / SAMPLE_RATE
        progress = local_time / max(duration, 1e-6)
        current_frequency = frequency + ((end_frequency or frequency) - frequency) * progress
        phase += math.tau * current_frequency / SAMPLE_RATE
        gain = envelope(local_time, duration, attack, release)
        fundamental = math.sin(phase)
        overtone = math.sin(phase * 2.0 + 0.35) * harmonic
        samples[index] += amplitude * gain * (fundamental + overtone)


def add_soft_noise(
    samples: list[float],
    start: float,
    duration: float,
    amplitude: float,
    *,
    seed: int,
    attack: float = 0.01,
    release: float = 0.08,
    smoothing: float = 0.82,
) -> None:
    rng = random.Random(seed)
    start_index = max(0, round(start * SAMPLE_RATE))
    end_index = min(len(samples), round((start + duration) * SAMPLE_RATE))
    filtered = 0.0
    for index in range(start_index, end_index):
        local_time = (index - start_index) / SAMPLE_RATE
        raw = rng.uniform(-1.0, 1.0)
        filtered = smoothing * filtered + (1.0 - smoothing) * raw
        gain = envelope(local_time, duration, attack, release)
        samples[index] += amplitude * gain * filtered


def new_buffer(duration: float) -> list[float]:
    return [0.0] * round(duration * SAMPLE_RATE)


def normalize(samples: list[float]) -> list[float]:
    peak = max((abs(value) for value in samples), default=1.0)
    scale = TARGET_PEAK / peak if peak else 1.0
    return [max(-1.0, min(1.0, value * scale)) for value in samples]


def create_ui_click() -> list[float]:
    samples = new_buffer(0.11)
    add_tone(samples, 0.0, 0.095, 1_180, 0.7, end_frequency=860, release=0.06)
    add_soft_noise(samples, 0.0, 0.055, 0.2, seed=101, release=0.045, smoothing=0.72)
    return samples


def create_ui_confirm() -> list[float]:
    samples = new_buffer(0.34)
    add_tone(samples, 0.0, 0.18, 620, 0.5, release=0.1)
    add_tone(samples, 0.115, 0.21, 930, 0.65, release=0.12)
    return samples


def create_dialogue_advance() -> list[float]:
    samples = new_buffer(0.16)
    add_soft_noise(samples, 0.0, 0.14, 0.65, seed=202, attack=0.004, release=0.1, smoothing=0.9)
    add_tone(samples, 0.015, 0.1, 720, 0.2, end_frequency=430, release=0.08)
    return samples


def create_gallery_open() -> list[float]:
    samples = new_buffer(0.72)
    for start, frequency, amplitude in ((0.0, 523.25, 0.46), (0.12, 659.25, 0.5), (0.24, 783.99, 0.56)):
        add_tone(samples, start, 0.43, frequency, amplitude, release=0.24, harmonic=0.2)
    return samples


def create_theme_switch() -> list[float]:
    samples = new_buffer(0.48)
    add_soft_noise(samples, 0.0, 0.42, 0.25, seed=303, attack=0.025, release=0.2, smoothing=0.93)
    add_tone(samples, 0.0, 0.42, 540, 0.48, end_frequency=1_080, release=0.18, harmonic=0.24)
    return samples


def create_game_start() -> list[float]:
    samples = new_buffer(0.96)
    for start, frequency, amplitude in ((0.0, 392.0, 0.4), (0.16, 523.25, 0.48), (0.32, 659.25, 0.56), (0.48, 783.99, 0.64)):
        add_tone(samples, start, 0.46, frequency, amplitude, release=0.24, harmonic=0.18)
    return samples


def create_save_confirm() -> list[float]:
    samples = new_buffer(0.3)
    add_tone(samples, 0.0, 0.16, 880, 0.52, release=0.1)
    add_tone(samples, 0.095, 0.19, 1_174.66, 0.62, release=0.12)
    return samples


def create_load_confirm() -> list[float]:
    samples = new_buffer(0.34)
    add_tone(samples, 0.0, 0.2, 1_046.5, 0.5, release=0.12)
    add_tone(samples, 0.105, 0.21, 698.46, 0.58, release=0.13)
    return samples


def create_scene_enter() -> list[float]:
    samples = new_buffer(0.68)
    add_soft_noise(samples, 0.0, 0.62, 0.5, seed=404, attack=0.06, release=0.24, smoothing=0.94)
    add_tone(samples, 0.06, 0.54, 310, 0.34, end_frequency=680, attack=0.06, release=0.2, harmonic=0.08)
    return samples


def create_branch_choice() -> list[float]:
    samples = new_buffer(0.44)
    add_tone(samples, 0.0, 0.3, 466.16, 0.48, release=0.18)
    add_tone(samples, 0.11, 0.3, 698.46, 0.58, release=0.18)
    return samples


def create_result_complete() -> list[float]:
    samples = new_buffer(1.28)
    for start, frequency, amplitude in ((0.0, 523.25, 0.38), (0.16, 659.25, 0.46), (0.32, 783.99, 0.5), (0.48, 1_046.5, 0.64)):
        add_tone(samples, start, 0.72, frequency, amplitude, release=0.36, harmonic=0.2)
    return samples


def create_result_defeat() -> list[float]:
    samples = new_buffer(0.92)
    add_tone(samples, 0.0, 0.52, 523.25, 0.5, end_frequency=466.16, release=0.28)
    add_tone(samples, 0.25, 0.62, 392.0, 0.58, end_frequency=293.66, release=0.34, harmonic=0.08)
    return samples


SOUNDS = (
    ("ui_click", create_ui_click, "普通按钮点击", "所有未指定专用提示音的按钮"),
    ("ui_confirm", create_ui_confirm, "设置确认", "声音开启与台词音频模式确认"),
    ("dialogue_advance", create_dialogue_advance, "对话推进", "点击、Space 或 Enter 推进台词"),
    ("gallery_open", create_gallery_open, "页面展开", "CG 鉴赏与制作人员页"),
    ("theme_switch", create_theme_switch, "主题切换", "昼夜主题按钮"),
    ("game_start", create_game_start, "游戏开始", "新游戏与继续游戏"),
    ("save_confirm", create_save_confirm, "保存完成", "写入存档槽"),
    ("load_confirm", create_load_confirm, "读取完成", "读取有效存档槽"),
    ("scene_enter", create_scene_enter, "角色登场转场", "每名角色的首个主线场景"),
    ("branch_choice", create_branch_choice, "分支确认", "主线结束后的路线选择"),
    ("result_complete", create_result_complete, "挑战完成", "全员挑战完成结局"),
    ("result_defeat", create_result_defeat, "本轮结束", "玩家战败支线结局"),
)


def write_wave(path: Path, samples: list[float]) -> dict:
    normalized = normalize(samples)
    pcm = b"".join(struct.pack("<h", round(value * 32767)) for value in normalized)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(pcm)
    peak = max(abs(value) for value in normalized)
    rms = math.sqrt(sum(value * value for value in normalized) / len(normalized))
    return {
        "file": path.name,
        "durationSeconds": round(len(normalized) / SAMPLE_RATE, 3),
        "sampleRate": SAMPLE_RATE,
        "channels": 1,
        "sampleWidthBits": 16,
        "peakDbfs": round(20.0 * math.log10(max(peak, 1e-9)), 2),
        "rmsDbfs": round(20.0 * math.log10(max(rms, 1e-9)), 2),
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schemaVersion": 1,
        "generator": "tools/generate_sfx_pack.py",
        "license": "Original procedural audio generated for this project; no external samples used.",
        "sounds": {},
    }
    for sound_id, factory, description, usage in SOUNDS:
        path = OUTPUT_DIR / f"{sound_id}.wav"
        metadata = write_wave(path, factory())
        metadata.update({"description": description, "usage": usage})
        manifest["sounds"][sound_id] = metadata
        print(f"{sound_id}: {metadata['durationSeconds']:.3f}s / {metadata['peakDbfs']:.2f} dBFS")
    (OUTPUT_DIR / "sfx_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(SOUNDS)} SFX in {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
