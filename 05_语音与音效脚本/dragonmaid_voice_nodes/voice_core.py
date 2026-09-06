from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STUDIO_ROOT = Path(os.environ.get("DMT_AI_STUDIO", str(Path.home() / "DMT-AI-Studio"))).expanduser()
QWEN_ENDPOINT = os.environ.get("DRAGONMAID_QWEN_TTS_ENDPOINT", "http://127.0.0.1:9881/synthesize")
QWEN_HEALTH = os.environ.get("DRAGONMAID_QWEN_TTS_HEALTH", "http://127.0.0.1:9881/health")
QWEN_PYTHON = STUDIO_ROOT / "envs" / "qwen3tts" / "Scripts" / "python.exe"
QWEN_SERVICE = STUDIO_ROOT / "scripts" / "qwen_customvoice_service.py"
RVC_ROOT = STUDIO_ROOT / "apps" / "RVC-WebUI"
RVC_PYTHON = STUDIO_ROOT / "envs" / "rvc" / "Scripts" / "python.exe"
RVC_MODEL_ROOT = STUDIO_ROOT / "models" / "rvc" / "Qwen3_CustomVoice_4Speaker_v1"
RVC_MODEL = RVC_MODEL_ROOT / "Qwen3_CustomVoice_4Speaker_v1.pth"
FFMPEG = RVC_ROOT / "ffmpeg.exe"
DEFAULT_OUTPUT_ROOT = (
    STUDIO_ROOT
    / "projects"
    / "dragonmaid-galgame"
    / "outputs"
    / "voice_comfyui"
)
TRUE_PEAK_DBTP = -1.5


ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "管家": {
        "folder": "01_管家",
        "speaker": "Serena",
        "rvc_speaker_id": 1,
        "speed": 0.94,
        "top_p": 0.78,
        "temperature": 0.58,
        "repetition_penalty": 1.12,
        "instruct": (
            "Calm and reliable adult head maid. Controlled lower energy, precise articulation, "
            "gentle authority, restrained warmth at sentence endings."
        ),
        "sample": "欢迎回来，主人。今天的日程已经整理完毕，请先把外套交给我吧。",
    },
    "小红": {
        "folder": "02_小红",
        "speaker": "Vivian",
        "rvc_speaker_id": 0,
        "speed": 1.00,
        "top_p": 0.84,
        "temperature": 0.68,
        "repetition_penalty": 1.10,
        "instruct": (
            "Capable and confident adult kitchen maid with a mildly proud tone. Bright, energetic "
            "and crisp; briefly flustered when praised. Not childish."
        ),
        "sample": "我只是顺手把晚餐做好了，可不是特意等你回来。趁热吃，别让我说第二遍。",
    },
    "小绿": {
        "folder": "03_小绿",
        "speaker": "Ono_Anna",
        "rvc_speaker_id": 2,
        "speed": 1.07,
        "top_p": 0.88,
        "temperature": 0.78,
        "repetition_penalty": 1.08,
        "instruct": (
            "Playful and lively young adult parlor maid. Quick reactions, a mischievous smile in "
            "the voice, bright and clear but not childish."
        ),
        "sample": "主人，猜猜我今天发现了什么？答对了就分你一半甜点。",
    },
    "小蓝": {
        "folder": "04_小蓝_SFW",
        "speaker": "Ono_Anna",
        "rvc_speaker_id": 2,
        "speed": 1.02,
        "top_p": 0.82,
        "temperature": 0.72,
        "repetition_penalty": 1.10,
        "instruct": (
            "All-ages cute fantasy character. Soft, clumsy and innocent, with small surprised "
            "pauses; clear and rounded pronunciation. Never sensual."
        ),
        "sample": "哇，我真的没有把床单洗成蓝色！大概只是水自己变蓝了吧？",
    },
    "小粉": {
        "folder": "05_小粉",
        "speaker": "Serena",
        "rvc_speaker_id": 1,
        "speed": 0.91,
        "top_p": 0.76,
        "temperature": 0.55,
        "repetition_penalty": 1.13,
        "instruct": (
            "Warm and caring adult nurse maid. Gentle, reassuring and unhurried with clear "
            "consonants and natural warmth. Avoid excessive breathiness."
        ),
        "sample": "别勉强自己，先坐下来慢慢呼吸。剩下的事情交给我。",
    },
    "小金": {
        "folder": "06_小金",
        "speaker": "Sohee",
        "rvc_speaker_id": 3,
        "speed": 0.96,
        "top_p": 0.80,
        "temperature": 0.64,
        "repetition_penalty": 1.11,
        "instruct": (
            "Elegant and noble adult personal maid. Refined diction, composed confidence, and a "
            "subtle playful trickster undertone near the end."
        ),
        "sample": "哎呀，我真的只是第一次来这里而已。至于这把钥匙，那当然是个秘密。",
    },
    "小黑": {
        "folder": "07_小黑",
        "speaker": "Serena",
        "rvc_speaker_id": 1,
        "speed": 0.93,
        "top_p": 0.79,
        "temperature": 0.60,
        "repetition_penalty": 1.12,
        "instruct": (
            "Quiet and reserved adult chamber maid. Soft but fully intelligible, shy and serious "
            "with a hidden trace of affection. Not gloomy and not weak."
        ),
        "sample": "那个，我把卧室收拾好了。如果你不介意，我可以再留下来一会儿吗？",
    },
}


ROLE_SAMPLE_TEXTS: dict[str, dict[str, str]] = {
    "管家": {
        "中文": "欢迎回来，主人。今天的日程已经整理完毕，请先把外套交给我吧。",
        "日语": "お帰りなさいませ、ご主人様。本日の予定は整理済みです。まずは上着をお預かりします。",
        "英语": "Welcome home, Master. I have organized today's schedule, so please let me take your coat first.",
    },
    "小红": {
        "中文": "我只是顺手把晚餐做好了，可不是特意等你回来。趁热吃，别让我说第二遍。",
        "日语": "夕食はついでに作っただけよ。あなたを待っていたわけじゃないんだから。冷めないうちに食べなさい。",
        "英语": "I only made dinner because I had time. I wasn't waiting for you. Eat it while it's hot.",
    },
    "小绿": {
        "中文": "主人，猜猜我今天发现了什么？答对了就分你一半甜点。",
        "日语": "ご主人、今日わたしが何を見つけたか当ててみて。正解したら、お菓子を半分あげる！",
        "英语": "Master, guess what I found today. If you get it right, I'll share half my dessert with you!",
    },
    "小蓝": {
        "中文": "哇，我真的没有把床单洗成蓝色！大概只是水自己变蓝了吧？",
        "日语": "わあ、シーツを青く染めたのは私じゃないよ！きっと水が勝手に青くなったんだよ？",
        "英语": "I really didn't wash the sheets blue! Maybe the water simply turned blue by itself?",
    },
    "小粉": {
        "中文": "别勉强自己，先坐下来慢慢呼吸。剩下的事情交给我。",
        "日语": "無理をしないで。まず座って、ゆっくり息をして。あとはお姉さんに任せてね。",
        "英语": "Don't push yourself. Sit down and breathe slowly. You can leave the rest to me.",
    },
    "小金": {
        "中文": "哎呀，我真的只是第一次来这里而已。至于这把钥匙，那当然是个秘密。",
        "日语": "あら、ここへ来たのは本当に初めてですわ。この鍵のことは、もちろん秘密です。",
        "英语": "Oh my, this truly is my first time here. As for this key, that is naturally a secret.",
    },
    "小黑": {
        "中文": "那个，我把卧室收拾好了。如果你不介意，我可以再留下来一会儿吗？",
        "日语": "あの、寝室のお掃除は終わりました。迷惑でなければ、もう少しここにいてもいいですか？",
        "英语": "Um, I finished tidying the bedroom. If you don't mind, may I stay a little longer?",
    },
}


LANGUAGES = {"中文": "zh", "日语": "ja", "英语": "en"}
EMOTIONS: dict[str, str] = {
    "平静": "Speak naturally and calmly, with controlled breathing and a neutral, attentive tone.",
    "开心": "Sound genuinely happy and bright, with a smiling voice and lively rhythm.",
    "害羞": "Sound shy and flustered, with restrained warmth and tiny hesitant pauses; remain clear.",
    "生气": "Sound annoyed and firm, with sharper consonants and controlled intensity; do not shout.",
    "难过": "Sound quietly sad and vulnerable, with slower phrasing; remain intelligible and avoid whispering.",
    "惊讶": "Sound surprised and alert, with a quick intake-like pause and raised energy; remain natural.",
    "温柔": "Sound gentle, caring and reassuring, with soft warmth but no excessive breathiness.",
    "调皮": "Sound playful and teasing, with a restrained mischievous smile; keep the delivery tasteful.",
}


@dataclass(frozen=True)
class VoiceResult:
    output_path: Path
    metadata_path: Path
    qwen_path: Path
    metadata: dict[str, Any]


def sanitize_name(value: str, limit: int = 36) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", str(value).strip())
    return (cleaned.strip("_") or "line")[:limit]


def normalize_role(value: str) -> str:
    text = str(value).strip()
    aliases = {
        "哈斯姬": "管家",
        "缇露露": "小红",
        "帕露拉": "小绿",
        "拉德莉": "小蓝",
        "纳莎莉": "小粉",
        "艾尔德": "小金",
        "切依姆": "小黑",
    }
    for role in ROLE_PRESETS:
        if role in text:
            return role
    for alias, role in aliases.items():
        if alias in text:
            return role
    raise ValueError(f"未知角色：{value}。可用角色：{', '.join(ROLE_PRESETS)}")


def normalize_language(value: str) -> str:
    text = str(value).strip().lower()
    aliases = {
        "中文": "zh", "汉语": "zh", "chinese": "zh", "zh-cn": "zh", "zh": "zh",
        "日语": "ja", "日文": "ja", "japanese": "ja", "jp": "ja", "ja": "ja",
        "英语": "en", "英文": "en", "english": "en", "en-us": "en", "en": "en",
    }
    if text not in aliases:
        raise ValueError(f"未知语言：{value}。请使用中文、日语或英语。")
    return aliases[text]


def normalize_emotion(value: str) -> str:
    text = str(value).strip()
    aliases = {
        "neutral": "平静", "normal": "平静", "default": "平静", "happy": "开心", "joy": "开心",
        "shy": "害羞", "angry": "生气", "sad": "难过", "surprised": "惊讶",
        "gentle": "温柔", "teasing": "调皮", "playful": "调皮",
        "troubled": "难过", "serious": "平静", "breathy": "害羞",
    }
    text = aliases.get(text.lower(), text)
    if text not in EMOTIONS:
        raise ValueError(f"未知情绪：{value}。可用情绪：{', '.join(EMOTIONS)}")
    return text


def service_is_ready(timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(QWEN_HEALTH, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return bool(payload.get("ready"))
    except (OSError, ValueError, urllib.error.URLError):
        return False


def start_qwen_service(wait_seconds: float = 20.0) -> None:
    if service_is_ready():
        return
    if not QWEN_PYTHON.is_file() or not QWEN_SERVICE.is_file():
        raise RuntimeError(
            "千问 TTS 服务未启动，且自动启动文件不存在。请先运行龙女仆语音工作台。"
        )
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    subprocess.Popen(
        [str(QWEN_PYTHON), str(QWEN_SERVICE)],
        cwd=str(STUDIO_ROOT),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if service_is_ready():
            return
        time.sleep(0.4)
    raise RuntimeError("千问 TTS 服务启动超时。请检查 DMT-AI-Studio/logs/voice-studio。")


def _post_qwen(payload: dict[str, Any], timeout: float = 900.0) -> bytes:
    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(3):
        request = urllib.request.Request(
            QWEN_ENDPOINT,
            data=payload_bytes,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"千问 TTS 返回 HTTP {exc.code}：{detail[:1200]}") from exc
        except (urllib.error.URLError, ConnectionResetError, OSError) as exc:
            last_error = exc
            if attempt >= 2:
                break
            time.sleep(0.8 + attempt * 0.8)
            start_qwen_service(wait_seconds=60.0)
    raise RuntimeError(f"无法连接千问 TTS 服务（已自动重试 3 次）：{last_error}") from last_error


def _run(command: list[str], timeout: float = 300.0, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env={**os.environ, "PYTHONUTF8": "1"},
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "未知错误")[-3000:]
        raise RuntimeError(detail)
    return completed


def _parse_loudnorm(text: str) -> dict[str, str] | None:
    blocks = re.findall(r'\{\s*"input_i".*?\}', text, flags=re.S)
    if not blocks:
        return None
    try:
        return json.loads(blocks[-1])
    except json.JSONDecodeError:
        return None


def _normalize_audio(source: Path, output: Path, target_lufs: float) -> dict[str, Any]:
    target_lufs = max(-24.0, min(-10.0, float(target_lufs)))
    if not FFMPEG.is_file():
        shutil.copy2(source, output)
        return {"warning": "FFmpeg 不存在，保留原始响度", "target_lufs": target_lufs}
    analysis = _run(
        [
            str(FFMPEG), "-hide_banner", "-nostats", "-i", str(source),
            "-af", f"loudnorm=I={target_lufs}:TP={TRUE_PEAK_DBTP}:LRA=7:print_format=json",
            "-f", "null", "NUL",
        ],
        timeout=180,
    )
    measured = _parse_loudnorm(analysis.stderr)
    finite_measurements = False
    if measured:
        try:
            finite_measurements = all(
                math.isfinite(float(measured[key]))
                for key in ("input_i", "input_lra", "input_tp", "input_thresh", "target_offset")
            )
        except (KeyError, TypeError, ValueError):
            finite_measurements = False
    if not measured or not finite_measurements:
        _run(
            [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
             "-af", f"loudnorm=I={target_lufs}:TP={TRUE_PEAK_DBTP}:LRA=7",
             "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(output)],
            timeout=180,
        )
        return {
            "target_lufs": target_lufs,
            "method": "FFmpeg EBU R128 one-pass",
            "warning": "two-pass measurements were non-finite" if measured else "two-pass measurements unavailable",
        }
    filter_text = (
        f"loudnorm=I={target_lufs}:TP={TRUE_PEAK_DBTP}:LRA=7"
        f":measured_I={measured['input_i']}:measured_LRA={measured['input_lra']}"
        f":measured_TP={measured['input_tp']}:measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}:linear=true:print_format=summary"
    )
    _run(
        [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
         "-af", filter_text, "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(output)],
        timeout=180,
    )
    return {
        "target_lufs": target_lufs,
        "target_true_peak_dbtp": TRUE_PEAK_DBTP,
        "before_lufs": measured.get("input_i"),
        "before_true_peak_dbtp": measured.get("input_tp"),
        "method": "FFmpeg EBU R128 two-pass",
    }


def _apply_speed(source: Path, output: Path, speed: float) -> None:
    speed = max(0.75, min(1.35, float(speed)))
    if math.isclose(speed, 1.0, abs_tol=0.001):
        shutil.copy2(source, output)
        return
    if not FFMPEG.is_file():
        raise RuntimeError(f"调整语速需要 FFmpeg，但没有找到：{FFMPEG}")
    _run(
        [str(FFMPEG), "-y", "-hide_banner", "-loglevel", "error", "-i", str(source),
         "-af", f"atempo={speed:.4f}", "-ar", "24000", "-ac", "1",
         "-c:a", "pcm_s16le", str(output)],
        timeout=180,
    )


def _run_rvc(source: Path, output: Path, speaker_id: int) -> dict[str, Any]:
    if not RVC_PYTHON.is_file() or not RVC_MODEL.is_file():
        raise RuntimeError("RVC 环境或四音色模型缺失，请改用“仅 Qwen 原声”。")
    command = [
        str(RVC_PYTHON), "-m", "infer.cli",
        "--model", str(RVC_MODEL), "--input", str(source), "--output", str(output),
        "--speaker-id", str(int(speaker_id)), "--pitch", "0", "--f0-method", "rmvpe",
        "--index-rate", "0.45", "--rms-mix-rate", "0.32", "--protect", "0.33", "--overwrite",
    ]
    _run(command, timeout=900, cwd=RVC_ROOT)
    if not output.is_file():
        raise RuntimeError("RVC 命令完成但没有生成 WAV。")
    return {
        "model": str(RVC_MODEL), "speaker_id": int(speaker_id), "f0_method": "rmvpe",
        "pitch": 0, "index_rate": 0.45, "rms_mix_rate": 0.32, "protect": 0.33,
    }


def synthesize_role(
    text: str,
    role: str,
    language: str = "中文",
    emotion: str = "平静",
    speed: float | None = None,
    emotion_strength: float = 1.0,
    target_lufs: float = -16.0,
    seed: int = 20260824,
    use_rvc: bool = False,
    output_root: str | Path | None = None,
    filename_prefix: str = "",
    delivery_instruction: str = "",
    max_new_tokens: int = 192,
    auto_start_service: bool = True,
) -> VoiceResult:
    text = str(text).strip()
    if not text:
        raise ValueError("台词不能为空。")
    if len(text) > 3000:
        raise ValueError("单条台词不能超过 3000 字符，请拆分后批量生成。")
    role = normalize_role(role)
    language_code = normalize_language(language)
    emotion = normalize_emotion(emotion)
    preset = ROLE_PRESETS[role]
    speed = preset["speed"] if speed is None else max(0.75, min(1.35, float(speed)))
    emotion_strength = max(0.25, min(1.75, float(emotion_strength)))
    if auto_start_service:
        start_qwen_service()
    elif not service_is_ready():
        raise RuntimeError("千问 TTS 服务未启动。")

    instruct = (
        f"{preset['instruct']} {EMOTIONS[emotion]} Emotion strength: {emotion_strength:.2f}. "
        "Clean studio recording, clear articulation, no whisper, no reverb, no background music."
    )
    if str(delivery_instruction).strip():
        instruct = f"{instruct} {str(delivery_instruction).strip()}"
    payload = {
        "text": text,
        "delivery_instruction": str(delivery_instruction).strip(),
        "language": language_code,
        "speaker": preset["speaker"],
        "instruct": instruct,
        "seed": int(seed),
        "top_p": float(preset["top_p"]),
        "temperature": float(preset["temperature"]),
        "repetition_penalty": float(preset["repetition_penalty"]),
        "max_new_tokens": max(16, min(512, int(max_new_tokens))),
    }
    root = Path(output_root) if output_root else DEFAULT_OUTPUT_ROOT
    role_root = root / preset["folder"] / language_code / sanitize_name(emotion)
    role_root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S") + f"_{time.time_ns() % 1_000_000:06d}"
    prefix = sanitize_name(filename_prefix) + "_" if str(filename_prefix).strip() else ""
    stem = f"{stamp}_{prefix}{sanitize_name(text)}"
    raw_path = role_root / f"{stem}_qwen_raw.wav"
    paced_path = role_root / f"{stem}_paced.tmp.wav"
    qwen_path = role_root / f"{stem}_qwen.wav"
    rvc_raw_path = role_root / f"{stem}_rvc_raw.tmp.wav"
    final_path = role_root / f"{stem}_{'rvc' if use_rvc else 'qwen'}.wav"

    raw_path.write_bytes(_post_qwen(payload))
    try:
        _apply_speed(raw_path, paced_path, speed)
        loudness_qwen = _normalize_audio(paced_path, qwen_path, target_lufs)
        if use_rvc:
            rvc_info = _run_rvc(qwen_path, rvc_raw_path, int(preset["rvc_speaker_id"]))
            loudness_final = _normalize_audio(rvc_raw_path, final_path, target_lufs)
        else:
            rvc_info = None
            loudness_final = loudness_qwen
    finally:
        paced_path.unlink(missing_ok=True)
        rvc_raw_path.unlink(missing_ok=True)

    metadata = {
        "schema_version": 1,
        "role": role,
        "language": language_code,
        "emotion": emotion,
        "emotion_strength": emotion_strength,
        "speed": speed,
        "target_lufs": float(target_lufs),
        "seed": int(seed),
        "mode": "Qwen3-TTS -> RVC" if use_rvc else "Qwen3-TTS",
        "speaker": preset["speaker"],
        "text": text,
        "request": payload,
        "qwen_output": str(qwen_path),
        "final_output": str(final_path),
        "qwen_loudness": loudness_qwen,
        "final_loudness": loudness_final,
        "rvc": rvc_info,
    }
    metadata_path = final_path.with_suffix(".json")
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_path.unlink(missing_ok=True)
    return VoiceResult(final_path, metadata_path, qwen_path, metadata)


def wav_to_comfy_audio(path: str | Path):
    import torch

    audio_path = Path(path)
    with wave.open(str(audio_path), "rb") as reader:
        channels = reader.getnchannels()
        sample_width = reader.getsampwidth()
        sample_rate = reader.getframerate()
        frame_count = reader.getnframes()
        frames = reader.readframes(frame_count)
    if sample_width != 2:
        raise ValueError(f"只支持 PCM16 WAV，当前采样宽度为 {sample_width * 8} bit。")
    waveform = torch.frombuffer(bytearray(frames), dtype=torch.int16).float() / 32768.0
    waveform = waveform.reshape(-1, channels).transpose(0, 1).contiguous().unsqueeze(0)
    return {"waveform": waveform, "sample_rate": sample_rate}
