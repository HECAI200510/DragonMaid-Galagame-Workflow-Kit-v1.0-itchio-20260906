from __future__ import annotations

import re
from dataclasses import dataclass


MAX_SEED = 0xFFFFFFFFFFFFFFFF
NUMBERED_LINE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?P<number>\d{1,5})\s*(?:[.)、．。:]|-\s+)\s*(?P<body>.*)$"
)
INLINE_NUMBER = re.compile(
    r"(?:^|[\s,，;；])(?P<number>\d{1,5})\s*[.)、．。]\s*"
)


@dataclass(frozen=True)
class PromptEntry:
    number: str
    text: str


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


def parse_numbered_markdown(text: str) -> list[PromptEntry]:
    entries: list[PromptEntry] = []
    current_number: str | None = None
    current_lines: list[str] = []

    def flush() -> None:
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

    matches = list(INLINE_NUMBER.finditer(text))
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
    blocks = [normalize_prompt(part) for part in re.split(r"\n\s*\n+|^\s*---+\s*$", text, flags=re.M)]
    blocks = [part for part in blocks if part]
    return [PromptEntry(str(index), value) for index, value in enumerate(blocks, 1)], "空行/分隔线"


def combine_prompt(prefix: str, body: str, postfix: str) -> str:
    parts = [str(value).strip(" ,\t\r\n") for value in (prefix, body, postfix)]
    return ", ".join(value for value in parts if value)


def consecutive_numbers(entries: list[PromptEntry]) -> list[int] | None:
    if not entries:
        return None
    try:
        numbers = [int(item.number.strip()) for item in entries]
    except ValueError:
        return None
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    return numbers if numbers == expected else None


def renumber_entries(entries: list[PromptEntry], start: int = 1) -> list[PromptEntry]:
    return [PromptEntry(str(start + index), item.text) for index, item in enumerate(entries)]


def smart_align_two_documents(
    left: list[PromptEntry], right: list[PromptEntry]
) -> tuple[list[PromptEntry], list[PromptEntry], str | None]:
    left_numbers = consecutive_numbers(left)
    right_numbers = consecutive_numbers(right)
    if left_numbers is None or right_numbers is None:
        return left, right, None

    if len(left) > len(right) and left_numbers[-len(right):] == right_numbers:
        prefix = left[:-len(right)]
        if len(prefix) == len(right) and consecutive_numbers(prefix) is not None:
            return (
                renumber_entries(prefix),
                renumber_entries(right),
                f"角色A包含前后两组：采用前 {len(prefix)} 条；角色B的 {right_numbers[0]}～{right_numbers[-1]} 已重排为 1～{len(right)}。",
            )
    if len(right) > len(left) and right_numbers[-len(left):] == left_numbers:
        prefix = right[:-len(left)]
        if len(prefix) == len(left) and consecutive_numbers(prefix) is not None:
            return (
                renumber_entries(left),
                renumber_entries(prefix),
                f"角色B包含前后两组：采用前 {len(prefix)} 条；两边已重排为 1～{len(left)}。",
            )

    if len(left) == len(right):
        left_start, right_start = left_numbers[0], right_numbers[0]
        normalized_left = renumber_entries(left)
        normalized_right = renumber_entries(right)
        if left_start != 1 or right_start != 1:
            return (
                normalized_left,
                normalized_right,
                f"检测到两份连续序列从 {left_start} 和 {right_start} 开始；已按各自顺序统一重排为 1～{len(left)}。",
            )
        return normalized_left, normalized_right, None
    return left, right, None


def pair_entries_by_number(
    left: list[PromptEntry], right: list[PromptEntry], right_label: str
) -> list[tuple[PromptEntry, PromptEntry]]:
    def build_index(items: list[PromptEntry], label: str) -> dict[str, PromptEntry]:
        result: dict[str, PromptEntry] = {}
        duplicates = []
        for item in items:
            key = item.number.strip()
            if key in result:
                duplicates.append(key)
            result[key] = item
        if duplicates:
            repeated = ", ".join(sorted(set(duplicates)))
            raise ValueError(f"{label}存在重复编号：{repeated}")
        return result

    left_index = build_index(left, "角色A文档")
    right_index = build_index(right, f"角色{right_label}文档")
    missing_right = [key for key in left_index if key not in right_index]
    missing_left = [key for key in right_index if key not in left_index]
    if missing_right or missing_left:
        parts = []
        if missing_right:
            parts.append(f"角色{right_label}缺少：" + ", ".join(missing_right[:20]))
        if missing_left:
            parts.append("角色A缺少：" + ", ".join(missing_left[:20]))
        raise ValueError("两份 MD 编号无法配对：" + "；".join(parts))
    return [(item, right_index[item.number.strip()]) for item in left]


def align_prompt_documents(
    documents: list[list[PromptEntry]], labels: list[str]
) -> tuple[list[list[PromptEntry]], str]:
    notes = []
    if len(documents) == 2:
        left, right, note = smart_align_two_documents(documents[0], documents[1])
        documents = [left, right]
        if note:
            notes.append(note)
    elif len({len(items) for items in documents}) == 1:
        numeric = [consecutive_numbers(items) for items in documents]
        if all(numbers is not None for numbers in numeric):
            starts = [numbers[0] for numbers in numeric]
            documents = [renumber_entries(items) for items in documents]
            if len(set(starts)) > 1 or starts[0] != 1:
                notes.append(
                    "连续编号起点为 " + "、".join(str(value) for value in starts) + f"；已按顺序统一重排为 1～{len(documents[0])}。"
                )

    aligned = [[item] for item in documents[0]]
    for other, label in zip(documents[1:], labels[1:]):
        pairs = pair_entries_by_number(documents[0], other, label)
        for index, (_, matched) in enumerate(pairs):
            aligned[index].append(matched)
    return aligned, " ".join(notes) if notes else "编号已严格配对。"


def select_rows(rows: list, start_item: int, max_items: int) -> list:
    start = max(0, int(start_item) - 1)
    selected = rows[start:]
    if int(max_items) > 0:
        selected = selected[: int(max_items)]
    if not selected:
        raise ValueError("当前起始条目和读取条数组合没有选中任何提示词。")
    return selected


def expand_jobs(
    rows: list[list[PromptEntry]], prefix: str, postfix: str, repeat: int, seed_start: int
) -> tuple[list[list[str]], list[str], list[int]]:
    participant_count = len(rows[0])
    prompts = [[] for _ in range(participant_count)]
    job_ids: list[str] = []
    seeds: list[int] = []
    serial = 0
    for row in rows:
        for copy_index in range(1, int(repeat) + 1):
            serial += 1
            for index, entry in enumerate(row):
                prompts[index].append(combine_prompt(prefix, entry.text, postfix))
            job_ids.append(f"{row[0].number}_{copy_index:02d}")
            seeds.append((int(seed_start) + serial - 1) & MAX_SEED)
    return prompts, job_ids, seeds


def format_preview(job_ids: list[str], seeds: list[int], prompt_columns: list[list[str]], limit: int = 5) -> str:
    lines = []
    for index in range(min(limit, len(job_ids))):
        parts = [f"{chr(ord('A') + column)}={values[index]}" for column, values in enumerate(prompt_columns)]
        lines.append(f"{job_ids[index]} | seed={seeds[index]} | " + " | ".join(parts))
    if len(job_ids) > limit:
        lines.append(f"……另有 {len(job_ids) - limit} 个任务")
    return "\n".join(lines)


def parse_required_document(text: str, label: str) -> tuple[list[PromptEntry], str]:
    entries, mode = parse_prompt_document(text)
    if not entries:
        raise ValueError(f"角色{label}没有识别到提示词。请粘贴 `1. 提示词`、`2. 提示词` 格式的内容。")
    return entries, mode


class DragonMaidBatchPromptList:
    @classmethod
    def INPUT_TYPES(cls):
        text = {"multiline": True, "dynamicPrompts": False, "default": ""}
        return {
            "required": {
                "编号提示词_MD": ("STRING", {**text, "tooltip": "粘贴编号 Markdown；也支持用空行或 --- 分隔。"}),
                "统一开头": ("STRING", {**text, "tooltip": "自动加到每条提示词最前面。"}),
                "统一末尾": ("STRING", {**text, "tooltip": "自动加到每条提示词最后面。"}),
                "起始条目": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "读取条数_0为全部": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "每条重复次数": ("INT", {"default": 1, "min": 1, "max": 20, "step": 1}),
                "起始种子": ("INT", {"default": 202609020001, "min": 0, "max": MAX_SEED, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("提示词列表", "任务编号列表", "种子列表", "任务总数", "前5条预览")
    OUTPUT_IS_LIST = (True, True, True, False, False)
    FUNCTION = "build"
    CATEGORY = "DragonMaid/批量提示词"
    DESCRIPTION = "把编号 Markdown 解析为 ComfyUI 列表；下游节点会对列表中的每条提示词依次执行。"

    def build(
        self,
        编号提示词_MD,
        统一开头,
        统一末尾,
        起始条目,
        读取条数_0为全部,
        每条重复次数,
        起始种子,
    ):
        entries, _ = parse_required_document(str(编号提示词_MD), "A")
        rows = select_rows([[entry] for entry in entries], 起始条目, 读取条数_0为全部)
        prompts, job_ids, seeds = expand_jobs(rows, 统一开头, 统一末尾, 每条重复次数, 起始种子)
        preview = format_preview(job_ids, seeds, prompts)
        return prompts[0], job_ids, seeds, len(job_ids), preview


class DragonMaidBatchPromptMultiList:
    @classmethod
    def INPUT_TYPES(cls):
        text = {"multiline": True, "dynamicPrompts": False, "default": ""}
        return {
            "required": {
                "角色数量": ("INT", {"default": 2, "min": 2, "max": 6, "step": 1}),
                "角色A_MD": ("STRING", {**text, "tooltip": "基准编号文档。"}),
                "角色B_MD": ("STRING", {**text, "tooltip": "按编号与角色A对齐。"}),
                "角色C_MD": ("STRING", {**text, "tooltip": "角色数量不足3时留空。"}),
                "角色D_MD": ("STRING", {**text, "tooltip": "角色数量不足4时留空。"}),
                "角色E_MD": ("STRING", {**text, "tooltip": "角色数量不足5时留空。"}),
                "角色F_MD": ("STRING", {**text, "tooltip": "角色数量不足6时留空。"}),
                "每人统一开头": ("STRING", {**text, "tooltip": "自动加到每名角色的每条提示词最前面。"}),
                "每人统一末尾": ("STRING", {**text, "tooltip": "自动加到每名角色的每条提示词最后面。"}),
                "起始条目": ("INT", {"default": 1, "min": 1, "max": 100000, "step": 1}),
                "读取条数_0为全部": ("INT", {"default": 0, "min": 0, "max": 100000, "step": 1}),
                "每条重复次数": ("INT", {"default": 1, "min": 1, "max": 20, "step": 1}),
                "起始种子": ("INT", {"default": 202609020001, "min": 0, "max": MAX_SEED, "step": 1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "INT", "INT", "STRING", "STRING")
    RETURN_NAMES = (
        "角色A提示词", "角色B提示词", "角色C提示词", "角色D提示词", "角色E提示词", "角色F提示词",
        "任务编号列表", "种子列表", "任务总数", "前5条预览", "编号对齐说明",
    )
    OUTPUT_IS_LIST = (True, True, True, True, True, True, True, True, False, False, False)
    FUNCTION = "build"
    CATEGORY = "DragonMaid/批量提示词"
    DESCRIPTION = "把2～6份编号 Markdown 严格对齐，并分别输出可连接到区域提示词编码器的列表。"

    def build(
        self,
        角色数量,
        角色A_MD,
        角色B_MD,
        角色C_MD,
        角色D_MD,
        角色E_MD,
        角色F_MD,
        每人统一开头,
        每人统一末尾,
        起始条目,
        读取条数_0为全部,
        每条重复次数,
        起始种子,
    ):
        count = int(角色数量)
        labels = list("ABCDEF")[:count]
        sources = [角色A_MD, 角色B_MD, 角色C_MD, 角色D_MD, 角色E_MD, 角色F_MD][:count]
        documents = [parse_required_document(str(source), label)[0] for label, source in zip(labels, sources)]
        rows, note = align_prompt_documents(documents, labels)
        rows = select_rows(rows, 起始条目, 读取条数_0为全部)
        prompts, job_ids, seeds = expand_jobs(rows, 每人统一开头, 每人统一末尾, 每条重复次数, 起始种子)
        padded = prompts + [[""] * len(job_ids) for _ in range(6 - len(prompts))]
        preview = format_preview(job_ids, seeds, prompts)
        return (*padded, job_ids, seeds, len(job_ids), preview, note)


class DragonMaidBatchPromptPreview:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"提示词列表": ("STRING", {"forceInput": True})}}

    INPUT_IS_LIST = True
    RETURN_TYPES = ()
    FUNCTION = "show"
    OUTPUT_NODE = True
    CATEGORY = "DragonMaid/批量提示词"
    DESCRIPTION = "在执行历史和节点界面中显示批量提示词，适合先检查再连接采样器。"

    def show(self, 提示词列表):
        return {"ui": {"text": [str(value) for value in 提示词列表]}}
