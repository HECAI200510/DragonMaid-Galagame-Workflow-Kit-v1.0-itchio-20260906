from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREFIX = "window.DRAGON_MAID_STORY = "
CATALOG_PATH = ROOT / "assets" / "audio" / "voice_emotion" / "emotion_voice_manifest.json"


def load_story(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith(PREFIX) or not text.endswith(";"):
        raise ValueError(f"Unexpected story wrapper: {path}")
    return json.loads(text[len(PREFIX):-1])


def cue(character_id: str, suffix: str) -> str:
    return f"assets/audio/voice_emotion/{character_id}/ev_{character_id}_{suffix}.wav"


def choose_primary(character_id: str, text: str, scene_index: int, main_count: int, is_defeat: bool) -> tuple[str, str, str]:
    lowered = text.replace(" ", "")
    progress = scene_index / max(1, main_count - 1)
    if re.search(r"哭腔|哭|泪|湿润的眼睛|眼睛湿润", lowered):
        suffix = "shame_sob_01" if character_id in {"xiahei", "xiaohong"} else "bashful_cry_01"
        return suffix, "cry", "正文或画面描述含哭腔、泪意或羞愧"
    if re.search(r"惊叫|啊啊——|突然|瞪大眼睛|猛地", lowered) and is_defeat:
        return "climax_cry_01", "scream", "突发高强度战败画面"
    if re.search(r"第[一二三四五六七八九十]+次高潮|剧烈高潮|高潮来得|又要去了|又去了|去了！|喷出", lowered):
        if progress >= 0.55 or is_defeat or re.search(r"剧烈|又要|接连|汹涌", lowered):
            return "climax_cry_01", "scream", "高潮或强烈失控画面"
        return ("rising_moan_02" if scene_index % 2 else "rising_moan_01"), "moan", "高潮上升阶段"
    if re.search(r"喘息|呼吸乱|呼吸.*加快|急促|疯狂|一晃一晃", lowered):
        return ("heavy_pant_02" if scene_index % 2 else "heavy_pant_01"), "pant", "正文明确描述急促或凌乱呼吸"
    if re.search(r"羞耻|脸颊.*红|耳尖微红|不敢看|犹豫|生涩|慌|颤了一下", lowered):
        return ("shy_gasp_02" if scene_index % 2 else "shy_gasp_01"), "shy", "害羞、迟疑或受惊画面"
    if re.search(r"痉挛|颤抖|轻轻颤|抽搐|失焦|迷离|软了|撑不住|要输了", lowered) or progress >= 0.68:
        return ("rising_moan_02" if scene_index % 2 else "heavy_pant_02"), "overwhelmed", "后段失控、颤抖或体力不支"
    if progress >= 0.35:
        return ("restrained_moan_02" if scene_index % 2 else "restrained_moan_01"), "restrained", "中段压抑反应"
    if character_id == "xiahei" or re.search(r"温柔|轻轻|小心翼翼", lowered):
        return ("soft_breath_02" if scene_index % 2 else "soft_breath_01"), "soft", "前段轻柔或内向反应"
    return ("shy_gasp_02" if scene_index % 2 else "soft_breath_01"), "opening", "前段试探性反应"


def choose_secondary(primary: str, scene_index: int, text: str, is_defeat: bool) -> str | None:
    if primary in {"climax_cry_01", "rising_moan_01", "rising_moan_02", "bashful_cry_01", "shame_sob_01"}:
        return "heavy_pant_02" if scene_index % 2 else "heavy_pant_01"
    if is_defeat and re.search(r"进入|撞击|释放|抽插|捅", text):
        return "rising_moan_02"
    return None


def bind(story: dict, valid_paths: set[str]) -> tuple[dict, list[dict]]:
    plan: list[dict] = []
    for character in story.get("characters", []):
        character_id = character["id"]
        main_count = int(character.get("defeatStartIndex") or len(character.get("scenes", [])))
        for scene_index, scene in enumerate(character.get("scenes", [])):
            lines = scene.get("lines", [])
            audio = scene.setdefault("audio", {})
            voices = list(audio.get("voice") or [])
            voices += [None] * (len(lines) - len(voices))
            available = [index for index in range(len(lines)) if not voices[index]]
            if not available:
                available = [max(0, len(lines) - 1)]
            is_defeat = scene_index >= main_count
            full_text = " ".join(lines)
            primary_suffix, emotion_group, reason = choose_primary(character_id, full_text, scene_index, main_count, is_defeat)
            primary_path = cue(character_id, primary_suffix)
            if primary_path not in valid_paths:
                raise ValueError(f"Missing generated emotion voice: {primary_path}")
            emotion_voice = [None] * len(lines)
            primary_line = available[0] if emotion_group in {"scream", "shy", "opening"} else available[-1]
            emotion_voice[primary_line] = primary_path
            bindings = [{"lineIndex": primary_line + 1, "cue": primary_suffix, "path": primary_path}]
            secondary_suffix = choose_secondary(primary_suffix, scene_index, full_text, is_defeat)
            secondary_candidates = [index for index in available if index != primary_line]
            if secondary_suffix and secondary_candidates:
                secondary_path = cue(character_id, secondary_suffix)
                if secondary_path not in valid_paths:
                    raise ValueError(f"Missing generated emotion voice: {secondary_path}")
                secondary_line = secondary_candidates[-1]
                emotion_voice[secondary_line] = secondary_path
                bindings.append({"lineIndex": secondary_line + 1, "cue": secondary_suffix, "path": secondary_path})
            audio["emotionVoice"] = emotion_voice
            plan.append({
                "characterId": character_id,
                "sceneId": scene["id"],
                "image": scene.get("img"),
                "branch": "playerDefeat" if is_defeat else "main",
                "emotionGroup": emotion_group,
                "reason": reason,
                "bindings": bindings,
            })
    binding_count = sum(len(item["bindings"]) for item in plan)
    story.setdefault("audio", {}).setdefault("volumes", {})["vocal"] = 0.68
    story["audio"]["profileId"] = "jp-default-soft-galgame-cc0-emotion-v21"
    story["releaseVersion"] = "2.1"
    story["emotionVoicePack"] = {
        "version": 1,
        "language": "ja",
        "generatedCount": len(valid_paths),
        "sceneCoverage": len(plan),
        "bindingCount": binding_count,
        "catalog": "data/emotion_voice_catalog.js",
        "plan": "data/emotion_voice_plan.json",
        "defaultVolume": 0.68,
        "formalDialoguePreserved": True,
        "technicalStatus": "pending-validation",
        "subjectiveListeningStatus": "pending-human-review",
    }
    return story, plan


def main() -> int:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    valid_paths = {sound["path"] for sound in catalog["sounds"]}
    runtime, plan = bind(load_story(ROOT / "data" / "story.js"), valid_paths)
    example, _ = bind(json.loads((ROOT / "data" / "story.example.json").read_text(encoding="utf-8")), valid_paths)
    (ROOT / "data" / "story.js").write_text(PREFIX + json.dumps(runtime, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    (ROOT / "data" / "story.example.json").write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "data" / "emotion_voice_plan.json").write_text(json.dumps({"version": "2.1", "scenes": plan}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    group_counts = Counter(item["emotionGroup"] for item in plan)
    binding_count = sum(len(item["bindings"]) for item in plan)
    print(json.dumps({"scenes": len(plan), "bindings": binding_count, "groups": group_counts}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
