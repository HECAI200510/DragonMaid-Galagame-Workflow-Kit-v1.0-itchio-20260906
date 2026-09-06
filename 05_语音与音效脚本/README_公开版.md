# 语音与音效脚本公开版说明

这里放的是制作流程源码示例，不是开箱即用的 TTS 整合包。

## 文件

- `dragonmaid_voice_batch_gui.py`：CSV/XLSX/JSON 批量导入、三语字段隔离、任务队列和导出 GUI。
- `dragonmaid_voice_nodes/`：ComfyUI 节点与共享的 `voice_core.py`。
- `qwen_customvoice_service.py`：Qwen3-TTS CustomVoice 的 FastAPI 服务示例。
- `qwen_customvoice_limited_service.py`：带短语气 token/资源保护的服务版本。
- `run_voice_batch.py`：根据 manifest 调用 9881 并做 FFmpeg 后处理。
- `qa_voice_assets.py`：WAV 与映射的技术 QA。
- `game_audio_examples/generate_sfx_pack.py`：生成 12 个程序化音效。
- `game_audio_examples/generate_emotion_vocals.py`：游戏项目定制的情绪语音生成示例。
- `game_audio_examples/bind_emotion_vocals.py`：游戏项目定制的 manifest 绑定示例。

最后两份情绪语音脚本依赖原游戏目录结构，仅用于展示“生成 -> 记录 -> 绑定”的实现，不应在空目录直接运行。

## 环境

批量 GUI 本身使用标准库 Tkinter；Qwen 服务需要 `requirements_voice_optional.txt` 中的包和与显卡匹配的 PyTorch。模型按官方说明单独下载到 TTS 环境。

不要把 TTS 依赖安装进 ComfyUI 的 Python 环境。本机经过验证的结构把 ComfyUI、TTS 和模型目录分开。

## 端口

- Qwen3-TTS：`http://127.0.0.1:9881`
- GPT-SoVITS 旧工作台：`http://127.0.0.1:9880`

端口只是本项目约定，不是上游工具固定要求。

## 权利边界

公开包不含参考音频、训练数据、角色音色权重或生成 WAV。只使用本人录音、原创配音者授权录音，或许可证明确覆盖训练与发布的数据。
