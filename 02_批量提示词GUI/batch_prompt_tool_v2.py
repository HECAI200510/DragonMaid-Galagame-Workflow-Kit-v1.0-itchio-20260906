from __future__ import annotations

import copy
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
import uuid
import webbrowser
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "batch_config_v2.json"
RUNS_DIR = APP_DIR / "runs_v2"
DEFAULT_WORKFLOW_ROOTS = tuple(
    path
    for path in (
        Path(os.environ["COMFYUI_WORKFLOWS_DIR"]).expanduser()
        if os.environ.get("COMFYUI_WORKFLOWS_DIR")
        else None,
        APP_DIR / "workflows_ui",
        Path(os.environ["DRAGONMAID_WORKSPACE"]).expanduser()
        if os.environ.get("DRAGONMAID_WORKSPACE")
        else None,
    )
    if path is not None
)
ROLE_ORDER = ["管家", "小红", "小绿", "小蓝", "小粉", "小金", "小黑", "通用"]
POSITION_ORDER = ["左上", "中上", "右上", "左中", "正中", "右中", "左下", "中下", "右下"]
ROLE_LORAS = {
    "管家": (r"dragonmaid_historical_recommended_v1\01_管家_Hasuki-pilot20-历史推荐-r32.safetensors", 0.72),
    "小红": (r"dragonmaid_public_illustrious_v4\02_Kitchen_dragonmaid_illuXL_v1.1.safetensors", 0.76),
    "小绿": (r"dragonmaid_public_illustrious_v4\03_Parlor_dragonmaid_illuXL_v1.1.safetensors", 0.76),
    "小蓝": (r"dragonmaid_historical_recommended_v1\04_小蓝_Laundry-pilot20-SFW历史推荐-r32.safetensors", 0.70),
    "小粉": (r"dragonmaid_historical_recommended_v1\05_小粉_Nasary-pilot20-历史推荐-r32.safetensors", 0.72),
    "小金": (r"dragonmaid_public_illustrious_v4\06_Latys_dragonmaid_illuXL_v2.safetensors", 0.76),
    "小黑": (r"dragonmaid_public_illustrious_v4\07_Chamber_dragonmaid_illuXL_v1.1.safetensors", 0.76),
}
ROLE_IDENTITY_PROMPTS = {
    "管家": "house dragonmaid, glasses, long dark brown hair, black curved horns, black formal maid uniform, attached dark feathered dragon tail",
    "小红": "kitchen dragonmaid, long red hair, cyan dragon horns, red dragon tail, brown maid clothes, white apron",
    "小绿": "parlor dragonmaid, short green hair, twin-tail silhouette, green dragon horns, leafy green dragon tail, black and white maid uniform",
    "小蓝": "laundry dragonmaid, short blue hair, small dragon horns, fluffy blue eastern dragon tail, modest maid outfit, SFW",
    "小粉": "nurse dragonmaid, pink hair, curled ram-like horns, pink dragon tail, pink and white nurse maid uniform",
    "小金": "golden dragonmaid, blonde hair, noble elegant maid, golden dragon horns, golden dragon tail",
    "小黑": "chamber dragonmaid, long white hair, black horns, black bedroom maid uniform, dark feathered dragon tail",
}
POSITION_AREAS = {
    "左上": (0.48, 0.56, 0.00, 0.00), "中上": (0.48, 0.56, 0.26, 0.00), "右上": (0.48, 0.56, 0.52, 0.00),
    "左中": (0.48, 0.56, 0.00, 0.22), "正中": (0.48, 0.56, 0.26, 0.22), "右中": (0.48, 0.56, 0.52, 0.22),
    "左下": (0.48, 0.56, 0.00, 0.44), "中下": (0.48, 0.56, 0.26, 0.44), "右下": (0.48, 0.56, 0.52, 0.44),
}
PANEL_FIELDS = (
    "通用提示词",
    "表情提示词",
    "动作提示词",
    "形象提示词",
    "穿着提示词",
    "分镜提示词",
)


@dataclass
class PromptEntry:
    number: str
    text: str


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_prompt(text: str) -> str:
    text = text.strip().strip("`").strip()
    text = re.sub(r"^\s*(?:prompt|提示词|正面提示词)\s*[:：]\s*", "", text, flags=re.I)
    lines = []
    in_fence = False
    for raw in text.replace("\r\n", "\n").splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not line:
            continue
        line = re.sub(r"^[-*+]\s+", "", line)
        lines.append(line)
    return " ".join(lines).strip(" ,\t\r\n")


def consecutive_numbers(entries: list[PromptEntry]) -> list[int] | None:
    """Return numeric IDs when entries form a strict ascending consecutive run."""
    if not entries:
        return None
    try:
        numbers = [int(str(item.number).strip()) for item in entries]
    except ValueError:
        return None
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    return numbers if numbers == expected else None


def renumber_entries(entries: list[PromptEntry], start: int = 1) -> list[PromptEntry]:
    """Create a copy numbered by local order; original source data is untouched."""
    return [PromptEntry(str(start + index), item.text) for index, item in enumerate(entries)]


def smart_align_two_documents(
    left: list[PromptEntry], right: list[PromptEntry]
) -> tuple[list[PromptEntry], list[PromptEntry], str | None]:
    """Normalize offset sequences and recognize a full document + suffix split."""
    left_numbers = consecutive_numbers(left)
    right_numbers = consecutive_numbers(right)
    if left_numbers is None or right_numbers is None:
        return left, right, None

    # Example: A contains 1..200 while B is the copied second group 101..200.
    if len(left) > len(right) and left_numbers[-len(right):] == right_numbers:
        prefix = left[:-len(right)]
        if len(prefix) == len(right) and consecutive_numbers(prefix) is not None:
            return (
                renumber_entries(prefix),
                renumber_entries(right),
                f"识别到角色A包含前后两组：已取A前{len(prefix)}条；角色B的{right_numbers[0]}～{right_numbers[-1]}已重排为1～{len(right)}。",
            )
    if len(right) > len(left) and right_numbers[-len(left):] == left_numbers:
        prefix = right[:-len(left)]
        if len(prefix) == len(left) and consecutive_numbers(prefix) is not None:
            return (
                renumber_entries(left),
                renumber_entries(prefix),
                f"识别到角色B包含前后两组：已取B前{len(prefix)}条；两边已重排为1～{len(left)}。",
            )

    # Same logical number of images, even when one file starts at 101 or another offset.
    if len(left) == len(right):
        left_start, right_start = left_numbers[0], right_numbers[0]
        normalized_left = renumber_entries(left)
        normalized_right = renumber_entries(right)
        if left_start != 1 or right_start != 1:
            return (
                normalized_left,
                normalized_right,
                f"检测到两份连续序列起点为{left_start}和{right_start}；已按各自顺序统一重排为1～{len(left)}。",
            )
        return normalized_left, normalized_right, None
    return left, right, None


NUMBERED_LINE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?P<number>\d{1,5})\s*(?:[.．、:：)]|\-\s+)\s*(?P<body>.*)$"
)


def parse_numbered_markdown(text: str) -> list[PromptEntry]:
    """Parse `1. prompt` blocks; continuation lines belong to the previous number."""
    entries: list[PromptEntry] = []
    current_number: str | None = None
    current_lines: list[str] = []

    def flush():
        nonlocal current_number, current_lines
        if current_number is None:
            return
        value = normalize_prompt("\n".join(current_lines))
        if value:
            entries.append(PromptEntry(current_number, value))
        current_number = None
        current_lines = []

    for raw in text.replace("\r\n", "\n").splitlines():
        match = NUMBERED_LINE.match(raw)
        if match:
            flush()
            current_number = match.group("number")
            current_lines = [match.group("body")]
        elif current_number is not None:
            current_lines.append(raw)
    flush()

    # Some prompt documents are written as `1.xxx，2.xxx，3.xxx` on one line.
    # Prefer this parse only when it finds more numbered items than the line parser.
    inline_pattern = re.compile(r"(?:^|[\s,，;；])(?P<number>\d{1,5})\s*[.．、)]\s*")
    matches = list(inline_pattern.finditer(text))
    inline_entries: list[PromptEntry] = []
    if len(matches) >= 2:
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            value = normalize_prompt(text[match.end():end])
            if value:
                inline_entries.append(PromptEntry(match.group("number"), value))
    return inline_entries if len(inline_entries) > len(entries) else entries


def parse_prompt_document(text: str) -> tuple[list[PromptEntry], str]:
    numbered = parse_numbered_markdown(text)
    if numbered:
        return numbered, "编号段落"
    blocks = [normalize_prompt(x) for x in re.split(r"\n\s*\n+|^\s*---+\s*$", text, flags=re.M)]
    blocks = [x for x in blocks if x]
    return [PromptEntry(str(i), value) for i, value in enumerate(blocks, 1)], "空行/分隔线"


def combine_prompt(prefix: str, suffix: str) -> str:
    prefix = prefix.strip(" ,\t\r\n")
    suffix = suffix.strip(" ,\t\r\n")
    if not prefix:
        return suffix
    if not suffix:
        return prefix
    return f"{prefix}, {suffix}"


def combine_prompt_parts(prefix: str, body: str, postfix: str) -> str:
    return combine_prompt(combine_prompt(prefix, body), postfix)


CORE_WIDGETS = {
    "CheckpointLoaderSimple": ("ckpt_name",),
    "LoraLoader": ("lora_name", "strength_model", "strength_clip"),
    "CLIPTextEncode": ("text",),
    "EmptyLatentImage": ("width", "height", "batch_size"),
    "VAEDecode": (),
    "VAEEncode": (),
    "SaveImage": ("filename_prefix",),
    "PreviewImage": (),
    "LoadImage": ("image",),
    "ControlNetLoader": ("control_net_name",),
    "CLIPVisionLoader": ("clip_name",),
    "RepeatLatentBatch": ("amount",),
    "DragonMaidPromptPanel": PANEL_FIELDS,
    "DragonMaidVideoPanel": (
        "视频秒数",
        "目标帧率FPS",
        "宽度px",
        "高度px",
        "首帧编号",
        "尾帧编号_负1自动",
        "生成关键帧张数",
    ),
}


def convert_ui_workflow_to_api(data: dict) -> dict:
    if data and all(str(k).isdigit() for k in data) and all(
        isinstance(v, dict) and "class_type" in v for v in data.values()
    ):
        return copy.deepcopy(data)
    if isinstance(data.get("prompt"), dict):
        prompt = data["prompt"]
        if all(isinstance(v, dict) and "class_type" in v for v in prompt.values()):
            return copy.deepcopy(prompt)
    if "nodes" not in data or "links" not in data:
        raise ValueError("不是 ComfyUI UI 工作流，也不是 API Format 工作流。")

    links = {}
    for link in data.get("links", []):
        if isinstance(link, list) and len(link) >= 6:
            links[int(link[0])] = [str(link[1]), int(link[2])]

    result = {}
    unsupported = []
    for node in data.get("nodes", []):
        if int(node.get("mode", 0)) in (2, 4):
            continue
        node_id = str(node["id"])
        class_type = node["type"]
        inputs = {}
        for item in node.get("inputs") or []:
            link_id = item.get("link")
            if link_id is not None and int(link_id) in links:
                inputs[item["name"]] = links[int(link_id)]

        values = list(node.get("widgets_values") or [])
        if class_type == "KSampler":
            if len(values) < 7:
                raise ValueError(f"KSampler 节点 {node_id} 参数不足。")
            inputs.update(
                seed=int(values[0]),
                steps=int(values[2]),
                cfg=float(values[3]),
                sampler_name=values[4],
                scheduler=values[5],
                denoise=float(values[6]),
            )
        elif class_type in CORE_WIDGETS:
            names = CORE_WIDGETS[class_type]
            if len(values) < len(names):
                raise ValueError(f"节点 {node_id} ({class_type}) 参数不足。")
            inputs.update(dict(zip(names, values)))
        elif values:
            unsupported.append(f"{node_id}:{class_type}")

        result[node_id] = {
            "inputs": inputs,
            "class_type": class_type,
            "_meta": {"title": node.get("title") or class_type},
        }
    if unsupported:
        raise ValueError(
            "无法安全转换这些自定义节点："
            + ", ".join(unsupported)
            + "。请从 ComfyUI 导出 API Format JSON 再导入。"
        )
    return result


def load_api_workflow(path: Path) -> dict:
    return convert_ui_workflow_to_api(read_json(path))


def find_prompt_targets(prompt: dict) -> list[tuple[str, str, str]]:
    targets: list[tuple[str, str, str]] = []
    for node_id, node in prompt.items():
        class_type = node.get("class_type", "")
        title = str((node.get("_meta") or {}).get("title", ""))
        if class_type == "DragonMaidPromptPanel":
            for field in PANEL_FIELDS:
                targets.append((f"六栏面板 · {field}（节点 {node_id}）", node_id, field))
        elif class_type == "CLIPTextEncode":
            lowered = title.lower()
            if "负面" not in title and "negative" not in lowered:
                targets.append((f"正面编码器 · {title or 'CLIPTextEncode'}（节点 {node_id}）", node_id, "text"))
    return targets


def find_runtime_nodes(prompt: dict):
    samplers, latents, saves = [], [], []
    for node_id, node in prompt.items():
        kind = node.get("class_type", "")
        if kind in ("KSampler", "KSamplerAdvanced"):
            samplers.append(node_id)
        elif kind == "EmptyLatentImage":
            latents.append(node_id)
        elif kind in ("SaveImage", "SaveAnimatedWEBP"):
            saves.append(node_id)
    return samplers, latents, saves


def api_get(url: str, timeout: int = 5):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def api_post(url: str, payload: dict, timeout: int = 20):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def pair_entries_by_number(
    left: list[PromptEntry], right: list[PromptEntry]
) -> list[tuple[PromptEntry, PromptEntry]]:
    """Strictly pair two prompt documents by their visible image number."""
    def build_index(items: list[PromptEntry], label: str) -> dict[str, PromptEntry]:
        result: dict[str, PromptEntry] = {}
        duplicates = []
        for item in items:
            key = str(item.number).strip()
            if key in result:
                duplicates.append(key)
            result[key] = item
        if duplicates:
            raise ValueError(f"{label} 存在重复编号：{', '.join(sorted(set(duplicates)))}")
        return result

    left_index = build_index(left, "角色A文档")
    right_index = build_index(right, "角色B文档")
    missing_right = [key for key in left_index if key not in right_index]
    missing_left = [key for key in right_index if key not in left_index]
    if missing_right or missing_left:
        parts = []
        if missing_right:
            parts.append("角色B缺少：" + ", ".join(missing_right[:20]))
        if missing_left:
            parts.append("角色A缺少：" + ", ".join(missing_left[:20]))
        raise ValueError("两份 MD 编号无法配对；" + "；".join(parts))
    return [(item, right_index[str(item.number).strip()]) for item in left]


def align_prompt_documents(documents: list[list[PromptEntry]]) -> list[list[PromptEntry]]:
    if len(documents) < 2:
        raise ValueError("多人模式至少需要两份提示词文档。")
    base = documents[0]
    aligned = [[item] for item in base]
    for other in documents[1:]:
        pairs = pair_entries_by_number(base, other)
        for index, (_, matched) in enumerate(pairs):
            aligned[index].append(matched)
    return aligned


def build_dynamic_region_workflow(base: dict, participants: list[dict]) -> tuple[dict, list[str]]:
    """Build a core API workflow with one regional prompt + LoRA hook per participant."""
    if not 2 <= len(participants) <= 6:
        raise ValueError("动态区域工作流支持 2～6 名角色。")
    for item in participants:
        if item["role"] not in ROLE_LORAS:
            raise ValueError(f"角色 {item['role']} 没有可用的区域 LoRA 映射。")
        if item["position"] not in POSITION_AREAS:
            raise ValueError(f"未知九宫格位置：{item['position']}")

    checkpoint = next((copy.deepcopy(n) for n in base.values() if n.get("class_type") == "CheckpointLoaderSimple"), None)
    positive = next((copy.deepcopy(n) for n in base.values() if n.get("class_type") == "CLIPTextEncode" and "共同画面" in str((n.get("_meta") or {}).get("title", ""))), None)
    negative = next((copy.deepcopy(n) for n in base.values() if n.get("class_type") == "CLIPTextEncode" and ("负面" in str((n.get("_meta") or {}).get("title", "")) or "negative" in str((n.get("_meta") or {}).get("title", "")).lower())), None)
    sampler_source = next((copy.deepcopy(n) for n in base.values() if n.get("class_type") in ("KSampler", "KSamplerAdvanced")), None)
    latent_source = next((copy.deepcopy(n) for n in base.values() if n.get("class_type") == "EmptyLatentImage"), None)
    if not all((checkpoint, positive, negative, sampler_source, latent_source)):
        raise ValueError("所选多人工作流缺少底模、共同画面、负面、采样器或画布节点。")

    workflow = {"1": checkpoint, "2": positive, "3": negative}
    workflow["2"]["inputs"]["clip"] = ["1", 1]
    workflow["3"]["inputs"]["clip"] = ["1", 1]
    common = str(workflow["2"]["inputs"].get("text", ""))
    common = re.sub(r"\b[2-9]girls\b", "", common)
    common = re.sub(r"exactly\s+(?:two|three|four|five|six|[2-6])\s+(?:adult\s+)?(?:women|girls|characters)", "", common, flags=re.I)
    workflow["2"]["inputs"]["text"] = combine_prompt(common, f"{len(participants)}girls, exactly {len(participants)} characters")
    negative_text = str(workflow["3"]["inputs"].get("text", ""))
    negative_text = re.sub(r"(?:^|,\s*)(?:solo|1girl|4girls|extra person)(?=\s*,|$)", "", negative_text, flags=re.I)
    workflow["3"]["inputs"]["text"] = combine_prompt(negative_text, "wrong number of characters")

    previous_condition = "2"
    prompt_ids = []
    next_id = 10
    for index, participant in enumerate(participants):
        letter = chr(ord("A") + index)
        prompt_id, area_id, hook_id, combine_id = map(str, range(next_id, next_id + 4))
        next_id += 4
        prompt_ids.append(prompt_id)
        width, height, x, y = POSITION_AREAS[participant["position"]]
        lora_name, weight = ROLE_LORAS[participant["role"]]
        workflow[prompt_id] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": ROLE_IDENTITY_PROMPTS[participant["role"]], "clip": ["1", 1]},
            "_meta": {"title": f"角色{letter} · {participant['role']} · {participant['position']} · MD动态写入"},
        }
        workflow[area_id] = {
            "class_type": "ConditioningSetAreaPercentage",
            "inputs": {"width": width, "height": height, "x": x, "y": y, "strength": 1.15, "conditioning": [prompt_id, 0]},
            "_meta": {"title": f"九宫格区域 · 角色{letter} · {participant['position']}"},
        }
        workflow[hook_id] = {
            "class_type": "CreateHookLoraModelOnly",
            "inputs": {"lora_name": lora_name, "strength_model": weight},
            "_meta": {"title": f"区域LoRA · 角色{letter} · {participant['role']}"},
        }
        workflow[combine_id] = {
            "class_type": "ConditioningSetPropertiesAndCombine",
            "inputs": {"strength": 1.0, "set_cond_area": "default", "cond": [previous_condition, 0], "cond_NEW": [area_id, 0], "hooks": [hook_id, 0]},
            "_meta": {"title": f"合并角色{letter}区域条件"},
        }
        previous_condition = combine_id

    latent_id, sampler_id, decode_id, save_id = map(str, range(next_id, next_id + 4))
    workflow[latent_id] = latent_source
    workflow[latent_id]["inputs"]["batch_size"] = 1
    sampler_inputs = sampler_source["inputs"]
    sampler_inputs["model"] = ["1", 0]
    sampler_inputs["positive"] = [previous_condition, 0]
    sampler_inputs["negative"] = ["3", 0]
    sampler_inputs["latent_image"] = [latent_id, 0]
    workflow[sampler_id] = sampler_source
    workflow[decode_id] = {"class_type": "VAEDecode", "inputs": {"samples": [sampler_id, 0], "vae": ["1", 2]}, "_meta": {"title": "VAE 解码"}}
    workflow[save_id] = {"class_type": "SaveImage", "inputs": {"filename_prefix": "DragonMaid/MD_Multi", "images": [decode_id, 0]}, "_meta": {"title": "保存多人批处理输出"}}
    return workflow, prompt_ids


class BatchPromptAppV2:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("龙女仆 ComfyUI · Markdown 批量提示词工具 V4（单人/2～6人九宫格）")
        self.root.geometry("1280x860")
        self.root.minsize(1050, 720)
        self.config = self.load_config()
        self.entries: list[PromptEntry] = []
        self.entries_b: list[PromptEntry] = []
        self.extra_participants: list[dict] = []
        self.targets: list[tuple[str, str, str]] = []
        self.stop_event = threading.Event()
        self.build_ui()
        self.restore_config()
        self.refresh_workflow_list()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_config(self):
        if CONFIG_PATH.exists():
            try:
                return read_json(CONFIG_PATH)
            except Exception:
                pass
        return {}

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10, "bold"))

        server = ttk.Frame(self.root, padding=(12, 10))
        server.pack(fill="x")
        ttk.Label(server, text="ComfyUI").pack(side="left")
        self.server_var = tk.StringVar(value="http://127.0.0.1:8188")
        ttk.Entry(server, textvariable=self.server_var, width=34).pack(side="left", padx=6)
        ttk.Button(server, text="检测连接", command=self.test_connection).pack(side="left")
        ttk.Button(server, text="打开 ComfyUI", command=lambda: webbrowser.open(self.server_var.get())).pack(side="left", padx=5)
        ttk.Label(server, text="角色").pack(side="left", padx=(18, 4))
        self.role_var = tk.StringVar(value="通用")
        ttk.Combobox(server, textvariable=self.role_var, values=ROLE_ORDER, state="readonly", width=8).pack(side="left")
        ttk.Label(server, text="角色B").pack(side="left", padx=(10, 4))
        self.role_b_var = tk.StringVar(value="通用")
        ttk.Combobox(server, textvariable=self.role_b_var, values=ROLE_ORDER, state="readonly", width=8).pack(side="left")
        self.status_var = tk.StringVar(value="请选择工作流并导入 Markdown")
        ttk.Label(server, textvariable=self.status_var).pack(side="right")

        wf = ttk.LabelFrame(self.root, text="1. 选择 ComfyUI 工作流 JSON", padding=9)
        wf.pack(fill="x", padx=12, pady=(0, 8))
        self.workflow_var = tk.StringVar()
        self.workflow_combo = ttk.Combobox(wf, textvariable=self.workflow_var)
        self.workflow_combo.pack(side="left", fill="x", expand=True)
        ttk.Button(wf, text="浏览…", command=self.choose_workflow).pack(side="left", padx=5)
        ttk.Button(wf, text="扫描最近工作流", command=self.refresh_workflow_list).pack(side="left")
        ttk.Button(wf, text="检查并读取提示词栏", command=self.inspect_workflow).pack(side="left", padx=(5, 0))

        prompt_frame = ttk.LabelFrame(self.root, text="2. 导入 Markdown：单人用角色A；双人模式再导入角色B", padding=9)
        prompt_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))
        toolbar = ttk.Frame(prompt_frame)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="导入角色A MD/TXT", command=self.import_document).pack(side="left")
        ttk.Button(toolbar, text="粘贴为角色A", command=self.paste_and_parse).pack(side="left", padx=5)
        ttk.Button(toolbar, text="导入角色B MD/TXT", command=self.import_document_b).pack(side="left")
        self.b_count_var = tk.StringVar(value="角色B：未导入")
        ttk.Button(toolbar, text="查看/编辑角色B", command=self.open_b_editor).pack(side="left", padx=5)
        ttk.Label(toolbar, textvariable=self.b_count_var).pack(side="left", padx=5)
        ttk.Button(toolbar, text="删除选中", command=self.remove_selected).pack(side="left")
        ttk.Button(toolbar, text="清空", command=self.clear_entries).pack(side="left", padx=5)
        ttk.Label(toolbar, text="双击一行可修改提示词；编号不必连续").pack(side="right")

        searchbar = ttk.Frame(prompt_frame)
        searchbar.pack(fill="x", pady=(7, 0))
        ttk.Label(searchbar, text="批量查找").pack(side="left")
        self.find_var = tk.StringVar()
        ttk.Entry(searchbar, textvariable=self.find_var, width=26).pack(side="left", padx=(5, 8))
        ttk.Label(searchbar, text="替换为").pack(side="left")
        self.replace_var = tk.StringVar()
        ttk.Entry(searchbar, textvariable=self.replace_var, width=26).pack(side="left", padx=(5, 8))
        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(searchbar, text="区分大小写", variable=self.case_sensitive_var).pack(side="left")
        ttk.Button(searchbar, text="查找全部", command=self.find_all).pack(side="left", padx=(8, 3))
        ttk.Button(searchbar, text="全部替换", command=self.replace_all).pack(side="left", padx=3)
        ttk.Button(searchbar, text="删除匹配文字", command=self.delete_matches).pack(side="left", padx=3)
        ttk.Button(searchbar, text="删除命中条目", command=self.delete_matching_entries).pack(side="left", padx=3)

        numberbar = ttk.Frame(prompt_frame)
        numberbar.pack(fill="x", pady=(6, 0))
        ttk.Label(numberbar, text="编号修复").pack(side="left")
        ttk.Button(numberbar, text="角色A从1重新编号", command=self.renumber_a).pack(side="left", padx=(6, 3))
        ttk.Button(numberbar, text="角色B从1重新编号", command=self.renumber_b).pack(side="left", padx=3)
        ttk.Button(numberbar, text="智能识别并对齐A/B", command=lambda: self.smart_align_ab(show_if_no_match=True)).pack(side="left", padx=3)
        ttk.Label(numberbar, text="仅修改当前导入列表，不改原始MD；严格连续的101～200会变成1～100。", foreground="#555").pack(side="left", padx=10)

        self.table = ttk.Treeview(prompt_frame, columns=("number", "chars", "prompt"), show="headings", height=14)
        self.table.heading("number", text="图片编号")
        self.table.heading("chars", text="字符数")
        self.table.heading("prompt", text="提示词预览")
        self.table.column("number", width=90, anchor="center", stretch=False)
        self.table.column("chars", width=80, anchor="center", stretch=False)
        self.table.column("prompt", width=900)
        scrollbar = ttk.Scrollbar(prompt_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True, pady=(8, 0))
        scrollbar.pack(side="right", fill="y", pady=(8, 0))
        self.table.bind("<Double-1>", self.edit_selected)

        compose = ttk.LabelFrame(self.root, text="3. 拼接与写入位置", padding=9)
        compose.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(compose, text="所有图片统一添加到开头").grid(row=0, column=0, sticky="w")
        self.prefix_text = tk.Text(compose, height=4, wrap="word", undo=True)
        self.prefix_text.grid(row=1, column=0, columnspan=8, sticky="ew", pady=(4, 7))
        ttk.Label(compose, text="所有图片统一添加到末尾").grid(row=2, column=0, sticky="w")
        self.postfix_text = tk.Text(compose, height=3, wrap="word", undo=True)
        self.postfix_text.grid(row=3, column=0, columnspan=8, sticky="ew", pady=(4, 7))
        ttk.Label(compose, text="写入正面提示词栏").grid(row=4, column=0, sticky="w")
        self.target_var = tk.StringVar()
        self.target_combo = ttk.Combobox(compose, textvariable=self.target_var, state="readonly", width=58)
        self.target_combo.grid(row=4, column=1, columnspan=3, sticky="ew", padx=(6, 15))
        self.keep_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(compose, text="保留工作流其他提示词栏", variable=self.keep_var).grid(row=4, column=4, sticky="w")
        ttk.Button(compose, text="查看前 5 条拼接结果", command=self.preview).grid(row=4, column=7, sticky="e")
        self.dual_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(compose, text="启用双人/双MD模式", variable=self.dual_mode_var, command=self.on_dual_mode_changed).grid(row=5, column=0, sticky="w", pady=(7, 0))
        ttk.Label(compose, text="角色B写入栏").grid(row=5, column=1, sticky="e", pady=(7, 0))
        self.target_b_var = tk.StringVar()
        self.target_b_combo = ttk.Combobox(compose, textvariable=self.target_b_var, state="readonly", width=52)
        self.target_b_combo.grid(row=5, column=2, columnspan=3, sticky="ew", padx=(6, 15), pady=(7, 0))
        ttk.Label(compose, text="角色B统一开头").grid(row=6, column=0, sticky="w", pady=(7, 0))
        self.prefix_b_var = tk.StringVar()
        ttk.Entry(compose, textvariable=self.prefix_b_var).grid(row=6, column=1, columnspan=3, sticky="ew", padx=(6, 15), pady=(7, 0))
        ttk.Label(compose, text="角色B统一末尾").grid(row=6, column=4, sticky="e", pady=(7, 0))
        self.postfix_b_var = tk.StringVar()
        ttk.Entry(compose, textvariable=self.postfix_b_var).grid(row=6, column=5, columnspan=3, sticky="ew", padx=(6, 0), pady=(7, 0))
        ttk.Label(compose, text="角色A位置").grid(row=7, column=0, sticky="w", pady=(7, 0))
        self.position_a_var = tk.StringVar(value="左中")
        ttk.Combobox(compose, textvariable=self.position_a_var, values=POSITION_ORDER, state="readonly", width=8).grid(row=7, column=1, sticky="w", padx=(6, 15), pady=(7, 0))
        ttk.Label(compose, text="角色B位置").grid(row=7, column=2, sticky="e", pady=(7, 0))
        self.position_b_var = tk.StringVar(value="右中")
        ttk.Combobox(compose, textvariable=self.position_b_var, values=POSITION_ORDER, state="readonly", width=8).grid(row=7, column=3, sticky="w", padx=(6, 15), pady=(7, 0))
        self.extra_count_var = tk.StringVar(value="无扩展角色")
        ttk.Button(compose, text="＋ 管理扩展角色 C～F", command=self.open_extra_participants_editor).grid(row=7, column=4, columnspan=2, sticky="ew", pady=(7, 0))
        ttk.Label(compose, textvariable=self.extra_count_var).grid(row=7, column=6, columnspan=2, sticky="w", padx=(8, 0), pady=(7, 0))
        compose.columnconfigure(3, weight=1)
        compose.columnconfigure(7, weight=1)

        options = ttk.LabelFrame(self.root, text="4. 批量参数", padding=9)
        options.pack(fill="x", padx=12, pady=(0, 8))
        ttk.Label(options, text="每个编号出图").grid(row=0, column=0)
        self.repeat_var = tk.IntVar(value=1)
        ttk.Spinbox(options, from_=1, to=20, textvariable=self.repeat_var, width=6).grid(row=0, column=1, padx=(5, 15))
        ttk.Label(options, text="种子方式").grid(row=0, column=2)
        self.seed_mode_var = tk.StringVar(value="递增")
        ttk.Combobox(options, values=("递增", "随机"), textvariable=self.seed_mode_var, state="readonly", width=8).grid(row=0, column=3, padx=5)
        ttk.Label(options, text="起始种子").grid(row=0, column=4, padx=(12, 0))
        self.seed_var = tk.StringVar(value="202608100001")
        ttk.Entry(options, textvariable=self.seed_var, width=16).grid(row=0, column=5, padx=5)
        ttk.Label(options, text="输出目录前缀").grid(row=0, column=6, padx=(12, 0))
        self.output_var = tk.StringVar(value="DragonMaid/MD_Batch")
        ttk.Entry(options, textvariable=self.output_var).grid(row=0, column=7, padx=5, sticky="ew")
        ttk.Label(options, text="提交只负责写入 ComfyUI 队列，不等待图片生成；提交结束后工具立即可继续导入。", foreground="#444").grid(row=1, column=0, columnspan=8, sticky="w", pady=(8, 0))
        options.columnconfigure(7, weight=1)

        actions = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        actions.pack(fill="x")
        ttk.Button(actions, text="导出任务包（不生图）", command=self.export_jobs).pack(side="left")
        ttk.Button(actions, text="开始批量加入 ComfyUI", style="Primary.TButton", command=self.start_queue).pack(side="left", padx=7)
        ttk.Button(actions, text="停止当前提交", command=self.stop_queue).pack(side="left")
        self.progress = ttk.Progressbar(actions, mode="determinate")
        self.progress.pack(side="right", fill="x", expand=True, padx=(20, 0))

        log_frame = ttk.LabelFrame(self.root, text="运行日志", padding=6)
        log_frame.pack(fill="both", padx=12, pady=(0, 12))
        self.log_text = tk.Text(log_frame, height=6, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    def restore_config(self):
        self.server_var.set(self.config.get("server", self.server_var.get()))
        self.workflow_var.set(self.config.get("workflow", ""))
        self.role_var.set(self.config.get("role", "通用"))
        self.role_b_var.set(self.config.get("role_b", "通用"))
        self.output_var.set(self.config.get("output_prefix", self.output_var.get()))
        self.prefix_text.insert("1.0", self.config.get("common_prefix", ""))
        self.postfix_text.insert("1.0", self.config.get("common_postfix", ""))
        self.dual_mode_var.set(bool(self.config.get("dual_mode", False)))
        self.prefix_b_var.set(self.config.get("common_prefix_b", ""))
        self.postfix_b_var.set(self.config.get("common_postfix_b", ""))
        self.position_a_var.set(self.config.get("position_a", "左中"))
        self.position_b_var.set(self.config.get("position_b", "右中"))

    def save_config(self):
        write_json(
            CONFIG_PATH,
            {
                "server": self.server_var.get().strip(),
                "workflow": self.workflow_var.get().strip(),
                "role": self.role_var.get(),
                "role_b": self.role_b_var.get(),
                "output_prefix": self.output_var.get().strip(),
                "common_prefix": self.prefix_text.get("1.0", "end").strip(),
                "common_postfix": self.postfix_text.get("1.0", "end").strip(),
                "dual_mode": bool(self.dual_mode_var.get()),
                "common_prefix_b": self.prefix_b_var.get().strip(),
                "common_postfix_b": self.postfix_b_var.get().strip(),
                "position_a": self.position_a_var.get(),
                "position_b": self.position_b_var.get(),
                "target": self.target_var.get(),
                "target_b": self.target_b_var.get(),
            },
        )

    def log(self, message: str):
        def append():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.root.after(0, append)

    def refresh_workflow_list(self):
        found = []
        for root in DEFAULT_WORKFLOW_ROOTS:
            if not root.exists():
                continue
            try:
                found.extend(root.rglob("*.json"))
            except OSError:
                continue
        found = sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)[:180]
        values = [str(p) for p in found]
        self.workflow_combo["values"] = values
        self.log(f"扫描到 {len(values)} 个最近修改的工作流 JSON。")

    def choose_workflow(self):
        path = filedialog.askopenfilename(title="选择 ComfyUI 工作流 JSON", filetypes=[("JSON", "*.json")])
        if path:
            self.workflow_var.set(path)
            self.inspect_workflow()

    def inspect_workflow(self):
        try:
            path = Path(self.workflow_var.get().strip())
            if not path.exists():
                raise FileNotFoundError(f"工作流不存在：{path}")
            prompt = load_api_workflow(path)
            self.targets = find_prompt_targets(prompt)
            if not self.targets:
                raise ValueError("没有找到可写入的正面提示词节点。")
            labels = [x[0] for x in self.targets]
            self.target_combo["values"] = labels
            self.target_b_combo["values"] = labels
            saved = self.config.get("target", "")
            preferred = next((x for x in labels if x == saved), None)
            if not preferred:
                preferred = next((x for x in labels if "通用提示词" in x), labels[0])
            self.target_var.set(preferred)
            saved_b = self.config.get("target_b", "")
            preferred_b = next((x for x in labels if x == saved_b), None)
            if not preferred_b:
                preferred_b = next((x for x in labels if "角色B" in x), labels[1] if len(labels) > 1 else labels[0])
            self.target_b_var.set(preferred_b)
            if self.dual_mode_var.get():
                preferred_a = next((x for x in labels if "角色A" in x), None)
                if preferred_a:
                    self.target_var.set(preferred_a)
            selected = self.targets[labels.index(preferred)]
            existing = str(prompt[selected[1]]["inputs"].get(selected[2], ""))
            if existing and not self.prefix_text.get("1.0", "end").strip():
                self.prefix_text.insert("1.0", existing)
            samplers, _, saves = find_runtime_nodes(prompt)
            self.status_var.set(f"工作流可用 · {len(self.targets)} 个正面栏 · {len(samplers)} 个采样器")
            self.log(f"已读取 {path.name}；保存节点 {','.join(saves) or '无'}。")
            self.save_config()
        except Exception as exc:
            messagebox.showerror("工作流检查失败", str(exc))
            self.log(f"工作流检查失败：{exc}")

    def import_document(self):
        path = filedialog.askopenfilename(
            title="导入编号提示词 Markdown",
            filetypes=[("Markdown / 文本", "*.md *.txt"), ("全部文件", "*.*")],
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = Path(path).read_text(encoding="gb18030")
        self.load_entries(text, Path(path).name)

    def import_document_b(self):
        path = filedialog.askopenfilename(
            title="导入角色B编号提示词 Markdown",
            filetypes=[("Markdown / 文本", "*.md *.txt"), ("全部文件", "*.*")],
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = Path(path).read_text(encoding="gb18030")
        entries, mode = parse_prompt_document(text)
        if not entries:
            messagebox.showerror("没有识别到角色B提示词", "请使用 `1. 提示词`、`2. 提示词` 格式。")
            return
        self.entries_b = entries
        self.b_count_var.set(f"角色B：{len(entries)} 条")
        self.dual_mode_var.set(True)
        self.on_dual_mode_changed()
        self.log(f"从 {Path(path).name} 识别角色B共 {len(entries)} 条，模式：{mode}。")
        self.smart_align_ab(show_if_no_match=False)

    def open_b_editor(self):
        win = tk.Toplevel(self.root)
        win.title("角色B提示词 · 双击编辑")
        win.geometry("1000x620")
        tree = ttk.Treeview(win, columns=("number", "chars", "prompt"), show="headings")
        tree.heading("number", text="图片编号")
        tree.heading("chars", text="字符数")
        tree.heading("prompt", text="角色B提示词")
        tree.column("number", width=90, anchor="center", stretch=False)
        tree.column("chars", width=70, anchor="center", stretch=False)
        tree.column("prompt", width=780)
        tree.pack(fill="both", expand=True, padx=10, pady=10)

        def refresh():
            tree.delete(*tree.get_children())
            for i, item in enumerate(self.entries_b):
                preview = item.text if len(item.text) <= 180 else item.text[:177] + "…"
                tree.insert("", "end", iid=str(i), values=(item.number, len(item.text), preview))
            self.b_count_var.set(f"角色B：{len(self.entries_b)} 条" if self.entries_b else "角色B：未导入")

        def edit(_event=None):
            selected = tree.selection()
            if not selected:
                return
            index = int(selected[0])
            item = self.entries_b[index]
            editor = tk.Toplevel(win)
            editor.title(f"编辑角色B第 {item.number} 条")
            editor.geometry("850x430")
            box = tk.Text(editor, wrap="word", undo=True)
            box.pack(fill="both", expand=True, padx=10, pady=10)
            box.insert("1.0", item.text)
            def save():
                value = normalize_prompt(box.get("1.0", "end"))
                if value:
                    self.entries_b[index] = PromptEntry(item.number, value)
                    refresh()
                editor.destroy()
            ttk.Button(editor, text="保存修改", command=save).pack(pady=(0, 10))

        def remove():
            for index in sorted((int(x) for x in tree.selection()), reverse=True):
                self.entries_b.pop(index)
            refresh()

        tree.bind("<Double-1>", edit)
        bar = ttk.Frame(win, padding=(10, 0, 10, 10))
        bar.pack(fill="x")
        ttk.Button(bar, text="删除选中", command=remove).pack(side="left")
        ttk.Button(bar, text="关闭", command=win.destroy).pack(side="right")
        refresh()

    def open_extra_participants_editor(self):
        win = tk.Toplevel(self.root)
        win.title("多人扩展角色 C～F · 每人一份编号 MD")
        win.geometry("1120x560")
        container = ttk.Frame(win, padding=10)
        container.pack(fill="both", expand=True)
        rows: list[dict] = []

        def render():
            for child in container.winfo_children():
                child.destroy()
            headers = ("编号", "角色", "九宫格位置", "MD状态", "统一开头", "统一末尾", "操作")
            for col, label in enumerate(headers):
                ttk.Label(container, text=label, font=("Microsoft YaHei UI", 9, "bold")).grid(row=0, column=col, padx=4, pady=5, sticky="w")
            for index, row in enumerate(rows):
                letter = chr(ord("C") + index)
                ttk.Label(container, text=f"角色{letter}").grid(row=index + 1, column=0, padx=4, pady=6)
                ttk.Combobox(container, textvariable=row["role_var"], values=ROLE_ORDER[:-1], state="readonly", width=8).grid(row=index + 1, column=1, padx=4)
                ttk.Combobox(container, textvariable=row["position_var"], values=POSITION_ORDER, state="readonly", width=8).grid(row=index + 1, column=2, padx=4)
                ttk.Label(container, textvariable=row["status_var"], width=18).grid(row=index + 1, column=3, padx=4)
                ttk.Entry(container, textvariable=row["prefix_var"], width=24).grid(row=index + 1, column=4, padx=4, sticky="ew")
                ttk.Entry(container, textvariable=row["postfix_var"], width=24).grid(row=index + 1, column=5, padx=4, sticky="ew")
                actions = ttk.Frame(container)
                actions.grid(row=index + 1, column=6, padx=4)
                ttk.Button(actions, text="导入MD", command=lambda i=index: import_md(i)).pack(side="left")
                ttk.Button(actions, text="删除", command=lambda i=index: remove_row(i)).pack(side="left", padx=3)
            container.columnconfigure(4, weight=1)
            container.columnconfigure(5, weight=1)
            bottom = ttk.Frame(container)
            bottom.grid(row=len(rows) + 2, column=0, columnspan=7, sticky="ew", pady=(20, 0))
            ttk.Button(bottom, text="＋ 添加一名角色", command=add_row).pack(side="left")
            ttk.Label(bottom, text="最多扩展到角色F；A/B在主窗口配置。九宫格允许重叠，但保真度会下降。 ").pack(side="left", padx=10)
            ttk.Button(bottom, text="应用并关闭", command=apply).pack(side="right")

        def add_row(initial=None):
            if len(rows) >= 4:
                messagebox.showwarning("已到上限", "当前版本支持 A～F，最多六名角色。", parent=win)
                return
            defaults = ["正中", "左上", "右上", "中下"]
            initial = initial or {}
            entries = list(initial.get("entries") or [])
            rows.append({
                "role_var": tk.StringVar(value=initial.get("role", "小绿")),
                "position_var": tk.StringVar(value=initial.get("position", defaults[len(rows)])),
                "prefix_var": tk.StringVar(value=initial.get("prefix", "")),
                "postfix_var": tk.StringVar(value=initial.get("postfix", "")),
                "entries": entries,
                "status_var": tk.StringVar(value=f"已导入 {len(entries)} 条" if entries else "未导入"),
            })
            render()

        def remove_row(index):
            rows.pop(index)
            render()

        def import_md(index):
            path = filedialog.askopenfilename(
                title=f"导入角色{chr(ord('C') + index)}编号提示词",
                filetypes=[("Markdown / 文本", "*.md *.txt"), ("全部文件", "*.*")],
                parent=win,
            )
            if not path:
                return
            try:
                value = Path(path).read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                value = Path(path).read_text(encoding="gb18030")
            entries, mode = parse_prompt_document(value)
            if not entries:
                messagebox.showerror("没有识别到提示词", "请使用 `1. 提示词` 编号格式。", parent=win)
                return
            rows[index]["entries"] = entries
            rows[index]["status_var"].set(f"已导入 {len(entries)} 条")
            self.log(f"扩展角色{chr(ord('C') + index)}导入 {len(entries)} 条，模式：{mode}。")

        def apply():
            for index, row in enumerate(rows):
                if not row["entries"]:
                    messagebox.showerror("扩展角色缺少MD", f"角色{chr(ord('C') + index)}尚未导入提示词。", parent=win)
                    return
            self.extra_participants = [
                {
                    "role": row["role_var"].get(),
                    "position": row["position_var"].get(),
                    "prefix": row["prefix_var"].get().strip(),
                    "postfix": row["postfix_var"].get().strip(),
                    "entries": list(row["entries"]),
                }
                for row in rows
            ]
            self.extra_count_var.set(f"已扩展 {len(rows)} 人；总人数 {2 + len(rows)}") if rows else self.extra_count_var.set("无扩展角色")
            self.dual_mode_var.set(True)
            win.destroy()

        if self.extra_participants:
            for participant in self.extra_participants:
                add_row(participant)
        else:
            render()

    def on_dual_mode_changed(self):
        if not self.targets or not self.dual_mode_var.get():
            return
        labels = [x[0] for x in self.targets]
        target_a = next((x for x in labels if "角色A" in x), None)
        target_b = next((x for x in labels if "角色B" in x), None)
        if target_a:
            self.target_var.set(target_a)
        if target_b:
            self.target_b_var.set(target_b)
        self.save_config()

    def paste_and_parse(self):
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            messagebox.showwarning("剪贴板为空", "剪贴板中没有可读取的文本。")
            return
        self.load_entries(text, "剪贴板")

    def load_entries(self, text: str, source: str):
        entries, mode = parse_prompt_document(text)
        if not entries:
            messagebox.showerror("没有识别到提示词", "请使用 `1. 提示词`、`2. 提示词` 格式，或用空行分隔。")
            return
        numbers = consecutive_numbers(entries)
        if numbers and numbers[0] != 1:
            entries = renumber_entries(entries)
            self.log(f"角色A检测到连续编号 {numbers[0]}～{numbers[-1]}，已自动重排为1～{len(entries)}。")
        self.entries = entries
        self.refresh_table()
        self.status_var.set(f"已导入 {len(entries)} 条 · {mode}")
        self.log(f"从 {source} 识别 {len(entries)} 条提示词，模式：{mode}。")

    def renumber_a(self):
        if not self.entries:
            messagebox.showwarning("角色A为空", "请先导入角色A的 MD。")
            return
        self.entries = renumber_entries(self.entries)
        self.refresh_table()
        self.status_var.set(f"角色A已按当前顺序重排为1～{len(self.entries)}")
        self.log(f"角色A手动重新编号：1～{len(self.entries)}。")

    def renumber_b(self):
        if not self.entries_b:
            messagebox.showwarning("角色B为空", "请先导入角色B的 MD。")
            return
        self.entries_b = renumber_entries(self.entries_b)
        self.b_count_var.set(f"角色B：{len(self.entries_b)} 条（已重排1～{len(self.entries_b)}）")
        self.status_var.set(f"角色B已按当前顺序重排为1～{len(self.entries_b)}")
        self.log(f"角色B手动重新编号：1～{len(self.entries_b)}。")

    def smart_align_ab(self, show_if_no_match: bool = False):
        if not self.entries or not self.entries_b:
            if show_if_no_match:
                messagebox.showwarning("无法对齐", "请先导入角色A和角色B两份 MD。")
            return False
        left, right, message = smart_align_two_documents(self.entries, self.entries_b)
        if not message:
            if show_if_no_match:
                messagebox.showinfo("无需调整", "没有检测到可安全自动修复的连续编号偏移。\n如果只是想忽略原编号，可分别点击“从1重新编号”。")
            return False
        self.entries = left
        self.entries_b = right
        self.refresh_table()
        self.b_count_var.set(f"角色B：{len(right)} 条（已与A对齐）")
        self.status_var.set(f"智能编号修复完成 · A/B各{len(left)}条")
        self.log(message)
        return True

    def refresh_table(self):
        self.table.delete(*self.table.get_children())
        for i, item in enumerate(self.entries):
            preview = item.text if len(item.text) <= 180 else item.text[:177] + "…"
            self.table.insert("", "end", iid=str(i), values=(item.number, len(item.text), preview))

    def remove_selected(self):
        indexes = sorted((int(x) for x in self.table.selection()), reverse=True)
        for index in indexes:
            self.entries.pop(index)
        self.refresh_table()

    def clear_entries(self):
        self.entries.clear()
        self.refresh_table()
        self.status_var.set("已清空提示词")

    def _find_pattern(self):
        needle = self.find_var.get()
        if not needle:
            raise ValueError("请先填写要查找的文字。")
        flags = 0 if self.case_sensitive_var.get() else re.IGNORECASE
        return re.compile(re.escape(needle), flags)

    def find_all(self):
        try:
            pattern = self._find_pattern()
        except ValueError as exc:
            messagebox.showwarning("无法查找", str(exc))
            return
        matched = []
        occurrences = 0
        for index, item in enumerate(self.entries):
            count = len(pattern.findall(item.text))
            if count:
                matched.append(str(index))
                occurrences += count
        self.table.selection_set(matched)
        if matched:
            self.table.see(matched[0])
        self.status_var.set(f"命中 {len(matched)} 条，共 {occurrences} 处")
        self.log(f"批量查找：命中 {len(matched)} 条，共 {occurrences} 处。")

    def replace_all(self):
        try:
            pattern = self._find_pattern()
        except ValueError as exc:
            messagebox.showwarning("无法替换", str(exc))
            return
        replacement = self.replace_var.get()
        changed_entries = 0
        replacements = 0
        for item in self.entries:
            new_text, count = pattern.subn(lambda _m: replacement, item.text)
            if count:
                item.text = normalize_prompt(new_text)
                changed_entries += 1
                replacements += count
        self.refresh_table()
        self.status_var.set(f"已替换 {changed_entries} 条，共 {replacements} 处")
        self.log(f"全部替换完成：{changed_entries} 条，共 {replacements} 处。")

    def delete_matches(self):
        self.replace_var.set("")
        self.replace_all()

    def delete_matching_entries(self):
        try:
            pattern = self._find_pattern()
        except ValueError as exc:
            messagebox.showwarning("无法删除", str(exc))
            return
        indexes = [i for i, item in enumerate(self.entries) if pattern.search(item.text)]
        if not indexes:
            self.status_var.set("没有命中可删除的条目")
            return
        if not messagebox.askyesno("确认批量删除", f"将删除 {len(indexes)} 条完整提示词，是否继续？"):
            return
        for index in reversed(indexes):
            self.entries.pop(index)
        self.refresh_table()
        self.status_var.set(f"已删除 {len(indexes)} 条命中提示词")
        self.log(f"批量删除完整条目：{len(indexes)} 条。")

    def edit_selected(self, _event=None):
        selection = self.table.selection()
        if not selection:
            return
        index = int(selection[0])
        item = self.entries[index]
        win = tk.Toplevel(self.root)
        win.title(f"编辑第 {item.number} 条")
        win.geometry("850x430")
        text = tk.Text(win, wrap="word", undo=True)
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", item.text)
        def save():
            value = normalize_prompt(text.get("1.0", "end"))
            if value:
                self.entries[index] = PromptEntry(item.number, value)
                self.refresh_table()
            win.destroy()
        ttk.Button(win, text="保存修改", command=save).pack(pady=(0, 10))

    def selected_target(self):
        label = self.target_var.get()
        for target in self.targets:
            if target[0] == label:
                return target
        raise ValueError("请先检查工作流并选择正面提示词栏。")

    def selected_target_b(self):
        label = self.target_b_var.get()
        for target in self.targets:
            if target[0] == label:
                return target
        raise ValueError("双人模式需要先选择角色B提示词栏。")

    def preview(self):
        if not self.entries:
            messagebox.showwarning("没有提示词", "请先导入 Markdown。")
            return
        prefix = self.prefix_text.get("1.0", "end").strip()
        postfix = self.postfix_text.get("1.0", "end").strip()
        win = tk.Toplevel(self.root)
        win.title("前 5 条拼接预览")
        win.geometry("980x650")
        text = tk.Text(win, wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        if self.dual_mode_var.get():
            participants = [
                {"role": self.role_var.get(), "position": self.position_a_var.get(), "prefix": prefix, "postfix": postfix, "entries": self.entries},
                {"role": self.role_b_var.get(), "position": self.position_b_var.get(), "prefix": self.prefix_b_var.get(), "postfix": self.postfix_b_var.get(), "entries": self.entries_b},
            ] + list(self.extra_participants)
            aligned = align_prompt_documents([p["entries"] for p in participants])
            for items in aligned[:5]:
                text.insert("end", f"===== 图片 {items[0].number} =====\n")
                for index, (participant, entry) in enumerate(zip(participants, items)):
                    letter = chr(ord("A") + index)
                    body = combine_prompt_parts(participant.get("prefix", ""), entry.text, participant.get("postfix", ""))
                    text.insert("end", f"【角色{letter} · {participant['role']} · {participant['position']}】{body}\n")
                text.insert("end", "\n")
        else:
            for item in self.entries[:5]:
                text.insert("end", f"===== 图片 {item.number} =====\n{combine_prompt_parts(prefix, item.text, postfix)}\n\n")
        text.configure(state="disabled")

    def prepare_jobs(self):
        path = Path(self.workflow_var.get().strip())
        if not path.exists():
            raise FileNotFoundError("工作流文件不存在。")
        template = load_api_workflow(path)
        if not self.targets:
            self.targets = find_prompt_targets(template)
        if not self.entries:
            raise ValueError("还没有导入任何提示词。")
        prefix = self.prefix_text.get("1.0", "end").strip()
        postfix = self.postfix_text.get("1.0", "end").strip()
        repeat = max(1, min(20, int(self.repeat_var.get())))
        seed_start = int(self.seed_var.get().strip() or "0")
        output_root = self.output_var.get().strip().strip("/\\") or "DragonMaid/MD_Batch"
        stamp = time.strftime("%Y%m%d_%H%M%S")
        jobs = []
        serial = 0
        dual_mode = bool(self.dual_mode_var.get())
        if dual_mode:
            if not self.entries_b:
                raise ValueError("多人模式尚未导入角色B的 Markdown。")
            participants = [
                {"role": self.role_var.get(), "position": self.position_a_var.get(), "prefix": prefix, "postfix": postfix, "entries": self.entries},
                {"role": self.role_b_var.get(), "position": self.position_b_var.get(), "prefix": self.prefix_b_var.get(), "postfix": self.postfix_b_var.get(), "entries": self.entries_b},
            ] + list(self.extra_participants)
            if any(item["role"] == "通用" for item in participants):
                raise ValueError("多人区域 LoRA 模式需要为每一名角色选择具体角色，不能使用“通用”。")
            template, dynamic_prompt_ids = build_dynamic_region_workflow(template, participants)
            source_rows = align_prompt_documents([item["entries"] for item in participants])
            node_id = input_name = None
        else:
            _, node_id, input_name = self.selected_target()
            participants = []
            dynamic_prompt_ids = []
            source_rows = [[item] for item in self.entries]
        samplers, latents, saves = find_runtime_nodes(template)
        for aligned_items in source_rows:
            item = aligned_items[0]
            for copy_index in range(1, repeat + 1):
                serial += 1
                workflow = copy.deepcopy(template)
                if not dual_mode and not self.keep_var.get() and workflow[node_id]["class_type"] == "DragonMaidPromptPanel":
                    for field in PANEL_FIELDS:
                        workflow[node_id]["inputs"][field] = ""
                full = combine_prompt_parts(prefix, item.text, postfix)
                participant_prompts = []
                if dual_mode:
                    for participant, prompt_id, entry in zip(participants, dynamic_prompt_ids, aligned_items):
                        body = combine_prompt_parts(participant.get("prefix", ""), entry.text, participant.get("postfix", ""))
                        final_prompt = combine_prompt(ROLE_IDENTITY_PROMPTS[participant["role"]], body)
                        workflow[prompt_id]["inputs"]["text"] = final_prompt
                        participant_prompts.append(final_prompt)
                    full_b = participant_prompts[1]
                else:
                    workflow[node_id]["inputs"][input_name] = full
                    participant_prompts = [full]
                    full_b = ""
                seed = random.SystemRandom().randrange(0, 2**63 - 1) if self.seed_mode_var.get() == "随机" else seed_start + serial - 1
                for sampler_id in samplers:
                    key = "noise_seed" if "noise_seed" in workflow[sampler_id]["inputs"] else "seed"
                    workflow[sampler_id]["inputs"][key] = seed
                for latent_id in latents:
                    workflow[latent_id]["inputs"]["batch_size"] = 1
                safe_number = re.sub(r"[^0-9A-Za-z_-]+", "_", item.number)
                filename_prefix = f"{output_root}/{stamp}/{safe_number}_{copy_index:02d}"
                for save_id in saves:
                    workflow[save_id]["inputs"]["filename_prefix"] = filename_prefix
                jobs.append(
                    {
                        "serial": serial,
                        "source_number": item.number,
                        "copy": copy_index,
                        "prompt": full,
                        "prompt_b": full_b,
                        "participant_prompts": participant_prompts,
                        "participants": [
                            {"role": p["role"], "position": p["position"]}
                            for p in participants
                        ] if dual_mode else [],
                        "seed": seed,
                        "filename_prefix": filename_prefix,
                        "workflow": workflow,
                    }
                )
        return path, jobs

    def export_jobs(self):
        try:
            path, jobs = self.prepare_jobs()
            destination = filedialog.askdirectory(title="选择任务包导出目录")
            if not destination:
                return
            out = Path(destination) / f"MD批量任务_{time.strftime('%Y%m%d_%H%M%S')}"
            out.mkdir(parents=True, exist_ok=True)
            manifest_jobs = []
            for job in jobs:
                write_json(out / f"job_{job['serial']:04d}.json", {"prompt": job["workflow"]})
                manifest_jobs.append({k: v for k, v in job.items() if k != "workflow"})
            write_json(out / "manifest.json", {"workflow_source": str(path), "jobs": manifest_jobs})
            self.log(f"已导出 {len(jobs)} 个 API 任务：{out}")
            messagebox.showinfo("导出完成", f"已导出 {len(jobs)} 个任务\n{out}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def test_connection(self):
        try:
            stats = api_get(self.server_var.get().strip().rstrip("/") + "/system_stats")
            device = (stats.get("devices") or [{}])[0].get("name", "未知设备")
            self.status_var.set(f"ComfyUI 已连接 · {device}")
            self.log(f"ComfyUI 已连接：{device}")
        except Exception as exc:
            messagebox.showerror("连接失败", f"无法连接 ComfyUI：{exc}")

    def start_queue(self):
        try:
            self.inspect_workflow()
            path, jobs = self.prepare_jobs()
        except Exception as exc:
            messagebox.showerror("无法开始", str(exc))
            return
        protected_prompts = []
        if self.dual_mode_var.get():
            for job in jobs:
                for participant, prompt in zip(job.get("participants", []), job.get("participant_prompts", [])):
                    if participant.get("role") == "小蓝":
                        protected_prompts.append(prompt)
        elif self.role_var.get() == "小蓝":
            protected_prompts.extend(job["prompt"] for job in jobs)
        if protected_prompts:
            joined = " ".join(protected_prompts)
            if re.search(r"\b(nsfw|nude|naked|sex|explicit)\b", joined, re.I):
                messagebox.showerror("小蓝仅限 SFW", "检测到成人提示词，本批任务没有提交。")
                return
        self.save_config()
        self.stop_event.clear()
        self.progress.configure(maximum=len(jobs), value=0)
        threading.Thread(target=self.queue_worker, args=(path, jobs), daemon=True).start()

    def queue_worker(self, path: Path, jobs: list[dict]):
        server = self.server_var.get().strip().rstrip("/")
        client_id = str(uuid.uuid4())
        run_dir = RUNS_DIR / time.strftime("%Y%m%d_%H%M%S")
        run_dir.mkdir(parents=True, exist_ok=True)
        records = []
        try:
            api_get(server + "/system_stats")
            for submitted, job in enumerate(jobs, 1):
                if self.stop_event.is_set():
                    break
                result = api_post(server + "/prompt", {"prompt": job["workflow"], "client_id": client_id})
                record = {k: v for k, v in job.items() if k != "workflow"}
                record["prompt_id"] = result.get("prompt_id")
                record["node_errors"] = result.get("node_errors")
                records.append(record)
                self.root.after(0, lambda value=submitted: self.progress.configure(value=value))
                self.log(f"[{submitted}/{len(jobs)}] 图片编号 {job['source_number']} 已写入 ComfyUI：{record['prompt_id']}")
                if record["node_errors"]:
                    self.log("节点错误：" + json.dumps(record["node_errors"], ensure_ascii=False))
            write_json(
                run_dir / "run_manifest.json",
                {
                    "workflow_source": str(path),
                    "server": server,
                    "submitted": len(records),
                    "total": len(jobs),
                    "jobs": records,
                },
            )
            if self.stop_event.is_set():
                message = f"已停止 · 已提交 {len(records)}/{len(jobs)} 个任务"
            else:
                message = f"提交完成 · {len(records)}/{len(jobs)} 个任务（不等待生成）"
            self.root.after(0, lambda value=message: self.status_var.set(value))
            self.log(f"{message}；记录已保存：{run_dir}")
        except urllib.error.URLError as exc:
            self.log(f"ComfyUI 连接失败：{exc}")
            self.root.after(0, lambda: messagebox.showerror("连接失败", "ComfyUI 未运行或 8188 不可访问。"))
        except Exception as exc:
            self.log(f"批量入队失败：{exc}")
            self.root.after(0, lambda: messagebox.showerror("批量入队失败", str(exc)))

    def stop_queue(self):
        self.stop_event.set()
        self.log("已停止当前提交；已进入 ComfyUI 队列的任务不会被删除。")

    def on_close(self):
        self.save_config()
        self.root.destroy()


def main():
    root = tk.Tk()
    BatchPromptAppV2(root)
    root.mainloop()


if __name__ == "__main__":
    main()
