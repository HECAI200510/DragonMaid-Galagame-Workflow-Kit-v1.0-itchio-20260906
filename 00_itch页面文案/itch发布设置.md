# itch.io 发布设置建议

## 建议作为独立工具页发布

- Title：`DragonMaid Galgame Workflow Kit / 龙女仆 Galgame 制作工作流`
- Short description：`我实际使用的 ComfyUI 批量提示词、TTS、分支机制与 UX 工作流；不含模型权重。`
- Classification：`Tools`；如果界面没有 Tools，可选 `Other`
- Kind of project：`Downloadable`
- Pricing：`No payments` 或免费；同人/衍生 IP 不建议设置付费门槛
- Release status：`Prototype` 或 `Released`
- Suggested tags：`visual-novel`, `comfyui`, `python`, `tools`, `workflow`, `generative-ai`, `game-development`, `chinese`, `windows`, `sourcecode`
- Cover：上传 `cover_630x500.png`
- Screenshots：建议 3～5 张，分别截 GUI、ComfyUI 节点、工作流图、分支自动存档、移动端界面
- Download：上传根目录旁边生成的 `DragonMaid-Galagame-Workflow-Kit-v1.0-itchio-20260906.zip`

项目页正文直接粘贴 `itch项目页_可直接粘贴.md`，如编辑器不识别 Markdown 标题，选中标题后应用 Header 2。

## 也可以作为现有游戏页的 devlog

如果你已经有游戏页面，不想再建工具页：

1. 在游戏页创建新 devlog。
2. 粘贴 `itch_devlog_可直接粘贴.md`。
3. 把 ZIP 作为免费 bonus/toolkit 上传到同一项目页。
4. 在主页面 Credits/Development workflow 段落链接到该 devlog。

## AI 披露

本项目涉及生成式 AI 封面、CG、提示词草稿和部分语音，应如实启用 itch.io 对应的 AI 生成内容标签/披露。模型、LoRA、声音和第三方素材的许可仍需分别核对；平台标签不能替代权利检查。

## 不要选择 HTML5 Game

这个 ZIP 是源码/工作流下载包，不是浏览器游戏，没有根级 `index.html`。因此应发布为 Downloadable。若以后另做交互式网页演示，再单独上传含根级 `index.html` 的 HTML5 ZIP。

## 发布前最后检查

- 页面明确写“非官方、非商业粉丝研究”。
- 不使用“官方”“授权”“原声优”等容易误导的表述。
- 不上传 `.safetensors/.pth/.index/参考音频/角色卡`。
- 所有第三方链接指向原作者或官方页。
- ZIP 内没有绝对隐私路径、运行日志、缓存和旧备份。
- Windows 上解压后先跑 `07_校验/verify_public_release.ps1`。
