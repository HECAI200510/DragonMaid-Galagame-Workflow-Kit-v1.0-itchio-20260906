# DragonMaid Galgame Workflow Kit v1.0

这是一份“制作过程公开包”，不是游戏本体，也不是模型合集。它记录我制作《游戏王》龙女仆同人 Galgame 时实际使用过的 ComfyUI、批量提示词、TTS、程序化音效、剧本分支和 UX 迭代方法。

## 包里有什么

- 可直接粘贴到 itch.io 的项目页文案和 devlog。
- Windows/Tkinter 批量提示词 GUI 当前版、测试和示例输入。
- ComfyUI 批量提示词自定义节点、最小预览工作流和测试。
- 6 个通用尺寸模板、7 个角色代表 API 工作流、70 条事件 CG 提示词与参数表。
- Qwen3-TTS 批量 GUI、服务端适配、ComfyUI 配音节点和技术验收脚本。
- GPT-SoVITS v2Pro、Qwen3-TTS、RVC 的职责区别和来源索引。
- 12 个无外部采样的程序化 UI/剧情音效生成示例。
- 模型名称、触发词、SHA-256 与来源索引；不含任何大模型权重。

## 推荐阅读顺序

1. `00_itch页面文案/itch项目页_可直接粘贴.md`
2. `01_工作流说明/工作流全景.md`
3. `01_工作流说明/CG与提示词管线.md`
4. `01_工作流说明/TTS与音效管线.md`
5. `01_工作流说明/剧本机制与UX迭代.md`
6. `01_工作流说明/模型与来源索引.md`
7. `07_校验/VALIDATION_REPORT.md`

## 最快试用批量提示词 GUI

1. 安装 Python 3.10 以上版本。Windows 自带的 Tkinter 即可，无额外 pip 依赖。
2. 启动 ComfyUI，默认地址为 `http://127.0.0.1:8188`。
3. 双击 `02_批量提示词GUI/启动批量提示词输入器.cmd`。
4. 选择一个 ComfyUI 工作流 JSON，再导入 `prompts` 下的编号提示词。
5. 先预览前 5 条，再提交小批量任务。

## 最快试用 ComfyUI 节点

把 `03_ComfyUI节点` 整个目录复制到：

```text
ComfyUI/custom_nodes/dragonmaid_batch_prompt_node
```

重启 ComfyUI，在节点菜单中寻找：

```text
DragonMaid / 批量提示词
```

最小工作流只做文本解析和预览，不加载模型、不生成图片。

## 公开边界

本包不包含：

- `.safetensors`、`.ckpt`、`.pth`、`.index`、`.bin`、`.gguf` 等权重；
- 第三方角色卡、VRChat/MMD/恋活模型本体；
- 参考音频、RVC 训练数据或角色音色权重；
- 游戏本体 CG、成人测试工作流、个人运行日志、旧 `.bak`；
- Civitai/Tensor.Art/PixAI 上作者未明确允许再分发的文件。

这是非官方、非商业的粉丝制作研究记录。《游戏王》、Dragonmaid 及相关角色权利归原权利方所有。本包不代表 KONAMI，也不授予第三方素材的再分发权。

代码部分尚未单独指定开源许可证。未经作者另行说明，不要把“能看到源码”理解为获得商用、再许可或二次打包权。第三方工具与模型分别遵守各自许可证。

## AI 披露

早期部分 SD 提示词和资料索引按作者自述曾由 Grok 协助起草；随后经过人工改写、筛选和本机验证。CG 使用本地 ComfyUI/SDXL/Illustrious 工作流；部分语音使用 Qwen3-TTS 或 GPT-SoVITS/RVC 实验管线。封面为生成式 AI 辅助制作，未使用第三方角色模型。

自动化校验只能证明源码、JSON、音频格式和打包结构符合预期，不能替代人工审美、听感与版权判断。
