from __future__ import annotations

import json
import time

from .voice_core import (
    DEFAULT_OUTPUT_ROOT,
    EMOTIONS,
    LANGUAGES,
    ROLE_PRESETS,
    ROLE_SAMPLE_TEXTS,
    synthesize_role,
    wav_to_comfy_audio,
)


class DragonMaidVoiceTTS:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "角色": (list(ROLE_PRESETS), {"default": "管家"}),
                "中文文案": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": ROLE_SAMPLE_TEXTS["管家"]["中文"],
                        "tooltip": "仅供“生成语言=中文”时使用。",
                    },
                ),
                "日语文案": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": ROLE_SAMPLE_TEXTS["管家"]["日语"],
                        "tooltip": "仅供“生成语言=日语”时使用；不会复用中文文案。",
                    },
                ),
                "英语文案": (
                    "STRING",
                    {
                        "multiline": True,
                        "default": ROLE_SAMPLE_TEXTS["管家"]["英语"],
                        "tooltip": "仅供“生成语言=英语”时使用；不会复用中文文案。",
                    },
                ),
                "生成语言": (list(LANGUAGES), {"default": "中文"}),
                "情绪": (list(EMOTIONS), {"default": "平静"}),
                "语速": ("FLOAT", {"default": 0.94, "min": 0.75, "max": 1.35, "step": 0.01}),
                "情绪强度": ("FLOAT", {"default": 1.0, "min": 0.25, "max": 1.75, "step": 0.05}),
                "目标响度_LUFS": ("FLOAT", {"default": -16.0, "min": -20.0, "max": -12.0, "step": 1.0}),
                "种子": ("INT", {"default": 20260824, "min": 0, "max": 0x7FFFFFFF}),
                "使用RVC": (
                    "BOOLEAN",
                    {
                        "default": False,
                        "label_on": "Qwen→RVC（慢速）",
                        "label_off": "仅Qwen原声",
                        "tooltip": "RVC 首次加载可能持续数分钟；批量文字配音建议保持关闭。",
                    },
                ),
                "输出根目录": (
                    "STRING",
                    {
                        "default": str(DEFAULT_OUTPUT_ROOT),
                        "tooltip": "会自动按角色、语言和情绪分文件夹。",
                    },
                ),
                "文件名前缀": ("STRING", {"default": "line"}),
            }
        }

    RETURN_TYPES = ("AUDIO", "STRING", "STRING")
    RETURN_NAMES = ("音频", "WAV路径", "生成记录JSON")
    FUNCTION = "generate"
    CATEGORY = "DragonMaid/配音"
    DESCRIPTION = "调用本地 Qwen3-TTS 七角色预设，可选 RVC，并自动完成语速与响度处理。"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        return time.time_ns()

    def generate(self, **values):
        language = values["生成语言"]
        text_key = {"中文": "中文文案", "日语": "日语文案", "英语": "英语文案"}[language]
        text = str(values[text_key]).strip()
        if not text:
            raise ValueError(f"{text_key}为空，不能生成{language}音频。")
        result = synthesize_role(
            text=text,
            role=values["角色"],
            language=language,
            emotion=values["情绪"],
            speed=values["语速"],
            emotion_strength=values["情绪强度"],
            target_lufs=values["目标响度_LUFS"],
            seed=values["种子"],
            use_rvc=values["使用RVC"],
            output_root=values["输出根目录"],
            filename_prefix=values["文件名前缀"],
        )
        audio = wav_to_comfy_audio(result.output_path)
        return audio, str(result.output_path), json.dumps(result.metadata, ensure_ascii=False, indent=2)


NODE_CLASS_MAPPINGS = {"DragonMaidVoiceTTS": DragonMaidVoiceTTS}
NODE_DISPLAY_NAME_MAPPINGS = {"DragonMaidVoiceTTS": "龙女仆｜三份独立文案配音"}
