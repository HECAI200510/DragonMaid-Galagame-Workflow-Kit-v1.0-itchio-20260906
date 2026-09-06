# DragonMaid TTS / RVC 官方底模筛选（2026-08-22）

## 结论先行

本报告只筛选官方 GitHub、Hugging Face 或 ModelScope 发布物；没有下载或安装模型，也不推荐任何真人声优、动漫角色克隆模型或来源不明的 RVC 权重。

对于当前电脑与项目，最合理的顺序是：

1. **今天先用已经安装好的 GPT-SoVITS v2Pro 整合包试听**：不新增依赖，直接用自己有权使用的参考录音测试中、日、英台词。
2. **补一个免训练的公开通用音色试听组**：优先 MeloTTS；再用 Kokoro 扩大可试听女声音色数量。两者都能直接输出 WAV，之后可作为 RVC 的源音频。
3. **如果 GPT-SoVITS 的跨语言、情绪或稳定性不够，再测试 Fun-CosyVoice3-0.5B-2512 或 Chatterbox Multilingual V3**。它们更适合“同一授权参考声跨中日英”的对照，但当前没有必要同时安装。
4. **Style-Bert-VITS2 只作为日语专项备选**。它的优势是日语角色感和风格控制，劣势是不能承担中日英统一入口，且默认 JVNV 音色包为 CC BY-SA 4.0。
5. **RVC 放在最后做音色统一，不用拿 TTS 合成音反过来训练 RVC**。更可靠的数据来源仍是同一位授权录音者的干净真人素材。TTS 输出可以作为 RVC 的推理输入和试听素材，但把带伪影的 TTS 输出当 RVC 训练集，会把咬字、气声和频谱伪影一起学进去。

## 安全边界

- 只使用本人录音、明确授权录音或许可证清楚的通用音色。
- 不使用声优、主播、动漫角色或游戏角色的未经授权克隆权重。
- “代码许可证”“官方基础权重许可证”“第三方 voice pack / 参考音频许可证”必须分别核对；代码开源不等于任意音色都可用。
- 本项目目前是非商业粉丝游戏，但仍建议保存模型卡、许可证、下载日期、参考音频来源和授权记录。
- 下表是工程筛选，不是法律意见。若以后公开收费、众筹、广告变现或向平台正式发布，需重新做一次许可证复核。

## 总表

| 方案 | 中/日/英 | 公共通用音色 | 角色定制方式 | 代码许可 | 官方权重/音色许可 | 官方硬件信息 | 接 RVC | 本项目定位 |
|---|---|---|---|---|---|---|---|---|
| GPT-SoVITS v2Pro / ProPlus | 是 | 不以命名通用音色库为卖点 | 5 秒 zero-shot；约 1 分钟 few-shot 微调 | MIT | 官方 HF 基础权重标注 MIT | 官方测试 CUDA 12.8 / PyTorch 2.7；V3 LoRA 微调注明 8GB VRAM；未给 v2Pro 固定显存下限 | 是，输出 WAV | **首选角色生产线；本机已有包** |
| Fun-CosyVoice3-0.5B-2512 | 是 | 不建议把仓库示例音频当正式角色音源 | 多语种 / 跨语种 zero-shot；指令控制情绪、速度等 | Apache-2.0 | 官方 HF 权重 Apache-2.0 | 官方卡给出 0.5B 和 Python 3.10；未给固定 VRAM 下限 | 是 | **高质量跨语言对照，第二阶段再装** |
| MeloTTS | 是 | 有：中文、日文单音色；英文多口音 | 固定音色 TTS；自定义需另训练；可和 OpenVoice 或 RVC 串联 | MIT | 官方各语言 HF 权重标注 MIT | 官方明确 CPU 可实时；单语言 checkpoint 约 208MB；未给 GPU 显存下限 | 是 | **今天试听通用底声最省事** |
| Kokoro-82M v1.0 | 是 | 有：54 个，含中/日/英 | 固定音色；支持速度与 voice embedding 混合，不是 zero-shot 克隆 | Apache-2.0 | 官方模型库 Apache-2.0；部分日语/法语训练来源另列 CC BY | 82M；官方 Colab/CPU/GPU均可用，但未给固定 VRAM下限 | 是 | **音色海选好用；中文/日文质量低于英语** |
| Chatterbox Multilingual V3 | 是 | 能无参考生成默认音色，也支持参考声 | 500M，多语种 zero-shot；表达夸张控制 | MIT | 官方 HF 权重 MIT | 官方给出 500M；未给固定 VRAM下限。Nano 110M 明确可在 8 核 CPU 约 3×实时，但只偏英语 | 是 | **跨语言与情绪对照；输出自带不可感知水印** |
| Style-Bert-VITS2 + JVNV | 技术栈可中/日/英，但默认包重点日语 | 有：JVNV 2 女 2 男等 | 日语角色定制训练；风格向量控制 | AGPL-3.0；部分文本模块 LGPL-3.0 | JVNV 默认音色包 CC BY-SA 4.0；其他包另有各自条款 | 推理可 CPU；训练需 NVIDIA。JP-Extra 训练官方经验值：batch 1/2/3/4 约 6/8/10/12GB VRAM | 是 | **日语专项，不做统一主入口** |
| RVC WebUI | 与文本语言无关 | 不应下载来历不明角色权重 | 用授权说话人数据训练音色转换模型 | MIT | 官方基础模型随仓库；每个角色模型的权利取决于训练数据 | 官方当前分支支持 RTX 50 系 CUDA 12.8；建议至少约 10 分钟低噪声说话数据 | 接收上游 WAV | **TTS 后处理 / 音色统一** |

## 逐项核对

### 1. GPT-SoVITS：当前首选

官方功能说明：

- 5 秒参考音频可 zero-shot；约 1 分钟数据可 few-shot 微调。
- 支持中文、英文、日语、韩语、粤语以及跨语言合成。
- 官方 README 的测试环境已经列出 Python 3.11 + PyTorch 2.7.0 + CUDA 12.8，适合 RTX 50 系环境。
- v2ProPlus 官方速度数据在 4060 Ti、4090 和 Apple M4 CPU 上都有记录。
- V3 LoRA 微调官方更新说明给出 8GB VRAM；v2Pro 没有官方固定显存下限。
- v2Pro / ProPlus 对普通质量训练集更宽容；v3/v4 更依赖参考音频质量。对当前“先建立七角色稳定音色”的目标，保留 v2Pro 是合理的。

许可证：

- [GitHub 代码仓库：MIT](https://github.com/RVC-Boss/GPT-SoVITS)
- [GitHub LICENSE](https://github.com/RVC-Boss/GPT-SoVITS/blob/main/LICENSE)
- [官方 Hugging Face 基础权重：MIT](https://huggingface.co/lj1995/GPT-SoVITS)

试听 / 下载：

- [官方 Windows 整合包与安装说明](https://github.com/RVC-Boss/GPT-SoVITS#installation)
- [官方 Hugging Face 模型目录](https://huggingface.co/lj1995/GPT-SoVITS)
- [官方 v2ProPlus 在线演示](https://huggingface.co/spaces/lj1995/GPT-SoVITS-ProPlus)

判断：**直接使用本机已有包，不另下重复整合包。** 今天的第一轮应使用有权使用的参考音频生成统一台词，再决定是否训练。

### 2. Fun-CosyVoice3-0.5B-2512：跨语言高质量对照

官方模型卡声明：

- 0.5B 参数。
- 支持中文、英文、日语、韩语、德语、西班牙语、法语、意大利语、俄语，以及 18+ 中文方言/口音。
- 支持多语种和跨语种 zero-shot 音色克隆、情绪/语速/音量等指令控制、中文拼音和英文 CMU 音素修正。
- 代码与官方 HF 权重均标注 Apache-2.0。
- 官方安装使用 Python 3.10；模型卡没有承诺固定最低显存，因此不能把社区“约 4GB”当官方要求。

风险：官方仓库免责声明说明部分演示内容来自互联网。**仓库的 `asset/zero_shot_prompt.wav` 可以用于复现实验，但不应直接成为游戏正式角色声源。** 正式使用必须换成自己的授权参考音频。

链接：

- [官方 GitHub（现会重定向到 QwenAudio/CosyVoice）](https://github.com/FunAudioLLM/CosyVoice)
- [官方 HF：Fun-CosyVoice3-0.5B-2512，Apache-2.0](https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512)
- [官方 ModelScope 页面入口](https://www.modelscope.cn/models/iic/Fun-CosyVoice3-0.5B-2512)
- [官方 CosyVoice 3 演示](https://funaudiollm.github.io/cosyvoice3/)

判断：**先在线听，再决定是否本地安装；不和 GPT-SoVITS 同时开新坑。**

### 3. MeloTTS：最适合今天建立“通用底声试听组”

官方信息：

- 支持英语多口音、中文（可中英混读）、日语、韩语、西班牙语和法语。
- 官方明确 CPU 足以实时推理。
- 中文、日文、英文官方 checkpoint 各约 208MB，HF 模型卡均标注 MIT。
- 它不是 few-shot 角色克隆模型；优势是输出稳定、轻、快。把它生成的中性 WAV 送入已训练好的 RVC，是清晰的两段式管线。

官方未在模型卡详细公开每个固定音色的说话人身份与训练语料明细。尽管权重标注 MIT，仍应保留模型卡快照和下载日期，不把声音宣传成某位真人。

链接：

- [官方 GitHub：MeloTTS，MIT](https://github.com/myshell-ai/MeloTTS)
- [中文权重](https://huggingface.co/myshell-ai/MeloTTS-Chinese)
- [日文权重](https://huggingface.co/myshell-ai/MeloTTS-Japanese)
- [英文权重](https://huggingface.co/myshell-ai/MeloTTS-English)

可试听的官方 speaker / 口音入口：

- 中文：`ZH`
- 日文：`JP`
- 英文：`EN-US`、`EN-BR`、`EN_INDIA`、`EN-AU`、`EN-Default`

判断：**公开通用底声试听优先级第一。** 但它是“为 RVC 提供干净发音”的底声，不是最终角色身份。

### 4. Kokoro-82M：适合大范围固定音色海选

官方信息：

- 82M 参数，v1.0 模型和 voice embeddings 在同一个 Apache-2.0 模型库中。
- 官方 voice 表共 54 个音色，包含中、日、英。
- 官方明确指出非英语语种可能因 G2P 和数据量表现较弱；中文女声的官方综合评分都是 D，日语女声约 C- 到 C+，英语 `af_heart` 为 A、`af_bella` 为 A-、`af_nicole` 为 B-。
- 部分日语 voice 的语料来源在官方 voice 表中另列 CC BY；使用这些音色时应保留对应署名。模型卡也给出了训练数据的 CC BY 归属记录。
- 官方未给最低 VRAM，只给出 Colab 使用方式；不要引用社区估算为官方要求。

首轮可试听 ID：

- 英语女声：`af_heart`、`af_bella`、`af_nicole`
- 日语女声：`jf_alpha`、`jf_gongitsune`、`jf_tebukuro`、`jf_nezumi`
- 中文女声：`zf_xiaobei`、`zf_xiaoni`、`zf_xiaoxiao`、`zf_xiaoyi`

链接：

- [官方 HF 模型与下载：Apache-2.0](https://huggingface.co/hexgrad/Kokoro-82M)
- [官方 VOICES.md：音色、质量分级和来源](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)
- [官方样音列表](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/SAMPLES.md)
- [官方 HF Space](https://huggingface.co/spaces/hexgrad/Kokoro-TTS)
- [官方推理库](https://github.com/hexgrad/kokoro)

判断：**适合海选，不应因为音色数量多就当最终中日文角色模型。**

### 5. Chatterbox Multilingual V3：表达力和跨语言备选

官方信息：

- Multilingual V3 为 500M，支持包括中、日、英在内的 23+ 种语言。
- 可以不传参考音频生成默认声音，也可以传入自己的参考音频进行 zero-shot。
- 支持 `exaggeration` 和 `cfg_weight` 控制表达强度与参考声约束。
- 官方代码和 HF 权重均标注 MIT。
- 每段生成音频都会写入 PerTh 不可感知水印；用于游戏前应接受并记录这一事实，不要尝试移除。
- 官方未给 500M 多语模型固定最低显存。110M Nano 明确支持 8 核 CPU 约 3×实时，但 Nano 重点是英语，不能用来替代三语 V3。

链接：

- [官方 GitHub：MIT](https://github.com/resemble-ai/chatterbox)
- [官方 HF 模型：MIT](https://huggingface.co/ResembleAI/chatterbox)
- [官方多语演示](https://huggingface.co/spaces/ResembleAI/Chatterbox-Multilingual-TTS)
- [官方样音站](https://resemble-ai.github.io/chatterbox_demopage/)

判断：**先在线听。** 若默认音色适合某个角色，可把它作为 RVC 的稳定源声；若用参考克隆，则参考音频仍必须有授权。

### 6. Style-Bert-VITS2：日语专项

官方信息：

- 代码仓库是 AGPL-3.0；部分源自 VOICEVOX 的文本模块是 LGPL-3.0。
- 默认 JVNV 音色包与代码分开发布，权重许可证为 CC BY-SA 4.0。
- 默认 JVNV 提供 `jvnv-F1-jp`、`jvnv-F2-jp`、`jvnv-M1-jp`、`jvnv-M2-jp`；本项目优先只试听 F1/F2。
- CPU 可推理和合并，但训练需要 NVIDIA GPU。
- 官方更新日志给出 JP-Extra 训练的经验显存：batch 1/2/3/4 约 6/8/10/12GB。
- 其他预设声如 koharune-ami、amitaro 有各自额外条款，不能因为主仓库是 AGPL 就跳过它们的声音许可。

链接：

- [官方 GitHub](https://github.com/litagin02/Style-Bert-VITS2)
- [默认音色及条款说明](https://github.com/litagin02/Style-Bert-VITS2/blob/master/docs/TERMS_OF_USE.md)
- [官方 JVNV 权重：CC BY-SA 4.0](https://huggingface.co/litagin/style_bert_vits2_jvnv)
- [JP-Extra 基础模型](https://huggingface.co/litagin/Style-Bert-VITS2-2.0-base-JP-Extra)

判断：**只在日语线路明确需要更强风格控制时再装。**

### 7. RVC：应如何与 TTS 串联

官方 RVC 项目定位是说话音色转换，而不是文本到语音。它建议使用至少约 10 分钟的低噪声说话数据训练；检索特征用于降低底声泄漏。

许可证和下载：

- [官方 GitHub：MIT](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
- [官方许可证与第三方组件清单](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI/blob/main/MIT%E5%8D%8F%E8%AE%AE%E6%9A%A8%E7%9B%B8%E5%85%B3%E5%BC%95%E7%94%A8%E5%BA%93%E5%8D%8F%E8%AE%AE)
- [官方基础模型目录](https://huggingface.co/lj1995/VoiceConversionWebUI/tree/main)

推荐离线链路：

```text
游戏台词
  -> GPT-SoVITS / MeloTTS / CosyVoice / Chatterbox 生成干净 WAV
  -> 音量标准化 + 去首尾静音（不要强降噪）
  -> 角色专用 RVC 模型推理
  -> 人工检查：咬字、呼吸、音高跳变、金属音、重复音
  -> Unity 用的 WAV/OGG + VoiceID 清单
```

正确的数据分工：

- **TTS 训练集**：录音 + 准确逐字文本，强调发音覆盖、句式和情绪。
- **RVC 训练集**：目标音色的干净干声，文本不是核心，但音高、情绪和语速覆盖很重要。
- **TTS 合成 WAV**：适合作为 RVC 推理输入，不宜成为主要 RVC 训练数据。

## 立即试听优先级

### 第 0 级：不下载

1. 打开本机 GPT-SoVITS v2Pro，用现有试听候选中的授权样本，生成同一套中/日/英对照句。
2. 在线听 [CosyVoice 3 官方演示](https://funaudiollm.github.io/cosyvoice3/) 和 [Chatterbox 多语演示](https://huggingface.co/spaces/ResembleAI/Chatterbox-Multilingual-TTS)，只决定是否值得安装。
3. 在线听 [Kokoro 官方样音](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/SAMPLES.md)，记录喜欢的 voice ID。

### 第 1 级：只装一个轻量公开底声

优先 **MeloTTS**。理由：三种目标语言都有官方独立权重、CPU 可实时、输出稳定、接 RVC 最直接。

### 第 2 级：需要更多固定女声时

补 **Kokoro-82M**。优先用作海选和英语底声；中文、日语要接受官方自评偏低的事实。

### 第 3 级：需要跨语言角色一致性时

在 **CosyVoice 3** 和 **Chatterbox Multilingual V3** 中二选一：

- 更重视中文、日文、英文的内容准确、细粒度指令：先试 CosyVoice 3。
- 更重视夸张程度控制、默认声音、安装简洁并接受水印：先试 Chatterbox。

### 第 4 级：日语专项

Style-Bert-VITS2 + JVNV F1/F2。只用于日语路线，单独建立署名与 ShareAlike 台账。

## 七角色试听建议（仅音色方向，不是角色克隆）

所有角色先使用相同三句台词、相同响度、相同采样率比较，不要先凭角色名字套用网络模型。

| 角色 | 第一轮需要辨别的声音属性 | 底声候选方式 |
|---|---|---|
| 管家 | 低调、沉稳、指挥感、不过度苍老 | MeloTTS ZH / JP；Kokoro 英语 `af_nicole`、`af_kore`；再由 RVC 定音色 |
| 小红 | 成熟、利落、傲娇但不尖锐 | MeloTTS；Kokoro 英语 `af_bella`、`af_heart`；GPT-SoVITS 授权参考声 |
| 小绿 | 明亮、快、带顽皮感 | Kokoro 多女声快速海选；最终转 GPT-SoVITS / RVC |
| 小蓝 | 年少感、轻、清楚，不做成人内容 | 只用明确安全、非真人模仿的高音区底声；限制音高转换，人工检查失真 |
| 小粉 | 温柔、包容、气息稳定 | MeloTTS 中性女声；GPT-SoVITS 授权参考声；RVC 轻量转换 |
| 小金 | 优雅、自信、略有戏谑 | 英语可先听 `af_heart` / `bf_emma`；中日文仍以授权参考声为准 |
| 小黑 | 内敛、偏低、羞怯但不能虚弱含混 | 日语可听 JVNV F1/F2；中英文使用 GPT-SoVITS + RVC 控制 |

这些只是筛音方向。不得把公开通用音色命名成某位真实声优，也不得声称模仿官方角色配音。

## 下载决策

现在应下载 / 安装：

- **无**。先用已安装 GPT-SoVITS 完成第一轮试听。

如果第一轮需要公开通用底声，只新增：

- MeloTTS Chinese / Japanese / English 三个官方 checkpoint。

暂缓：

- CosyVoice 3、Chatterbox、Kokoro、Style-Bert-VITS2 同时本地安装。
- 任何第三方“动漫角色音色包”“声优 RVC”“整合音色包”。
- Fish Speech：官方当前代码和权重使用 Fish Audio Research License，明确非商业免费、商业需另行许可；虽然本项目当前非商业，但没有必要在已有方案足够时增加额外许可证与环境复杂度。

## 试听验收表

每条 1–5 分，3 为可用；同一角色同一候选必须中、日、英分别记录。

| 项目 | 检查内容 |
|---|---|
| 发音准确 | 人名、长音、促音、中英混读、数字和标点 |
| 角色匹配 | 年龄感、性格、威严/活泼/温柔程度 |
| 情绪范围 | 平静、开心、害羞、着急、低声五类 |
| 音色稳定 | 长句是否漂移、重复、突然换人 |
| RVC 适配 | 转换后是否保留咬字，是否出现金属音、漏底声、音高断层 |
| 合规 | 权重、参考音频和署名记录是否完整 |

只有三种语言都完成试听，才把候选标为“角色正式音色”；否则只标“试听候选”。

