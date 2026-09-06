from __future__ import annotations

import csv
import json
import os
import posixpath
import queue
import subprocess
import sys
import threading
import traceback
import winsound
import zipfile
from pathlib import Path
from tkinter import END, BOTH, LEFT, RIGHT, TOP, X, Y, BooleanVar, DoubleVar, IntVar, StringVar, Tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from xml.etree import ElementTree


SCRIPT_ROOT = Path(__file__).resolve().parent
NODE_PARENT_CANDIDATES = [SCRIPT_ROOT]
if os.environ.get("COMFYUI_CUSTOM_NODES"):
    NODE_PARENT_CANDIDATES.append(Path(os.environ["COMFYUI_CUSTOM_NODES"]).expanduser())
for candidate in NODE_PARENT_CANDIDATES:
    if (candidate / "dragonmaid_voice_nodes").is_dir():
        sys.path.insert(0, str(candidate))
        break

from dragonmaid_voice_nodes.voice_core import (  # noqa: E402
    DEFAULT_OUTPUT_ROOT,
    EMOTIONS,
    LANGUAGES,
    ROLE_PRESETS,
    normalize_emotion,
    normalize_language,
    normalize_role,
    synthesize_role,
)


COLUMNS = ("id", "角色", "语言", "情绪", "语速", "台词", "状态", "输出")
FIELD_ALIASES = {
    "id": ("id", "编号", "序号", "voice_id"),
    "角色": ("角色", "角色显示名", "character", "role"),
    "语言": ("语言", "language", "lang"),
    "情绪": ("情绪", "情绪类别", "emotion", "mood"),
    "语速": ("语速", "speed", "rate"),
    "台词": ("台词", "文本", "text", "line", "dialogue"),
    "情绪强度": ("情绪强度", "强度", "emotion_strength", "intensity"),
    "目标文件名": ("目标文件名", "文件名", "filename", "output_filename"),
    "时长范围": ("时长范围", "建议时长", "duration", "duration_range"),
    "种子": ("种子", "seed"),
    "使用RVC": ("使用rvc", "rvc", "use_rvc"),
}

LANGUAGE_TEXT_ALIASES = {
    "中文": ("中文文案", "中文台词", "中文", "zh_text", "text_zh"),
    "日语": ("日语文案", "日语台词", "日文", "日语", "ja_text", "text_ja"),
    "英语": ("英语文案", "英文文案", "英语台词", "英文台词", "英文", "英语", "en_text", "text_en"),
}

SHORT_INTERJECTION_TRANSLATIONS = {
    "嗯嗯～": ("うんうん～", "Mm-hmm~"),
    "嗯啊……": ("んあっ。", "Mmh."),
    "嗯。": ("うん。", "Mm."),
    "嗯……": ("んっ。", "Mm."),
    "唔……": ("うっ。", "Mmm."),
    "啊哈……": ("あっ、はぁ。", "Ah."),
    "嗯嗯。": ("うんうん。", "Mm-hmm."),
    "呜……": ("うぅっ。", "Nnh."),
    "哈啊……": ("はぁっ。", "Hah."),
    "呼……": ("ふぅ。", "Phew."),
    "诶？！": ("えっ？！", "Huh?!"),
    "唔嗯……": ("んぅっ。", "Mmmh."),
    "哼哼～": ("ふふん～", "Hehe~"),
    "啊……": ("あっ。", "Ah."),
    "啊？！": ("あっ？！", "Ah?!"),
    "哦齁齁齁～": ("おほほほ～", "Ohohoho~"),
    "唔。": ("ん。", "Mm."),
}


def _pick(mapping: dict, canonical: str, default=""):
    lower = {str(key).strip().lower(): value for key, value in mapping.items()}
    for alias in FIELD_ALIASES[canonical]:
        if alias.lower() in lower:
            return lower[alias.lower()]
    return default


def _pick_aliases(mapping: dict, aliases: tuple[str, ...], default=""):
    lower = {str(key).strip().lower(): value for key, value in mapping.items()}
    for alias in aliases:
        if alias.lower() in lower:
            return lower[alias.lower()]
    return default


def normalize_row(row: dict, number: int, defaults: dict | None = None) -> dict:
    defaults = defaults or {}
    role = normalize_role(_pick(row, "角色", defaults.get("角色", "管家")))
    language_code = normalize_language(_pick(row, "语言", defaults.get("语言", "中文")))
    language = {"zh": "中文", "ja": "日语", "en": "英语"}[language_code]
    emotion = normalize_emotion(_pick(row, "情绪", defaults.get("情绪", "平静")))
    text = str(_pick(row, "台词", defaults.get("台词", ""))).strip()
    if not text:
        raise ValueError(f"第 {number} 行缺少台词。")
    speed_raw = _pick(row, "语速", defaults.get("语速", ROLE_PRESETS[role]["speed"]))
    seed_raw = _pick(row, "种子", defaults.get("种子", 20260824 + number))
    strength_raw = _pick(row, "情绪强度", defaults.get("情绪强度", 1.0))
    target_filename = str(_pick(row, "目标文件名", defaults.get("目标文件名", ""))).strip()
    duration_range = str(_pick(row, "时长范围", defaults.get("时长范围", ""))).strip()
    rvc_raw = str(_pick(row, "使用RVC", defaults.get("使用RVC", False))).strip().lower()
    return {
        "id": str(_pick(row, "id", number)).strip() or str(number),
        "角色": role,
        "语言": language,
        "情绪": emotion,
        "语速": max(0.75, min(1.35, float(speed_raw))),
        "台词": text,
        "情绪强度": max(0.25, min(1.75, float(strength_raw))),
        "目标文件名": target_filename,
        "时长范围": duration_range,
        "种子": int(float(seed_raw)),
        "使用RVC": rvc_raw in {"1", "true", "yes", "y", "是", "开", "开启"},
        "状态": "待生成",
        "输出": "",
    }


def _column_index(cell_reference: str) -> int:
    letters = "".join(ch for ch in cell_reference if ch.isalpha()).upper()
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - 64
    return value - 1


def _read_xlsx_rows(path: Path) -> list[dict]:
    ns_main = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    ns_rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    ns_pkg = "{http://schemas.openxmlformats.org/package/2006/relationships}"
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall(f"{ns_main}si"):
                shared.append("".join(node.text or "" for node in item.iter(f"{ns_main}t")))

        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rels_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rels = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels_root.findall(f"{ns_pkg}Relationship")
        }
        sheets = []
        for sheet in workbook.find(f"{ns_main}sheets") or []:
            sheets.append((sheet.attrib["name"], rels[sheet.attrib[f"{ns_rel}id"]]))
        preferred = next((item for item in sheets if item[0] == "三语生成表"), None)
        preferred = preferred or next((item for item in sheets if item[0] == "短语气配音表"), None)
        if preferred is None:
            preferred = sheets[0]
        target = preferred[1].lstrip("/")
        sheet_path = posixpath.normpath(target if target.startswith("xl/") else posixpath.join("xl", target))
        root = ElementTree.fromstring(archive.read(sheet_path))

        matrix: list[list[object]] = []
        sheet_data = root.find(f"{ns_main}sheetData")
        for row_node in sheet_data or []:
            row_values: list[object] = []
            for cell in row_node.findall(f"{ns_main}c"):
                index = _column_index(cell.attrib.get("r", "A1"))
                while len(row_values) <= index:
                    row_values.append("")
                cell_type = cell.attrib.get("t", "")
                value_node = cell.find(f"{ns_main}v")
                if cell_type == "inlineStr":
                    inline = cell.find(f"{ns_main}is")
                    value: object = "" if inline is None else "".join(
                        node.text or "" for node in inline.iter(f"{ns_main}t")
                    )
                elif value_node is None:
                    value = ""
                elif cell_type == "s":
                    value = shared[int(value_node.text or 0)]
                elif cell_type == "b":
                    value = value_node.text == "1"
                else:
                    raw = value_node.text or ""
                    try:
                        numeric = float(raw)
                        value = int(numeric) if numeric.is_integer() else numeric
                    except ValueError:
                        value = raw
                row_values[index] = value
            matrix.append(row_values)
    if not matrix:
        return []
    headers = [str(value).strip() for value in matrix[0]]
    return [
        {headers[index]: value for index, value in enumerate(row) if index < len(headers) and headers[index]}
        for row in matrix[1:]
        if any(str(value).strip() for value in row)
    ]


def expand_multilingual_row(row: dict, number: int, defaults: dict | None = None) -> list[dict]:
    defaults = defaults or {}
    texts = {
        language: str(_pick_aliases(row, aliases, "")).strip()
        for language, aliases in LANGUAGE_TEXT_ALIASES.items()
    }
    source_phrase = str(row.get("推荐纯语气词", "")).strip()
    if source_phrase and not any(texts.values()):
        japanese, english = SHORT_INTERJECTION_TRANSLATIONS.get(
            source_phrase,
            (source_phrase, source_phrase),
        )
        texts = {"中文": source_phrase, "日语": japanese, "英语": english}
    if not any(texts.values()):
        return [normalize_row(row, number, defaults)]

    base_id = str(_pick(row, "id", number)).strip() or str(number)
    filename = str(_pick(row, "目标文件名", "")).strip()
    if "情绪强度" not in row and str(row.get("强度", "")).strip():
        level = int(float(row["强度"]))
        row = dict(row)
        row["情绪强度"] = {1: 0.80, 2: 1.15, 3: 1.50}.get(level, 1.0)
    language_codes = {"中文": "zh", "日语": "ja", "英语": "en"}
    expanded = []
    for offset, language in enumerate(("中文", "日语", "英语")):
        if not texts[language]:
            continue
        item = dict(row)
        item.update({
            "id": f"{base_id}_{language_codes[language]}",
            "语言": language,
            "台词": texts[language],
            "目标文件名": str(row.get(f"{language}文件名", "")).strip() or filename,
            "种子": int(float(_pick(row, "种子", 20260824 + number))) + offset * 100000,
        })
        expanded.append(normalize_row(item, number * 10 + offset, defaults))
    return expanded


def parse_batch_file(path: str | Path, defaults: dict | None = None) -> list[dict]:
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".txt":
        raw_rows = [{"台词": line.strip()} for line in source.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    elif suffix == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            raw_rows = list(csv.DictReader(handle))
    elif suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8-sig"))
        raw_rows = payload.get("lines", []) if isinstance(payload, dict) else payload
        if not isinstance(raw_rows, list):
            raise ValueError("JSON 顶层必须是数组，或包含 lines 数组。")
    elif suffix == ".xlsx":
        raw_rows = _read_xlsx_rows(source)
    else:
        raise ValueError("仅支持 TXT、CSV、JSON、XLSX。")
    result = []
    for index, row in enumerate(raw_rows, 1):
        result.extend(expand_multilingual_row(dict(row), index, defaults))
    return result


class VoiceBatchApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title("龙女仆七角色配音工作台")
        self.root.geometry("1380x840")
        self.root.minsize(1120, 700)
        self.rows: dict[str, dict] = {}
        self.events: queue.Queue = queue.Queue()
        self.worker: threading.Thread | None = None

        self.role = StringVar(value="管家")
        self.language = StringVar(value="中文")
        self.emotion = StringVar(value="平静")
        self.speed = DoubleVar(value=ROLE_PRESETS["管家"]["speed"])
        self.emotion_strength = DoubleVar(value=1.0)
        self.target_lufs = DoubleVar(value=-16.0)
        self.seed = IntVar(value=20260824)
        self.use_rvc = BooleanVar(value=False)
        self.output_root = StringVar(value=str(DEFAULT_OUTPUT_ROOT))
        self.status = StringVar(value="就绪：可直接输入，或导入 TXT / CSV / JSON。")
        self.progress_value = DoubleVar(value=0.0)

        self._build_ui()
        self.role.trace_add("write", self._role_changed)
        self.root.after(100, self._poll_events)

    def _build_ui(self):
        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        header = ttk.Frame(self.root, padding=(14, 12))
        header.pack(side=TOP, fill=X)
        ttk.Label(header, text="龙女仆七角色配音工作台", font=("Microsoft YaHei UI", 18, "bold")).pack(side=LEFT)
        ttk.Label(header, text="Qwen3-TTS 原声优先｜可选 RVC｜三语｜批量导入", foreground="#555").pack(side=LEFT, padx=18)

        editor = ttk.LabelFrame(self.root, text="单条编辑 / 批次默认值", padding=10)
        editor.pack(fill=X, padx=14, pady=(0, 8))
        controls = ttk.Frame(editor)
        controls.pack(fill=X)
        self._combo(controls, "角色", self.role, list(ROLE_PRESETS), 10)
        self._combo(controls, "语言", self.language, list(LANGUAGES), 8)
        self._combo(controls, "情绪", self.emotion, list(EMOTIONS), 8)
        self._spin(controls, "语速", self.speed, 0.75, 1.35, 0.01, 7)
        self._spin(controls, "情绪强度", self.emotion_strength, 0.25, 1.75, 0.05, 7)
        self._spin(controls, "LUFS", self.target_lufs, -20, -12, 1, 7)
        self._spin(controls, "种子", self.seed, 0, 2147483647, 1, 11)
        ttk.Checkbutton(controls, text="通过 RVC（慢速）", variable=self.use_rvc).pack(side=LEFT, padx=8)

        text_row = ttk.Frame(editor)
        text_row.pack(fill=X, pady=(8, 0))
        ttk.Label(text_row, text="台词").pack(side=LEFT, padx=(0, 8))
        self.text = ScrolledText(text_row, height=4, wrap="word", font=("Microsoft YaHei UI", 10))
        self.text.pack(side=LEFT, fill=X, expand=True)
        self.text.insert("1.0", ROLE_PRESETS["管家"]["sample"])
        buttons = ttk.Frame(text_row)
        buttons.pack(side=RIGHT, padx=(10, 0))
        ttk.Button(buttons, text="加入队列", command=self.add_current).pack(fill=X, pady=2)
        ttk.Button(buttons, text="更新选中", command=self.update_selected).pack(fill=X, pady=2)
        ttk.Button(buttons, text="生成当前", command=self.generate_current).pack(fill=X, pady=2)

        path_row = ttk.Frame(editor)
        path_row.pack(fill=X, pady=(8, 0))
        ttk.Label(path_row, text="输出目录").pack(side=LEFT, padx=(0, 8))
        ttk.Entry(path_row, textvariable=self.output_root).pack(side=LEFT, fill=X, expand=True)
        ttk.Button(path_row, text="选择", command=self.choose_output).pack(side=LEFT, padx=4)
        ttk.Button(path_row, text="打开", command=self.open_output).pack(side=LEFT)

        toolbar = ttk.Frame(self.root, padding=(14, 2))
        toolbar.pack(fill=X)
        ttk.Button(toolbar, text="导入 TXT / CSV / JSON", command=self.import_file).pack(side=LEFT)
        ttk.Button(toolbar, text="导出队列 CSV", command=self.export_csv).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="导出 CSV 模板", command=self.export_template).pack(side=LEFT)
        ttk.Separator(toolbar, orient="vertical").pack(side=LEFT, fill=Y, padx=10)
        ttk.Button(toolbar, text="生成选中", command=self.generate_selected).pack(side=LEFT)
        ttk.Button(toolbar, text="生成全部待办", command=self.generate_all).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="试听选中", command=self.play_selected).pack(side=LEFT)
        ttk.Button(toolbar, text="删除选中", command=self.delete_selected).pack(side=LEFT, padx=5)
        ttk.Button(toolbar, text="清空队列", command=self.clear_rows).pack(side=LEFT)

        table_frame = ttk.Frame(self.root, padding=(14, 6))
        table_frame.pack(fill=BOTH, expand=True)
        self.tree = ttk.Treeview(table_frame, columns=COLUMNS, show="headings", selectmode="extended")
        widths = {"id": 70, "角色": 75, "语言": 65, "情绪": 65, "语速": 55, "台词": 520, "状态": 90, "输出": 330}
        for column in COLUMNS:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=widths[column], minwidth=45, stretch=column in {"台词", "输出"})
        yscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        yscroll.pack(side=RIGHT, fill=Y)
        xscroll.pack(side="bottom", fill=X)
        self.tree.bind("<Double-1>", self.load_selected)

        footer = ttk.Frame(self.root, padding=(14, 8))
        footer.pack(fill=X)
        ttk.Progressbar(footer, variable=self.progress_value, maximum=100).pack(fill=X)
        ttk.Label(footer, textvariable=self.status).pack(anchor="w", pady=(4, 0))

    @staticmethod
    def _combo(parent, label, variable, values, width):
        box = ttk.Frame(parent)
        box.pack(side=LEFT, padx=(0, 8))
        ttk.Label(box, text=label).pack(anchor="w")
        ttk.Combobox(box, textvariable=variable, values=values, width=width, state="readonly").pack()

    @staticmethod
    def _spin(parent, label, variable, low, high, increment, width):
        box = ttk.Frame(parent)
        box.pack(side=LEFT, padx=(0, 8))
        ttk.Label(box, text=label).pack(anchor="w")
        ttk.Spinbox(box, textvariable=variable, from_=low, to=high, increment=increment, width=width).pack()

    def _role_changed(self, *_):
        role = self.role.get()
        if role in ROLE_PRESETS:
            self.speed.set(ROLE_PRESETS[role]["speed"])

    def _current_defaults(self):
        return {
            "角色": self.role.get(), "语言": self.language.get(), "情绪": self.emotion.get(),
            "语速": self.speed.get(), "种子": self.seed.get(), "使用RVC": self.use_rvc.get(),
        }

    def _current_row(self, number=None):
        return normalize_row(
            {
                "id": number or len(self.rows) + 1, "角色": self.role.get(), "语言": self.language.get(),
                "情绪": self.emotion.get(), "语速": self.speed.get(), "台词": self.text.get("1.0", END).strip(),
                "种子": self.seed.get(), "使用RVC": self.use_rvc.get(),
            },
            number or len(self.rows) + 1,
        )

    def _insert_row(self, row):
        iid = self.tree.insert("", END, values=self._display_values(row))
        self.rows[iid] = row
        return iid

    @staticmethod
    def _display_values(row):
        return tuple(row.get(column, "") for column in COLUMNS)

    def _refresh_row(self, iid):
        self.tree.item(iid, values=self._display_values(self.rows[iid]))

    def add_current(self):
        try:
            self._insert_row(self._current_row())
        except Exception as exc:
            messagebox.showerror("无法加入", str(exc), parent=self.root)

    def update_selected(self):
        selected = self.tree.selection()
        if len(selected) != 1:
            messagebox.showinfo("请选择一条", "更新时请只选择一条队列记录。", parent=self.root)
            return
        try:
            old = self.rows[selected[0]]
            row = self._current_row(old["id"])
            self.rows[selected[0]] = row
            self._refresh_row(selected[0])
        except Exception as exc:
            messagebox.showerror("更新失败", str(exc), parent=self.root)

    def load_selected(self, *_):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.rows[selected[0]]
        self.role.set(row["角色"])
        self.language.set(row["语言"])
        self.emotion.set(row["情绪"])
        self.speed.set(row["语速"])
        self.seed.set(row["种子"])
        self.use_rvc.set(row["使用RVC"])
        self.text.delete("1.0", END)
        self.text.insert("1.0", row["台词"])

    def choose_output(self):
        path = filedialog.askdirectory(initialdir=self.output_root.get(), parent=self.root)
        if path:
            self.output_root.set(path)

    def open_output(self):
        path = Path(self.output_root.get())
        path.mkdir(parents=True, exist_ok=True)
        os.startfile(path)

    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("支持的文本", "*.txt *.csv *.json"), ("全部文件", "*.*")], parent=self.root)
        if not path:
            return
        try:
            imported = parse_batch_file(path, self._current_defaults())
            for row in imported:
                self._insert_row(row)
            self.status.set(f"已导入 {len(imported)} 条：{path}")
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc), parent=self.root)

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")], parent=self.root)
        if not path:
            return
        fields = ("id", "角色", "语言", "情绪", "语速", "台词", "种子", "使用RVC", "状态", "输出")
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows({field: row.get(field, "") for field in fields} for row in self.rows.values())
        self.status.set(f"已导出队列：{path}")

    def export_template(self):
        path = filedialog.asksaveasfilename(initialfile="龙女仆配音导入模板.csv", defaultextension=".csv", filetypes=[("CSV", "*.csv")], parent=self.root)
        if not path:
            return
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("id", "角色", "语言", "情绪", "语速", "台词", "种子", "使用RVC"))
            writer.writeheader()
            for index, role in enumerate(ROLE_PRESETS, 1):
                writer.writerow({
                    "id": index, "角色": role, "语言": "中文", "情绪": "平静",
                    "语速": ROLE_PRESETS[role]["speed"], "台词": ROLE_PRESETS[role]["sample"],
                    "种子": 20260824 + index, "使用RVC": "否",
                })
        self.status.set(f"已导出模板：{path}")

    def delete_selected(self):
        for iid in self.tree.selection():
            self.rows.pop(iid, None)
            self.tree.delete(iid)

    def clear_rows(self):
        if self.rows and not messagebox.askyesno("清空队列", "确定清空当前队列吗？不会删除已生成 WAV。", parent=self.root):
            return
        for iid in list(self.rows):
            self.tree.delete(iid)
        self.rows.clear()

    def play_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("没有选择", "请选择一条已生成的记录。", parent=self.root)
            return
        path = Path(self.rows[selected[0]].get("输出", ""))
        if not path.is_file():
            messagebox.showerror("无法试听", "这条记录还没有有效 WAV。", parent=self.root)
            return
        winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)

    def generate_current(self):
        try:
            row = self._current_row("single")
            iid = self._insert_row(row)
            self._start_generation([iid])
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc), parent=self.root)

    def generate_selected(self):
        self._start_generation(list(self.tree.selection()))

    def generate_all(self):
        targets = [iid for iid, row in self.rows.items() if row.get("状态") != "已完成"]
        self._start_generation(targets)

    def _start_generation(self, targets):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("正在生成", "当前批次尚未结束，请稍候。", parent=self.root)
            return
        if not targets:
            messagebox.showinfo("没有任务", "请选择记录，或先加入/导入台词。", parent=self.root)
            return
        runtime_settings = {
            "emotion_strength": self.emotion_strength.get(),
            "target_lufs": self.target_lufs.get(),
            "output_root": self.output_root.get(),
        }
        self.progress_value.set(0)
        self.worker = threading.Thread(
            target=self._worker_generate,
            args=(targets, runtime_settings),
            daemon=True,
        )
        self.worker.start()

    def _worker_generate(self, targets, runtime_settings):
        total = len(targets)
        for index, iid in enumerate(targets, 1):
            row = self.rows.get(iid)
            if not row:
                continue
            self.events.put(("row", iid, "生成中", ""))
            try:
                result = synthesize_role(
                    text=row["台词"], role=row["角色"], language=row["语言"], emotion=row["情绪"],
                    speed=row["语速"], emotion_strength=runtime_settings["emotion_strength"],
                    target_lufs=runtime_settings["target_lufs"], seed=row["种子"], use_rvc=row["使用RVC"],
                    output_root=runtime_settings["output_root"], filename_prefix=row["id"],
                )
                self.events.put(("row", iid, "已完成", str(result.output_path)))
            except Exception as exc:
                self.events.put(("row", iid, "失败", str(exc)))
                self.events.put(("log", traceback.format_exc()))
            self.events.put(("progress", index / total * 100, f"进度 {index}/{total}"))
        self.events.put(("done",))

    def _poll_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == "row":
                    _, iid, status, output = event
                    if iid in self.rows:
                        self.rows[iid]["状态"] = status
                        if status == "已完成":
                            self.rows[iid]["输出"] = output
                        elif status == "失败":
                            self.rows[iid]["输出"] = output[:300]
                        self._refresh_row(iid)
                elif event[0] == "progress":
                    self.progress_value.set(event[1])
                    self.status.set(event[2])
                elif event[0] == "log":
                    print(event[1], file=sys.stderr)
                elif event[0] == "done":
                    self.status.set("当前批次已结束；失败项可修正后重新生成。")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)


def main():
    root = Tk()
    VoiceBatchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
