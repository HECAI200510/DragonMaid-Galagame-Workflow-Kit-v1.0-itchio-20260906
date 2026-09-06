# TTS 与音效管线

## 先纠正名称

`Qwen3-TTS` 不是 GPT-2，也不是 GPT-SoVITS 的“免费底模”。本项目出现过三条不同链路：

| 链路 | 本机用途 | 本机端口/入口 | 是否必须参考音频 |
|---|---|---|---|
| Qwen3-TTS 1.7B CustomVoice | 预设音色 + 指令控制的中/日/英底声、批量短语气 | `127.0.0.1:9881` | 否 |
| GPT-SoVITS v2Pro | zero/few-shot TTS 试听与旧工作台 | `127.0.0.1:9880` | 是 |
| RVC | 把已有 WAV 转为目标音色的可选后处理 | 本地模型/推理脚本 | 需要合法训练的音色权重 |

最终 H5 v2.1 的新增情绪语音记录为 Qwen3-TTS CustomVoice；旧的日语正式配音、GPT-SoVITS/RVC 试听和 Qwen 短语气批次是不同资产层，不应合并描述为一个模型。

## Qwen 批量流程

```text
需求表/CSV/JSON
-> 角色、语言、情绪、强度、语速、目标文件名
-> 9881 /health 确认 ready + loaded
-> /synthesize 生成原始 WAV
-> 去首尾静音、响度处理、时长保护
-> 角色/语言/情绪目录 + 同名 JSON 记录
-> 技术 QA
-> 人工试听
-> 游戏 manifest 绑定
```

本机曾完成 97 条中文、97 条日语、97 条英语短语气技术批次，共 291 个 24 kHz mono PCM16 WAV；这是当次验收记录，不是公开包内的音频数量。公开包不含这些 WAV。

## 短语气保护

- 单条最多尝试有限次数，不无限换 seed；
- 限制 `max_new_tokens`；
- 对异常超长音频停止批次；
- 用 RMS/峰值检测近静音；
- TTS 连接失败允许重试和服务重启；
- `loudnorm` 测得 `-inf` 时使用降级策略；
- 每种语言只读取对应文案列，不能把中文复用给日语/英语。

## GPT-SoVITS 与 RVC

GPT-SoVITS v2Pro 适合使用有权使用的参考音频做 zero/few-shot TTS。RVC 只负责音色转换，不能把公开角色/真人音色权重当成项目可自由分发的素材。

公开分享时只保留：代码入口、参数、模型官方链接、生成记录结构和验收方法。参考音频、训练数据、`.pth/.index` 一律不打包。

## 程序化音效

`05_语音与音效脚本/game_audio_examples/generate_sfx_pack.py` 用正弦音、扫频、包络和软噪声程序生成 12 个 UI/剧情音效，不读取外部采样：

```text
ui_click, ui_confirm, dialogue_advance, gallery_open,
theme_switch, game_start, save_confirm, load_confirm,
scene_enter, branch_choice, result_complete, result_defeat
```

脚本输出 48 kHz、mono、PCM16 WAV 与 `sfx_manifest.json`。这能说明声音文件的生成方式和格式，不等于每个声音的听感已经适合最终发行。

## 游戏接线

- WAV 放进清晰的角色/用途目录；
- manifest 使用真实相对路径；
- 正式配音优先时，不在同一行再叠情绪语音；
- 提供“日语配音/纯音效”之类的明确模式切换；
- 浏览器实际点击验证音频触发与自动播放限制；
- ZIP 用 CRC/`testzip()` 检查。

## 技术 QA 与人工 QA

技术检查：文件存在、可解码、采样率、声道、位深、时长、近静音、映射、重复、ZIP。

人工检查：咬字、年龄感、情绪、换气、金属音、尾音、音量体感、与 CG/台词同步。两种结果必须分别记录。
